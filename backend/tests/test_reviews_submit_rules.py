import pytest
from datetime import date
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.review_record import ReviewRecord
from app.models.work_order_file import WorkOrderFile
from app.schemas.review import ReviewApprovalRoutingRequest, ReviewAssigneeChangeRequest, ReviewDecisionRequest, ReviewRecallRoutingRequest, ReviewSubmitRequest

def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_basic(db: Session) -> tuple[User, User, Project, WorkOrder]:
    leader = User(username="leader", password_hash="x", real_name="Leader", is_active=True)
    reviewer = User(username="reviewer", password_hash="x", real_name="Reviewer", is_active=True)
    business = User(username="business", password_hash="x", real_name="Business", is_active=True)
    db.add_all([leader, reviewer, business])
    db.flush()

    roles = [
        Role(code="PROJECT_LEADER", name="项目负责人", description="", is_system_fixed=True),
        Role(code="FIRST_REVIEWER", name="一审", description="", is_system_fixed=True),
    ]
    db.add_all(roles)
    db.flush()

    db.add(UserRole(user_id=leader.id, role_id=roles[0].id))

    project = Project(
        project_code="P-1",
        project_name="Demo",
        client_name="Client",
        project_amount=0,
        valuation_base_date=date(2026, 5, 14),
        business_user_id=business.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()

    work_order = WorkOrder(
        work_order_no="WO-1",
        project_id=project.id,
        title="WO",
        current_status="WAIT_FIRST_REVIEW_SUBMIT",
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.commit()
    return leader, reviewer, project, work_order


def _add_review_file(
    db: Session,
    work_order: WorkOrder,
    *,
    category: str = "REPORT_ZIP",
    round_name: str = "FIRST",
    uploaded_by: int | None = None,
    filename: str = "report.zip",
) -> WorkOrderFile:
    row = WorkOrderFile(
        work_order_id=work_order.id,
        file_category=category,
        business_stage=f"REVIEW_{round_name}",
        version_no=1,
        is_current=True,
        origin_file_name=filename,
        storage_key=filename,
        file_size=100,
        uploaded_by=uploaded_by or work_order.project_leader_id,
        uploaded_at=work_order.created_at,
    )
    db.add(row)
    db.commit()
    return row


def test_submit_review_rejects_reviewer_without_round_role() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)

    payload = ReviewSubmitRequest(
        work_order_id=work_order.id,
        review_round="FIRST",
        reviewer_user_id=reviewer.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        submit_review(payload=payload, db=db, current_user=leader, role_codes={"PROJECT_LEADER"})

    assert exc_info.value.status_code == 400
    assert "不具备FIRST轮审核角色" in str(exc_info.value.detail)


def test_submit_review_requires_amount_and_valuation_base_date() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review

    db = _build_session()
    leader, reviewer, project, work_order = _seed_basic(db)
    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    db.add(UserRole(user_id=reviewer.id, role_id=first_role.id))
    project.project_amount = None
    project.valuation_base_date = None
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        submit_review(
            payload=ReviewSubmitRequest(
                work_order_id=work_order.id,
                review_round="FIRST",
                reviewer_user_id=reviewer.id,
            ),
            db=db,
            current_user=leader,
            role_codes={"PROJECT_LEADER"},
        )

    assert exc_info.value.status_code == 400
    assert "项目金额和评估基准日" in str(exc_info.value.detail)


def test_submit_review_accepts_reviewer_with_round_role() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    db.add(UserRole(user_id=reviewer.id, role_id=first_role.id))
    db.commit()
    _add_review_file(db, work_order, uploaded_by=leader.id)

    payload = ReviewSubmitRequest(
        work_order_id=work_order.id,
        review_round="FIRST",
        reviewer_user_id=reviewer.id,
    )

    result = submit_review(payload=payload, db=db, current_user=leader, role_codes={"PROJECT_LEADER"})
    assert result.reviewer_user_id == reviewer.id
    assert result.review_round == "FIRST"


def test_rejected_review_can_be_resubmitted_to_same_round() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    db.add(UserRole(user_id=reviewer.id, role_id=first_role.id))
    work_order.current_status = "FIRST_REVIEW_REJECTED"
    work_order.current_handler_user_id = leader.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()
    _add_review_file(db, work_order, uploaded_by=leader.id, filename="report-v2.zip")

    result = submit_review(
        payload=ReviewSubmitRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=reviewer.id,
            comment="已回复意见",
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert result.action == "SUBMIT"
    assert work_order.current_status == "FIRST_REVIEWING"
    assert work_order.current_handler_user_id == reviewer.id


def test_rejected_review_assignee_change_takes_effect_on_resubmit() -> None:
    from app.api.v1.reviews import _change_reviewer_after_reject_impl as change_reviewer_after_reject, _submit_review_impl as submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    new_reviewer = User(username="reviewer2", password_hash="x", real_name="Reviewer2", is_active=True)
    db.add(new_reviewer)
    db.flush()

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    db.add(UserRole(user_id=reviewer.id, role_id=first_role.id))
    db.add(UserRole(user_id=new_reviewer.id, role_id=first_role.id))
    work_order.current_status = "FIRST_REVIEW_REJECTED"
    work_order.current_handler_user_id = leader.id
    work_order.first_reviewer_id = reviewer.id
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=reviewer.id,
            action="REJECT_RETURN",
            comment="退回",
            acted_at=work_order.created_at,
        )
    )
    db.commit()
    _add_review_file(db, work_order, uploaded_by=leader.id, filename="report-v2.zip")

    record = change_reviewer_after_reject(
        payload=ReviewAssigneeChangeRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=new_reviewer.id,
            comment="更换老师",
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert record.action == "CHANGE_REVIEWER"
    assert work_order.first_reviewer_id == reviewer.id
    assert work_order.current_handler_user_id == leader.id

    result = submit_review(
        payload=ReviewSubmitRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=new_reviewer.id,
            comment="沿用文件重新提交",
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert result.reviewer_user_id == new_reviewer.id
    assert work_order.first_reviewer_id == new_reviewer.id
    assert work_order.current_handler_user_id == new_reviewer.id


def test_pending_reviewer_change_does_not_override_plain_resubmit() -> None:
    from app.api.v1.reviews import _change_reviewer_after_reject_impl as change_reviewer_after_reject, _submit_review_impl as submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    new_reviewer = User(username="reviewer2", password_hash="x", real_name="Reviewer2", is_active=True)
    db.add(new_reviewer)
    db.flush()

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    db.add(UserRole(user_id=reviewer.id, role_id=first_role.id))
    db.add(UserRole(user_id=new_reviewer.id, role_id=first_role.id))
    work_order.current_status = "FIRST_REVIEW_REJECTED"
    work_order.current_handler_user_id = leader.id
    work_order.first_reviewer_id = reviewer.id
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=reviewer.id,
            action="REJECT_RETURN",
            comment="退回",
            acted_at=work_order.created_at,
        )
    )
    db.commit()
    _add_review_file(db, work_order, uploaded_by=leader.id, filename="report-v2.zip")

    change_reviewer_after_reject(
        payload=ReviewAssigneeChangeRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=new_reviewer.id,
            comment="更换老师",
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    result = submit_review(
        payload=ReviewSubmitRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=reviewer.id,
            comment="普通回复",
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert result.reviewer_user_id == reviewer.id
    assert work_order.first_reviewer_id == reviewer.id
    assert work_order.current_handler_user_id == reviewer.id


def test_rejected_review_assignee_change_only_once_per_rejection() -> None:
    from app.api.v1.reviews import _change_reviewer_after_reject_impl as change_reviewer_after_reject

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    new_reviewer = User(username="reviewer2", password_hash="x", real_name="Reviewer2", is_active=True)
    another_reviewer = User(username="reviewer3", password_hash="x", real_name="Reviewer3", is_active=True)
    db.add_all([new_reviewer, another_reviewer])
    db.flush()

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    for user in [reviewer, new_reviewer, another_reviewer]:
        db.add(UserRole(user_id=user.id, role_id=first_role.id))
    work_order.current_status = "FIRST_REVIEW_REJECTED"
    work_order.current_handler_user_id = leader.id
    work_order.first_reviewer_id = reviewer.id
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=reviewer.id,
            action="REJECT_RETURN",
            comment="退回",
            acted_at=work_order.created_at,
        )
    )
    db.commit()

    change_reviewer_after_reject(
        payload=ReviewAssigneeChangeRequest(work_order_id=work_order.id, review_round="FIRST", reviewer_user_id=new_reviewer.id),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    with pytest.raises(HTTPException) as exc_info:
        change_reviewer_after_reject(
            payload=ReviewAssigneeChangeRequest(work_order_id=work_order.id, review_round="FIRST", reviewer_user_id=another_reviewer.id),
            db=db,
            current_user=leader,
            role_codes={"PROJECT_LEADER"},
        )

    assert exc_info.value.status_code == 400
    assert "已变更过审核人" in str(exc_info.value.detail)


def test_first_review_approve_moves_to_second_submit() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    _, reviewer, _, work_order = _seed_basic(db)
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()

    result = decide_review(
        payload=ReviewDecisionRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            action="APPROVE",
        ),
        db=db,
        current_user=reviewer,
        _={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    assert result.comment == "审核通过"
    assert work_order.current_status == "FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND"
    assert work_order.current_handler_user_id == reviewer.id


def test_first_review_approve_auto_advances_to_second_when_project_party_uploaded_report() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    second_reviewer = User(username="reviewer_second", password_hash="x", real_name="ReviewerSecond", is_active=True)
    db.add(second_reviewer)
    db.flush()
    second_role = Role(code="SECOND_REVIEWER", name="二审", description="", is_system_fixed=True)
    db.add(second_role)
    db.flush()
    db.add(UserRole(user_id=second_reviewer.id, role_id=second_role.id))
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    work_order.second_reviewer_id = second_reviewer.id
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_FIRST",
            version_no=1,
            is_current=True,
            origin_file_name="report-v1.zip",
            storage_key="report-v1.zip",
            file_size=100,
            uploaded_by=leader.id,
            uploaded_at=work_order.created_at,
        )
    )
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            action="APPROVE",
        ),
        db=db,
        current_user=reviewer,
        _={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    latest_submit = db.query(ReviewRecord).filter(ReviewRecord.work_order_id == work_order.id, ReviewRecord.action == "SUBMIT", ReviewRecord.review_round == "SECOND").first()
    cloned_file = db.query(WorkOrderFile).filter(
        WorkOrderFile.work_order_id == work_order.id,
        WorkOrderFile.business_stage == "REVIEW_SECOND",
        WorkOrderFile.file_category == "REPORT_ZIP",
    ).first()
    assert work_order.current_status == "FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND"
    assert work_order.current_handler_user_id == reviewer.id
    assert latest_submit is None
    assert cloned_file is not None
    assert cloned_file.origin_file_name == "report-v1.zip"


def test_third_review_approve_moves_to_owner_signoff_upload_for_non_state_owned_project() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    _, reviewer, _, work_order = _seed_basic(db)
    work_order.current_status = "THIRD_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.third_reviewer_id = reviewer.id
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(
            work_order_id=work_order.id,
            review_round="THIRD",
            action="APPROVE",
        ),
        db=db,
        current_user=reviewer,
        _={"THIRD_REVIEWER"},
    )

    db.refresh(work_order)
    assert work_order.current_status == "WAIT_OWNER_SIGNOFF_UPLOAD"
    assert work_order.current_handler_user_id == work_order.project_leader_id


def test_workbench_shows_current_reviewer_todo_even_when_user_created_project() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = User(username="leader", password_hash="x", real_name="Leader", is_active=True)
    reviewer = User(username="reviewer", password_hash="x", real_name="Reviewer", is_active=True)
    db.add_all([leader, reviewer])
    db.flush()

    project = Project(
        project_code="P-REVIEW-TODO",
        project_name="Review Todo",
        client_name="Client",
        business_user_id=reviewer.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()

    work_order = WorkOrder(
        work_order_no="WO-REVIEW-TODO",
        project_id=project.id,
        title="WO",
        current_status="FIRST_REVIEWING",
        current_handler_user_id=reviewer.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        first_reviewer_id=reviewer.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.commit()

    result = get_workbench(db=db, current_user=reviewer)

    assert [item.id for item in result.todo_projects] == [project.id]



def test_first_review_route_back_to_project_leader_after_approve() -> None:
    from app.api.v1.reviews import decide_review, route_approved_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            action="APPROVE",
        ),
        db=db,
        current_user=reviewer,
        _={"FIRST_REVIEWER"},
    )

    result = route_approved_review(
        payload=ReviewApprovalRoutingRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            route_mode="RETURN_TO_PROJECT_LEADER",
        ),
        db=db,
        current_user=reviewer,
        role_codes={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    assert work_order.current_status == "FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND"
    assert work_order.current_handler_user_id == work_order.project_leader_id
    assert result.action == "CHANGE_REVIEWER"


def test_project_leader_cannot_choose_route_after_first_review_approve() -> None:
    from app.api.v1.reviews import decide_review, route_approved_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            action="APPROVE",
        ),
        db=db,
        current_user=reviewer,
        _={"FIRST_REVIEWER"},
    )

    with pytest.raises(HTTPException) as exc_info:
        route_approved_review(
            payload=ReviewApprovalRoutingRequest(
                work_order_id=work_order.id,
                review_round="FIRST",
                route_mode="RETURN_TO_PROJECT_LEADER",
            ),
            db=db,
            current_user=leader,
            role_codes={"PROJECT_LEADER"},
        )

    assert exc_info.value.status_code == 403


def test_first_reviewer_directly_routes_to_second_reviewer_after_approve() -> None:
    from app.api.v1.reviews import decide_review, route_approved_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    second_reviewer = User(username="reviewer_second", password_hash="x", real_name="ReviewerSecond", is_active=True)
    db.add(second_reviewer)
    db.flush()
    second_role = Role(code="SECOND_REVIEWER", name="二审", description="", is_system_fixed=True)
    db.add(second_role)
    db.flush()
    db.add(UserRole(user_id=second_reviewer.id, role_id=second_role.id))
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()
    _add_review_file(db, work_order, uploaded_by=leader.id, filename="report-approved.zip")

    approve = decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="FIRST", action="APPROVE"),
        db=db,
        current_user=reviewer,
        _={"FIRST_REVIEWER"},
    )
    assert approve.action == "APPROVE"

    route_approved_review(
        payload=ReviewApprovalRoutingRequest(
            work_order_id=work_order.id,
            review_round="FIRST",
            route_mode="REVIEWER_SELECT_NEXT",
            reviewer_user_id=second_reviewer.id,
        ),
        db=db,
        current_user=reviewer,
        role_codes={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    submit_record = db.query(ReviewRecord).filter(
        ReviewRecord.work_order_id == work_order.id,
        ReviewRecord.review_round == "SECOND",
        ReviewRecord.action == "SUBMIT",
    ).first()
    assert work_order.current_status == "SECOND_REVIEWING"
    assert work_order.current_handler_user_id == second_reviewer.id
    assert work_order.second_reviewer_id == second_reviewer.id
    assert submit_record is not None


def test_first_review_reviewer_select_status_maps_to_second_review_step() -> None:
    from app.services.project_flow import normalize_project_step

    assert normalize_project_step("FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND", archived=False) == "二审"
    assert normalize_project_step("SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD", archived=False) == "三审"


def test_project_leader_can_submit_second_review_without_reupload_after_first_approved() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review

    db = _build_session()
    leader, first_reviewer, _, work_order = _seed_basic(db)
    second_reviewer = User(username="reviewer_second", password_hash="x", real_name="ReviewerSecond", is_active=True)
    db.add(second_reviewer)
    db.flush()

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    second_role = Role(code="SECOND_REVIEWER", name="二审", description="", is_system_fixed=True)
    assert first_role is not None
    db.add(second_role)
    db.flush()
    db.add(UserRole(user_id=first_reviewer.id, role_id=first_role.id))
    db.add(UserRole(user_id=second_reviewer.id, role_id=second_role.id))

    work_order.current_status = "FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND"
    work_order.current_handler_user_id = leader.id
    work_order.first_reviewer_id = first_reviewer.id
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_SECOND",
            version_no=1,
            is_current=True,
            origin_file_name="report-second.zip",
            storage_key="report-second.zip",
            file_size=100,
            uploaded_by=leader.id,
            uploaded_at=work_order.created_at,
        )
    )
    db.commit()

    result = submit_review(
        payload=ReviewSubmitRequest(
            work_order_id=work_order.id,
            review_round="SECOND",
            reviewer_user_id=second_reviewer.id,
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert result.review_round == "SECOND"
    assert result.reviewer_user_id == second_reviewer.id
    assert work_order.current_status == "SECOND_REVIEWING"
    assert work_order.current_handler_user_id == second_reviewer.id


def test_project_leader_can_submit_third_review_without_reupload_after_second_approved() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review

    db = _build_session()
    leader, first_reviewer, _, work_order = _seed_basic(db)
    second_reviewer = User(username="reviewer_second", password_hash="x", real_name="ReviewerSecond", is_active=True)
    third_reviewer = User(username="reviewer_third", password_hash="x", real_name="ReviewerThird", is_active=True)
    db.add_all([second_reviewer, third_reviewer])
    db.flush()

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    second_role = Role(code="SECOND_REVIEWER", name="二审", description="", is_system_fixed=True)
    third_role = Role(code="THIRD_REVIEWER", name="三审", description="", is_system_fixed=True)
    assert first_role is not None
    db.add_all([second_role, third_role])
    db.flush()
    db.add(UserRole(user_id=first_reviewer.id, role_id=first_role.id))
    db.add(UserRole(user_id=second_reviewer.id, role_id=second_role.id))
    db.add(UserRole(user_id=third_reviewer.id, role_id=third_role.id))

    work_order.current_status = "SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD"
    work_order.current_handler_user_id = leader.id
    work_order.first_reviewer_id = first_reviewer.id
    work_order.second_reviewer_id = second_reviewer.id
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_THIRD",
            version_no=1,
            is_current=True,
            origin_file_name="report-third.zip",
            storage_key="report-third.zip",
            file_size=100,
            uploaded_by=leader.id,
            uploaded_at=work_order.created_at,
        )
    )
    db.commit()

    result = submit_review(
        payload=ReviewSubmitRequest(
            work_order_id=work_order.id,
            review_round="THIRD",
            reviewer_user_id=third_reviewer.id,
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert result.review_round == "THIRD"
    assert result.reviewer_user_id == third_reviewer.id
    assert work_order.current_status == "THIRD_REVIEWING"
    assert work_order.current_handler_user_id == third_reviewer.id


def test_external_second_candidates_are_fixed_to_original_second_reviewer() -> None:
    from app.api.v1.reviews import list_review_candidates

    db = _build_session()
    leader, reviewer, project, work_order = _seed_basic(db)
    second_reviewer = User(username="reviewer_second", password_hash="x", real_name="ReviewerSecond", is_active=True)
    db.add(second_reviewer)
    db.flush()
    second_role = Role(code="SECOND_REVIEWER", name="二审", description="", is_system_fixed=True)
    db.add(second_role)
    db.flush()
    db.add(UserRole(user_id=second_reviewer.id, role_id=second_role.id))
    work_order.current_status = "EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    work_order.second_reviewer_id = second_reviewer.id
    db.commit()

    result = list_review_candidates(
        work_order_id=work_order.id,
        review_round="EXTERNAL_SECOND",
        db=db,
        current_user=reviewer,
        role_codes={"FIRST_REVIEWER"},
    )

    assert [(item.user_id, item.real_name) for item in result.items] == [(second_reviewer.id, "ReviewerSecond")]


def test_external_first_approve_enters_recall_or_second_state() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    work_order.current_status = "EXTERNAL_FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()

    decide_review(
        payload=ReviewDecisionRequest(
            work_order_id=work_order.id,
            review_round="EXTERNAL_FIRST",
            action="APPROVE",
        ),
        db=db,
        current_user=reviewer,
        _={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    assert work_order.current_status == "EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND"
    assert work_order.current_handler_user_id == reviewer.id


def test_recall_routed_second_review_returns_to_first_reviewer_selection_state() -> None:
    from app.api.v1.reviews import recall_routed_review

    db = _build_session()
    leader, first_reviewer, _, work_order = _seed_basic(db)
    second_reviewer = User(username="reviewer_second", password_hash="x", real_name="ReviewerSecond", is_active=True)
    db.add(second_reviewer)
    db.flush()
    second_role = Role(code="SECOND_REVIEWER", name="二审", description="", is_system_fixed=True)
    db.add(second_role)
    db.flush()
    db.add(UserRole(user_id=second_reviewer.id, role_id=second_role.id))
    work_order.current_status = "SECOND_REVIEWING"
    work_order.current_handler_user_id = second_reviewer.id
    work_order.first_reviewer_id = first_reviewer.id
    work_order.second_reviewer_id = second_reviewer.id
    db.commit()

    result = recall_routed_review(
        payload=ReviewRecallRoutingRequest(
            work_order_id=work_order.id,
            review_round="SECOND",
            comment="撤回转交二审",
        ),
        db=db,
        current_user=first_reviewer,
        role_codes={"FIRST_REVIEWER"},
    )

    db.refresh(work_order)
    assert result.action == "CHANGE_REVIEWER"
    assert work_order.current_status == "FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND"
    assert work_order.current_handler_user_id == first_reviewer.id


def test_reject_return_requires_opinion_file_or_comment() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    _, reviewer, _, work_order = _seed_basic(db)
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        decide_review(
            payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="FIRST", action="REJECT_RETURN"),
            db=db,
            current_user=reviewer,
            _={"FIRST_REVIEWER"},
        )

    assert exc_info.value.status_code == 400
    assert "审核意见文件或审核备注" in str(exc_info.value.detail)


def test_reject_return_with_opinion_file_generates_default_comment() -> None:
    from app.api.v1.reviews import decide_review

    db = _build_session()
    _, reviewer, _, work_order = _seed_basic(db)
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = reviewer.id
    work_order.first_reviewer_id = reviewer.id
    db.commit()
    _add_review_file(db, work_order, category="REVIEW_OPINION", uploaded_by=reviewer.id, filename="first-opinion.docx")

    result = decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="FIRST", action="REJECT_RETURN"),
        db=db,
        current_user=reviewer,
        _={"FIRST_REVIEWER"},
    )

    assert result.comment == "FIRST审核意见返回修改"


def test_rejected_resubmit_requires_reply_file_or_comment() -> None:
    from app.api.v1.reviews import _submit_review_impl as submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)
    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    db.add(UserRole(user_id=reviewer.id, role_id=first_role.id))
    work_order.current_status = "FIRST_REVIEW_REJECTED"
    work_order.current_handler_user_id = leader.id
    work_order.first_reviewer_id = reviewer.id
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round="FIRST",
            reviewer_user_id=reviewer.id,
            action="REJECT_RETURN",
            comment="退回",
            acted_at=work_order.created_at,
        )
    )
    db.commit()
    _add_review_file(db, work_order, uploaded_by=leader.id, filename="report-v2.zip")

    with pytest.raises(HTTPException) as exc_info:
        submit_review(
            payload=ReviewSubmitRequest(work_order_id=work_order.id, review_round="FIRST", reviewer_user_id=reviewer.id),
            db=db,
            current_user=leader,
            role_codes={"PROJECT_LEADER"},
        )

    assert exc_info.value.status_code == 400
    assert "审核意见回复文件或送审备注" in str(exc_info.value.detail)
