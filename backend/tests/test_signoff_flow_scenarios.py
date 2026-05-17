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
from app.schemas.review import ReviewDecisionRequest, ReviewRecallRoutingRequest, ReviewSubmitRequest


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


def _seed_bundle(db: Session, eval_nature: str) -> tuple[User, User, User, User, User, WorkOrder]:
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    member_role = _seed_role(db, "PROJECT_MEMBER", "项目组成员")
    first_role = _seed_role(db, "FIRST_REVIEWER", "一审")
    second_role = _seed_role(db, "SECOND_REVIEWER", "二审")
    third_role = _seed_role(db, "THIRD_REVIEWER", "三审")

    leader = _seed_user(db, "leader", "Leader", [leader_role])
    member = _seed_user(db, "member", "Member", [member_role])
    first = _seed_user(db, "first", "First", [first_role])
    second = _seed_user(db, "second", "Second", [second_role])
    third = _seed_user(db, "third", "Third", [third_role])
    business = _seed_user(db, "business", "Business", [])

    project = Project(
        project_code=f"P-{eval_nature}",
        project_name="Signoff Demo",
        client_name="Client",
        project_amount=100.0,
        valuation_base_date=date(2026, 5, 15),
        business_user_id=business.id,
        project_leader_id=leader.id,
        evaluation_business_nature=eval_nature,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=member.id))
    work_order = WorkOrder(
        work_order_no=f"WO-{eval_nature}",
        project_id=project.id,
        title="WO",
        current_status="THIRD_REVIEWING",
        current_handler_user_id=third.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        first_reviewer_id=first.id,
        second_reviewer_id=second.id,
        third_reviewer_id=third.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_THIRD",
            version_no=1,
            is_current=True,
            origin_file_name="report.zip",
            storage_key="report.zip",
            file_size=100,
            uploaded_by=leader.id,
            uploaded_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return leader, member, first, second, third, work_order


def test_real_scenario_non_state_owned_project_moves_to_owner_signoff_upload() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    _, _, _, _, third, work_order = _seed_bundle(db, "非国有资产评估业务")

    decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="THIRD", action="APPROVE", comment="通过"),
        db=db,
        current_user=third,
        _={"THIRD_REVIEWER"},
    )

    db.refresh(work_order)
    assert work_order.current_status == "WAIT_OWNER_SIGNOFF_UPLOAD"
    assert work_order.signoff_status == "WAIT_UPLOAD"
    assert work_order.current_handler_user_id == work_order.project_leader_id


def test_real_scenario_state_owned_project_moves_to_owner_external_confirm() -> None:
    from app.api.v1.reviews import decide_review
    from app.api.v1.signoff import mark_has_external_audit, request_owner_external_audit_confirm

    db = _build_session()
    leader, _, _, _, third, work_order = _seed_bundle(db, "国有资产评估业务")

    decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="THIRD", action="APPROVE", comment="通过"),
        db=db,
        current_user=third,
        _={"THIRD_REVIEWER"},
    )
    db.refresh(work_order)
    assert work_order.current_status == "THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND"

    request_owner_external_audit_confirm(work_order.id, db=db, current_user=third, _={"THIRD_REVIEWER"})
    db.refresh(work_order)
    assert work_order.current_status == "WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM"

    mark_has_external_audit(work_order.id, db=db, current_user=leader, _={"PROJECT_LEADER"})
    db.refresh(work_order)
    assert work_order.current_status == "WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT"


def test_external_first_review_approve_moves_to_external_second() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review, decide_review

    db = _build_session()
    leader, _, first, second, _, work_order = _seed_bundle(db, "国有资产评估业务")
    work_order.current_status = "WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT"
    work_order.current_handler_user_id = leader.id
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_EXTERNAL_FIRST",
            version_no=1,
            is_current=True,
            origin_file_name="external-v1.zip",
            storage_key="external-v1.zip",
            file_size=120,
            uploaded_by=leader.id,
            uploaded_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    submit_review(
        payload=ReviewSubmitRequest(
            work_order_id=work_order.id,
            review_round="EXTERNAL_FIRST",
            reviewer_user_id=first.id,
            comment="提交外部一级复核",
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="EXTERNAL_FIRST", action="APPROVE", comment="通过"),
        db=db,
        current_user=first,
        _={"FIRST_REVIEWER"},
    )
    db.refresh(work_order)
    assert work_order.current_status == "EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND"
    assert work_order.current_handler_user_id == first.id


def test_external_second_recall_returns_to_external_first_selection_state() -> None:
    from app.api.v1.reviews import recall_routed_review

    db = _build_session()
    _, _, first, second, _, work_order = _seed_bundle(db, "国有资产评估业务")
    work_order.current_status = "EXTERNAL_SECOND_REVIEWING"
    work_order.current_handler_user_id = second.id
    db.commit()

    result = recall_routed_review(
        payload=ReviewRecallRoutingRequest(
            work_order_id=work_order.id,
            review_round="EXTERNAL_SECOND",
            comment="撤回外审二级复核",
        ),
        db=db,
        current_user=first,
        role_codes={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    assert result.action == "CHANGE_REVIEWER"
    assert work_order.current_status == "EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND"
    assert work_order.current_handler_user_id == first.id


def test_external_third_review_approve_moves_to_owner_signoff_upload() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    leader, _, _, _, third, work_order = _seed_bundle(db, "国有资产评估业务")
    work_order.current_status = "EXTERNAL_THIRD_REVIEWING"
    work_order.current_handler_user_id = third.id
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="EXTERNAL_THIRD", action="APPROVE", comment="通过"),
        db=db,
        current_user=third,
        _={"THIRD_REVIEWER"},
    )
    db.refresh(work_order)
    assert work_order.current_status == "WAIT_OWNER_SIGNOFF_UPLOAD"
    assert work_order.current_handler_user_id == work_order.project_leader_id


def test_final_real_scenario_owner_upload_enters_signoff_and_approves() -> None:
    from app.api.v1.signoff import enter_signoff_review, approve_signoff

    db = _build_session()
    leader, _, _, _, _, work_order = _seed_bundle(db, "非国有资产评估业务")
    chief_role = _seed_role(db, "CHIEF_APPRAISER", "首席评估师")
    chief = _seed_user(db, "chief", "Chief", [chief_role])
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    print_room = _seed_user(db, "printroom", "PrintRoom", [print_room_role])
    work_order.current_status = "WAIT_OWNER_SIGNOFF_UPLOAD"
    work_order.current_handler_user_id = leader.id
    work_order.print_room_handler_id = print_room.id
    db.commit()

    enter_signoff_review(work_order.id, db=db, current_user=leader, _={"PROJECT_LEADER"})
    db.refresh(work_order)
    assert work_order.current_status == "SIGNOFF_REVIEWING"
    assert work_order.current_handler_user_id == chief.id

    approve_signoff(work_order.id, db=db, current_user=chief, _={"CHIEF_APPRAISER"})
    db.refresh(work_order)
    assert work_order.current_status == "THIRD_APPROVED_WAIT_PRINTROOM"
    assert work_order.current_handler_user_id == print_room.id


def test_enter_signoff_review_uses_assigned_chief_appraiser_and_workbench_todo() -> None:
    from app.api.v1.signoff import enter_signoff_review
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader, _, _, _, _, work_order = _seed_bundle(db, "非国有资产评估业务")
    chief_role = _seed_role(db, "CHIEF_APPRAISER", "首席评估师")
    other_chief = _seed_user(db, "other_chief", "OtherChief", [chief_role])
    assigned_chief = _seed_user(db, "fusheng", "付胜", [chief_role])
    work_order.current_status = "WAIT_OWNER_SIGNOFF_UPLOAD"
    work_order.current_handler_user_id = leader.id
    work_order.chief_appraiser_user_id = assigned_chief.id
    db.commit()

    enter_signoff_review(work_order.id, db=db, current_user=leader, _={"PROJECT_LEADER"})

    db.refresh(work_order)
    assigned_workbench = get_workbench(db=db, current_user=assigned_chief)
    other_workbench = get_workbench(db=db, current_user=other_chief)
    assert work_order.current_status == "SIGNOFF_REVIEWING"
    assert work_order.current_handler_user_id == assigned_chief.id
    assert work_order.chief_appraiser_user_id == assigned_chief.id
    assert [item.id for item in assigned_workbench.todo_projects] == [work_order.project_id]
    assert other_workbench.todo_projects == []


def test_enter_signoff_review_ignores_hidden_super_admin_chief_role() -> None:
    from app.api.v1.signoff import enter_signoff_review
    from app.api.v1.workbench import get_workbench
    from app.api.v1.users import list_user_candidates

    db = _build_session()
    leader, _, _, _, _, work_order = _seed_bundle(db, "非国有资产评估业务")
    admin_role = _seed_role(db, "ADMIN", "管理员")
    chief_role = _seed_role(db, "CHIEF_APPRAISER", "首席评估师")
    super_admin = _seed_user(db, "zhongqin123", "系统管理员", [admin_role, chief_role])
    fusheng = _seed_user(db, "fusheng", "付胜", [chief_role])
    work_order.current_status = "WAIT_OWNER_SIGNOFF_UPLOAD"
    work_order.current_handler_user_id = leader.id
    db.commit()

    candidates = list_user_candidates("CHIEF_APPRAISER", db=db, _=leader)
    enter_signoff_review(work_order.id, db=db, current_user=leader, _={"PROJECT_LEADER"})

    db.refresh(work_order)
    fusheng_workbench = get_workbench(db=db, current_user=fusheng)
    super_admin_workbench = get_workbench(db=db, current_user=super_admin)
    assert [item.username for item in candidates.items] == ["fusheng"]
    assert work_order.current_status == "SIGNOFF_REVIEWING"
    assert work_order.current_handler_user_id == fusheng.id
    assert work_order.chief_appraiser_user_id == fusheng.id
    assert [item.id for item in fusheng_workbench.todo_projects] == [work_order.project_id]
    assert super_admin_workbench.todo_projects == []
