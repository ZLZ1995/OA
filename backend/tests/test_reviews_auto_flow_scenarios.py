from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.review_record import ReviewRecord
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.review import ReviewDecisionRequest


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_role(db: Session, code: str, name: str) -> Role:
    role = Role(code=code, name=name, description="", is_system_fixed=True)
    db.add(role)
    db.flush()
    return role


def _seed_user(db: Session, username: str, real_name: str, roles: list[Role]) -> User:
    user = User(username=username, password_hash="x", real_name=real_name, is_active=True)
    db.add(user)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def _seed_project_bundle(db: Session) -> tuple[User, User, User, User, WorkOrder]:
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    member_role = _seed_role(db, "PROJECT_MEMBER", "项目组成员")
    first_role = _seed_role(db, "FIRST_REVIEWER", "一审")
    second_role = _seed_role(db, "SECOND_REVIEWER", "二审")

    leader = _seed_user(db, "leader", "Leader", [leader_role])
    member = _seed_user(db, "member", "Member", [member_role])
    first = _seed_user(db, "first", "First Reviewer", [first_role])
    second = _seed_user(db, "second", "Second Reviewer", [second_role])
    business = _seed_user(db, "business", "Business", [])

    project = Project(
        project_code="P-AUTO-001",
        project_name="Auto Flow Demo",
        client_name="Client",
        project_amount=100.0,
        valuation_base_date=date(2026, 5, 15),
        business_user_id=business.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=member.id))
    work_order = WorkOrder(
        work_order_no="WO-AUTO-001",
        project_id=project.id,
        title="WO",
        current_status="FIRST_REVIEWING",
        current_handler_user_id=first.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        first_reviewer_id=first.id,
        second_reviewer_id=second.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.commit()
    return leader, member, first, second, work_order


def test_real_scenario_round_one_first_approve_auto_advances_to_second() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    leader, _, first, second, work_order = _seed_project_bundle(db)
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_FIRST",
            version_no=1,
            is_current=True,
            origin_file_name="一期报告包.zip",
            storage_key="review-first-v1.zip",
            file_size=256,
            uploaded_by=leader.id,
            uploaded_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="FIRST", action="APPROVE", comment="通过"),
        db=db,
        current_user=first,
        _={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    second_submit = db.query(ReviewRecord).filter(
        ReviewRecord.work_order_id == work_order.id,
        ReviewRecord.review_round == "SECOND",
        ReviewRecord.action == "SUBMIT",
    ).first()
    second_file = db.query(WorkOrderFile).filter(
        WorkOrderFile.work_order_id == work_order.id,
        WorkOrderFile.business_stage == "REVIEW_SECOND",
        WorkOrderFile.file_category == "REPORT_ZIP",
    ).first()

    assert work_order.current_status == "SECOND_REVIEWING"
    assert work_order.current_handler_user_id == second.id
    assert second_submit is not None
    assert second_submit.comment and "AUTO_FROM_RECORD" in second_submit.comment
    assert second_file is not None
    assert second_file.origin_file_name == "一期报告包.zip"


def test_real_scenario_round_two_reject_reupload_preserves_first_round_history() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    leader, _, first, second, work_order = _seed_project_bundle(db)
    first_time = datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)
    second_time = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_FIRST",
            version_no=1,
            is_current=True,
            origin_file_name="一审第一版.zip",
            storage_key="review-first-v1.zip",
            file_size=128,
            uploaded_by=leader.id,
            uploaded_at=first_time,
        )
    )
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="FIRST", action="APPROVE", comment="一审通过"),
        db=db,
        current_user=first,
        _={"FIRST_REVIEWER"},
    )
    db.refresh(work_order)
    work_order.current_status = "SECOND_REVIEW_REJECTED"
    work_order.current_handler_user_id = leader.id
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round="SECOND",
            reviewer_user_id=second.id,
            action="REJECT_RETURN",
            comment="二审退回",
            acted_at=second_time,
        )
    )
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_SECOND",
            version_no=2,
            is_current=True,
            origin_file_name="二审修改第二版.zip",
            storage_key="review-second-v2.zip",
            file_size=512,
            uploaded_by=leader.id,
            uploaded_at=datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc),
        )
    )
    db.commit()

    first_round_file = db.query(WorkOrderFile).filter(
        WorkOrderFile.work_order_id == work_order.id,
        WorkOrderFile.business_stage == "REVIEW_FIRST",
        WorkOrderFile.file_category == "REPORT_ZIP",
    ).first()
    current_second_file = db.query(WorkOrderFile).filter(
        WorkOrderFile.work_order_id == work_order.id,
        WorkOrderFile.business_stage == "REVIEW_SECOND",
        WorkOrderFile.file_category == "REPORT_ZIP",
        WorkOrderFile.is_current.is_(True),
    ).order_by(WorkOrderFile.version_no.desc()).first()

    assert first_round_file is not None
    assert current_second_file is not None
    assert first_round_file.origin_file_name == "一审第一版.zip"
    assert current_second_file.origin_file_name == "二审修改第二版.zip"



def test_first_round_reapprove_carries_latest_passed_package_to_second_wait_submit() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    leader, _, first, _, work_order = _seed_project_bundle(db)
    work_order.second_reviewer_id = None
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = first.id

    first_submit_time = datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)
    reject_time = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
    reupload_time = datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc)

    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_FIRST",
            version_no=1,
            is_current=False,
            origin_file_name="?????V1.0.zip",
            storage_key="review-first-v1.zip",
            file_size=120,
            uploaded_by=leader.id,
            uploaded_at=first_submit_time,
        )
    )
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=first.id,
            action="REJECT_RETURN",
            comment="???",
            acted_at=reject_time,
        )
    )
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_FIRST",
            version_no=2,
            is_current=True,
            origin_file_name="?????V2.0.zip",
            storage_key="review-first-v2.zip",
            file_size=256,
            uploaded_by=leader.id,
            uploaded_at=reupload_time,
        )
    )
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REVIEW_OPINION",
            business_stage="REVIEW_FIRST",
            version_no=1,
            is_current=True,
            origin_file_name="????.docx",
            storage_key="review-opinion-first.docx",
            file_size=88,
            uploaded_by=first.id,
            uploaded_at=reject_time,
        )
    )
    db.commit()

    result = decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="FIRST", action="APPROVE", comment="???????"),
        db=db,
        current_user=first,
        _={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    second_report = db.query(WorkOrderFile).filter(
        WorkOrderFile.work_order_id == work_order.id,
        WorkOrderFile.business_stage == "REVIEW_SECOND",
        WorkOrderFile.file_category == "REPORT_ZIP",
        WorkOrderFile.is_current.is_(True),
    ).order_by(WorkOrderFile.version_no.desc()).first()
    second_opinion = db.query(WorkOrderFile).filter(
        WorkOrderFile.work_order_id == work_order.id,
        WorkOrderFile.business_stage == "REVIEW_SECOND",
        WorkOrderFile.file_category == "REVIEW_OPINION",
        WorkOrderFile.is_current.is_(True),
    ).order_by(WorkOrderFile.version_no.desc()).first()

    assert work_order.current_status == "WAIT_SECOND_REVIEW_SUBMIT"
    assert work_order.current_handler_user_id == work_order.project_leader_id
    assert second_report is not None
    assert second_report.origin_file_name == "?????V2.0.zip"
    assert second_opinion is not None
    assert second_opinion.origin_file_name == "????.docx"
    assert result.transferred_to_next is True
    assert result.transferred_to_round == "SECOND"
