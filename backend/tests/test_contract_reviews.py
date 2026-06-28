from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.review import ReviewSubmitRequest
from app.schemas.contract_review import (
    ContractReviewApproveTransferRequest,
    ContractReviewDecisionRequest,
    ContractReviewSubmitRequest,
    ContractReviewTransferApprovedRequest,
)
from app.schemas.print_room import PrintRoomRollbackRequest


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_role(db: Session, code: str, name: str) -> Role:
    role = Role(code=code, name=name, description="", is_system_fixed=True)
    db.add(role)
    db.flush()
    return role


def _seed_user(db: Session, username: str, roles: list[Role]) -> User:
    user = User(username=username, password_hash="x", real_name=username.title(), is_active=True)
    db.add(user)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def _seed_project_and_work_order(db: Session, creator: User, leader: User) -> tuple[Project, WorkOrder]:
    project = Project(
        project_code="P-CONTRACT",
        undertaking_unit="中勤",
        project_name="Demo",
        client_name="Client",
        report_type="评估报告",
        business_salesman="Sales",
        project_amount=1000,
        valuation_base_date=date(2026, 6, 28),
        business_user_id=creator.id,
        project_leader_id=leader.id,
        project_source="INTERNAL",
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no="WO-CONTRACT",
        project_id=project.id,
        title="WO",
        current_status="WAIT_CONTRACT_REVIEW_SUBMIT",
        current_handler_user_id=leader.id,
        initiator_user_id=creator.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="CONTRACT_DRAFT",
            business_stage="CONTRACT_DRAFT",
            version_no=1,
            is_current=True,
            origin_file_name="contract.pdf",
            storage_key="contract.pdf",
            uploaded_by=leader.id,
            uploaded_at=work_order.created_at,
        )
    )
    db.commit()
    return project, work_order


def test_submit_contract_review_requires_contract_reviewer_role() -> None:
    from app.api.v1.contract_reviews import submit_contract_review

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    leader = _seed_user(db, "leader", [leader_role])
    reviewer = _seed_user(db, "reviewer", [])
    _, work_order = _seed_project_and_work_order(db, leader, leader)

    with pytest.raises(HTTPException) as exc_info:
        submit_contract_review(
            payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=reviewer.id),
            db=db,
            current_user=leader,
        )

    assert exc_info.value.status_code == 400


def test_contract_review_approve_moves_to_contract_approved() -> None:
    from app.api.v1.contract_reviews import approve_contract_review, submit_contract_review

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    reviewer_role = _seed_role(db, "CONTRACT_REVIEWER", "合同审核人")
    leader = _seed_user(db, "leader", [leader_role])
    reviewer = _seed_user(db, "reviewer", [reviewer_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)

    submit_record = submit_contract_review(
        payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=reviewer.id),
        db=db,
        current_user=leader,
    )

    result = approve_contract_review(
        record_id=submit_record.id,
        payload=ContractReviewDecisionRequest(comment="ok"),
        db=db,
        current_user=reviewer,
        _={"CONTRACT_REVIEWER"},
    )

    db.refresh(work_order)
    assert result.action_type == "APPROVE_CONTRACT"
    assert work_order.current_status == "CONTRACT_APPROVED"
    assert work_order.current_handler_user_id == work_order.project_leader_id


def test_contract_review_approve_and_transfer_moves_to_print_room() -> None:
    from app.api.v1.contract_reviews import approve_and_transfer_contract_review, submit_contract_review
    from app.services.contract_print_room_flow import get_contract_print_room_status

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    reviewer_role = _seed_role(db, "CONTRACT_REVIEWER", "合同审核人")
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    leader = _seed_user(db, "leader", [leader_role])
    reviewer = _seed_user(db, "reviewer", [reviewer_role])
    print_room = _seed_user(db, "printroom", [print_room_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)

    submit_record = submit_contract_review(
        payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=reviewer.id),
        db=db,
        current_user=leader,
    )

    result = approve_and_transfer_contract_review(
        record_id=submit_record.id,
        payload=ContractReviewApproveTransferRequest(comment="ok", print_room_handler_id=print_room.id),
        db=db,
        current_user=reviewer,
        _={"CONTRACT_REVIEWER"},
    )

    db.refresh(work_order)
    assert result.action_type == "APPROVE_AND_TRANSFER_PRINT_ROOM"
    assert work_order.current_status == "CONTRACT_APPROVED"
    assert work_order.current_handler_user_id == leader.id
    assert get_contract_print_room_status(db, work_order) == "WAIT_PRINT_ROOM_PROCESS"
    assert work_order.print_room_handler_id == print_room.id


def test_contract_approved_can_be_transferred_to_print_room() -> None:
    from app.api.v1.contract_reviews import approve_contract_review, submit_contract_review, transfer_approved_contract_to_print_room
    from app.services.contract_print_room_flow import get_contract_print_room_status

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    reviewer_role = _seed_role(db, "CONTRACT_REVIEWER", "合同审核人")
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    leader = _seed_user(db, "leader", [leader_role])
    reviewer = _seed_user(db, "reviewer", [reviewer_role])
    print_room = _seed_user(db, "printroom", [print_room_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)

    submit_record = submit_contract_review(
        payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=reviewer.id),
        db=db,
        current_user=leader,
    )
    approve_contract_review(
        record_id=submit_record.id,
        payload=ContractReviewDecisionRequest(comment="ok"),
        db=db,
        current_user=reviewer,
        _={"CONTRACT_REVIEWER"},
    )

    result = transfer_approved_contract_to_print_room(
        work_order_id=work_order.id,
        payload=ContractReviewTransferApprovedRequest(print_room_handler_id=print_room.id, comment="transfer"),
        db=db,
        current_user=leader,
    )

    db.refresh(work_order)
    assert result.action_type == "TRANSFER_APPROVED_PRINT_ROOM"
    assert work_order.current_status == "CONTRACT_APPROVED"
    assert work_order.current_handler_user_id == leader.id
    assert get_contract_print_room_status(db, work_order) == "WAIT_PRINT_ROOM_PROCESS"
    assert work_order.print_room_handler_id == print_room.id


def test_contract_reviewer_can_transfer_approved_contract_to_print_room() -> None:
    from app.api.v1.contract_reviews import approve_contract_review, submit_contract_review, transfer_approved_contract_to_print_room
    from app.services.contract_print_room_flow import get_contract_print_room_status

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    reviewer_role = _seed_role(db, "CONTRACT_REVIEWER", "合同审核人")
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    leader = _seed_user(db, "leader", [leader_role])
    reviewer = _seed_user(db, "reviewer", [reviewer_role])
    print_room = _seed_user(db, "printroom", [print_room_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)

    submit_record = submit_contract_review(
        payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=reviewer.id),
        db=db,
        current_user=leader,
    )
    approve_contract_review(
        record_id=submit_record.id,
        payload=ContractReviewDecisionRequest(comment="ok"),
        db=db,
        current_user=reviewer,
        _={"CONTRACT_REVIEWER"},
    )

    result = transfer_approved_contract_to_print_room(
        work_order_id=work_order.id,
        payload=ContractReviewTransferApprovedRequest(print_room_handler_id=print_room.id, comment="transfer"),
        db=db,
        current_user=reviewer,
    )

    db.refresh(work_order)
    assert result.action_type == "TRANSFER_APPROVED_PRINT_ROOM"
    assert work_order.current_status == "CONTRACT_APPROVED"
    assert work_order.current_handler_user_id == leader.id
    assert get_contract_print_room_status(db, work_order) == "WAIT_PRINT_ROOM_PROCESS"
    assert work_order.print_room_handler_id == print_room.id


def test_first_review_can_start_while_contract_print_room_is_pending() -> None:
    from app.api.v1.contract_reviews import approve_contract_review, submit_contract_review, transfer_approved_contract_to_print_room
    from app.api.v1.print_room import send_contract_to_project_leader
    from app.api.v1.reviews import _submit_review_impl as submit_review
    from app.services.contract_print_room_flow import get_contract_print_room_status

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    reviewer_role = _seed_role(db, "CONTRACT_REVIEWER", "合同审核人")
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    first_role = _seed_role(db, "FIRST_REVIEWER", "一审")
    leader = _seed_user(db, "leader", [leader_role])
    reviewer = _seed_user(db, "reviewer", [reviewer_role])
    print_room = _seed_user(db, "printroom", [print_room_role])
    first = _seed_user(db, "first", [first_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)

    submit_record = submit_contract_review(
        payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=reviewer.id),
        db=db,
        current_user=leader,
    )
    approve_contract_review(
        record_id=submit_record.id,
        payload=ContractReviewDecisionRequest(comment="ok"),
        db=db,
        current_user=reviewer,
        _={"CONTRACT_REVIEWER"},
    )
    transfer_approved_contract_to_print_room(
        work_order_id=work_order.id,
        payload=ContractReviewTransferApprovedRequest(print_room_handler_id=print_room.id, comment="transfer"),
        db=db,
        current_user=leader,
    )
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT_ZIP",
            business_stage="REVIEW_FIRST",
            version_no=1,
            is_current=True,
            origin_file_name="review.zip",
            storage_key="review.zip",
            uploaded_by=leader.id,
            uploaded_at=work_order.created_at,
        )
    )
    db.commit()

    submit_review(
        payload=ReviewSubmitRequest(work_order_id=work_order.id, review_round="FIRST", reviewer_user_id=first.id),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )
    db.refresh(work_order)
    assert work_order.current_status == "FIRST_REVIEWING"
    assert get_contract_print_room_status(db, work_order) == "WAIT_PRINT_ROOM_PROCESS"

    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="STAMPED_CONTRACT_SCAN",
            business_stage="PRINT_ROOM_CONTRACT_SCAN",
            version_no=1,
            is_current=True,
            origin_file_name="stamped.pdf",
            storage_key="stamped.pdf",
            uploaded_by=print_room.id,
            uploaded_at=work_order.created_at,
        )
    )
    db.commit()
    send_contract_to_project_leader(
        payload=PrintRoomRollbackRequest(work_order_id=work_order.id, remark="scan ready"),
        db=db,
        current_user=print_room,
        _={"PRINT_ROOM"},
    )

    db.refresh(work_order)
    assert work_order.current_status == "FIRST_REVIEWING"
    assert get_contract_print_room_status(db, work_order) == "WAIT_PROJECT_LEADER_CONTRACT_CONFIRM"


def test_project_flow_exposes_leader_for_contract_print_room_confirmation() -> None:
    from app.api.v1.projects import get_project_flow

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    leader = _seed_user(db, "leader", [leader_role])
    project, work_order = _seed_project_and_work_order(db, leader, leader)
    work_order.current_status = "WAIT_PROJECT_LEADER_CONTRACT_CONFIRM"
    work_order.current_handler_user_id = leader.id
    db.commit()

    result = get_project_flow(project.id, db=db, current_user=leader)

    assert result.project.project_leader_id == leader.id
    assert result.current_work_order_status == "WAIT_PROJECT_LEADER_CONTRACT_CONFIRM"
    assert result.current_handler_user_id == leader.id
    assert result.project.current_step == "合同初稿审核"


def test_contract_project_leader_without_global_role_can_confirm_complete() -> None:
    from app.api.v1.print_room import confirm_contract_complete

    db = _build_session()
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    leader = _seed_user(db, "leader", [])
    print_room = _seed_user(db, "printroom", [print_room_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)
    work_order.current_status = "WAIT_PROJECT_LEADER_CONTRACT_CONFIRM"
    work_order.current_handler_user_id = leader.id
    work_order.print_room_handler_id = print_room.id
    db.commit()

    confirm_contract_complete(
        payload=PrintRoomRollbackRequest(work_order_id=work_order.id, remark="ok"),
        db=db,
        current_user=leader,
    )

    db.refresh(work_order)
    assert work_order.current_status == "CONTRACT_PROCESS_COMPLETED"
    assert work_order.current_handler_user_id == leader.id


def test_contract_project_leader_without_global_role_can_return_to_print_room() -> None:
    from app.api.v1.print_room import return_contract_to_print_room

    db = _build_session()
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    leader = _seed_user(db, "leader", [])
    print_room = _seed_user(db, "printroom", [print_room_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)
    work_order.current_status = "WAIT_PROJECT_LEADER_CONTRACT_CONFIRM"
    work_order.current_handler_user_id = leader.id
    work_order.print_room_handler_id = print_room.id
    db.commit()

    return_contract_to_print_room(
        payload=PrintRoomRollbackRequest(work_order_id=work_order.id, remark="need fix"),
        db=db,
        current_user=leader,
    )

    db.refresh(work_order)
    assert work_order.current_status == "WAIT_PRINT_ROOM_PROCESS"
    assert work_order.current_handler_user_id == print_room.id


def test_contract_review_reject_moves_back_to_project_side() -> None:
    from app.api.v1.contract_reviews import reject_contract_review, submit_contract_review

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    reviewer_role = _seed_role(db, "CONTRACT_REVIEWER", "合同审核人")
    leader = _seed_user(db, "leader", [leader_role])
    reviewer = _seed_user(db, "reviewer", [reviewer_role])
    _, work_order = _seed_project_and_work_order(db, leader, leader)

    submit_record = submit_contract_review(
        payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=reviewer.id),
        db=db,
        current_user=leader,
    )

    result = reject_contract_review(
        record_id=submit_record.id,
        payload=ContractReviewDecisionRequest(comment="need fix"),
        db=db,
        current_user=reviewer,
        _={"CONTRACT_REVIEWER"},
    )

    db.refresh(work_order)
    assert result.action_type == "REJECT_CONTRACT"
    assert work_order.current_status == "CONTRACT_REJECTED"
    assert work_order.current_handler_user_id == work_order.project_leader_id
