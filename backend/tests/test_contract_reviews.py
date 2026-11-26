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


@pytest.mark.parametrize("parallel", [False, True])
def test_replace_approved_contract_twice(tmp_path, monkeypatch, parallel):
    from io import BytesIO
    from fastapi import UploadFile
    from app.api.v1 import contract_reviews as api
    from app.api.v1.files import download_work_order_file
    from app.core.config import settings
    from app.services.contract_revision import contract_status
    from app.services.contract_print_room_flow import get_contract_print_room_status

    monkeypatch.setattr(settings, "local_storage_dir", str(tmp_path))
    db = _build_session()
    leader = _seed_user(db, "leader", [])
    reviewer = _seed_user(db, "reviewer", [_seed_role(db, "CONTRACT_REVIEWER", "Reviewer")])
    printer = _seed_user(db, "printer", [_seed_role(db, "PRINT_ROOM", "Print")])
    other = _seed_user(db, "other", [])
    _, order = _seed_project_and_work_order(db, leader, leader)
    record = api.submit_contract_review(ContractReviewSubmitRequest(work_order_id=order.id,
                                        reviewer_user_id=reviewer.id), db, leader)
    (tmp_path / "contract.pdf").write_bytes(b"original")
    for version in (2, 3):
        approval = api.approve_and_transfer_contract_review(record.id,
            ContractReviewApproveTransferRequest(print_room_handler_id=printer.id), db, reviewer, set())
        if parallel:
            order.current_status = "FIRST_REVIEWING"
            order.current_handler_user_id = other.id
            db.commit()
        old = db.get(WorkOrderFile, record.contract_file_id)
        old_path = tmp_path / old.storage_key
        def revise(user, state="WAIT_PRINT_ROOM_PROCESS", data=b"replacement"):
            return api.revise_approved_contract(order.id, approval.id, state,
                UploadFile(filename="contract.pdf", file=BytesIO(data)), db, user)
        for who, state, data, code in [
            (other, "WAIT_PRINT_ROOM_PROCESS", b"new", 403),
            (leader, "NONE", b"new", 409),
            (leader, "WAIT_PRINT_ROOM_PROCESS", b"", 400),
        ]:
            with pytest.raises(HTTPException) as exc:
                revise(who, state, data)
            db.rollback()
            assert exc.value.status_code == code
            assert old.is_current and old_path.exists()
        previous_submit = record
        record = revise(leader)
        assert not old_path.exists()
        assert not old.is_current
        assert record.reviewer_user_id == reviewer.id
        assert contract_status(db, order) == "CONTRACT_REVIEWING"
        assert get_contract_print_room_status(db, order) is None
        assert order.current_handler_user_id == (other.id if parallel else reviewer.id)
        if parallel:
            assert order.current_status == "FIRST_REVIEWING"
        new = db.get(WorkOrderFile, record.contract_file_id)
        assert new.version_no == version
        assert (tmp_path / new.storage_key).read_bytes() == b"replacement"
        with pytest.raises(HTTPException) as exc:
            download_work_order_file(old.id, db, leader)
        assert exc.value.status_code == 410
        with pytest.raises(HTTPException):
            revise(leader)
        with pytest.raises(HTTPException):
            api.approve_contract_review(previous_submit.id, ContractReviewDecisionRequest(), db, reviewer, set())
        db.rollback()


def test_revision_guards_and_cleanup_retry(tmp_path, monkeypatch):
    from io import BytesIO
    from pathlib import Path
    from fastapi import UploadFile
    from app.api.v1 import contract_reviews as api
    from app.core.config import settings
    from app.services.contract_revision import PENDING_DELETE, DELETED, purge_replaced_contracts

    monkeypatch.setattr(settings, "local_storage_dir", str(tmp_path))
    db = _build_session()
    leader = _seed_user(db, "leader", [])
    reviewer = _seed_user(db, "reviewer", [_seed_role(db, "CONTRACT_REVIEWER", "Reviewer")])
    _, order = _seed_project_and_work_order(db, leader, leader)
    submit = api.submit_contract_review(ContractReviewSubmitRequest(work_order_id=order.id,
                                        reviewer_user_id=reviewer.id), db, leader)
    approval = api.approve_contract_review(submit.id, ContractReviewDecisionRequest(), db, reviewer, set())
    old = db.get(WorkOrderFile, submit.contract_file_id)
    original = tmp_path / old.storage_key
    original.write_bytes(b"original")

    def revise():
        upload = UploadFile(filename="new.pdf", file=BytesIO(b"new"))
        return api.revise_approved_contract(order.id, approval.id, "NONE", upload, db, leader)

    reviewer.is_active = False
    db.commit()
    with pytest.raises(HTTPException, match="原审核人"):
        revise()
    reviewer.is_active = True
    stamped = WorkOrderFile(work_order_id=order.id, file_category="STAMPED_CONTRACT_SCAN",
        business_stage="PRINT_ROOM_CONTRACT_SCAN", version_no=1, is_current=True,
        uploaded_by=leader.id, uploaded_at=order.created_at, storage_key="stamped.pdf", origin_file_name="stamped.pdf")
    db.add(stamped)
    db.commit()
    with pytest.raises(HTTPException, match="盖章"):
        revise()
    stamped.is_current = False
    db.commit()

    def fail_notification(*args, **kwargs):
        raise RuntimeError("notification failure")

    with monkeypatch.context() as patch:
        patch.setattr(api, "send_workflow_notification", fail_notification)
        with pytest.raises(RuntimeError):
            revise()
    assert old.is_current and order.current_status == "CONTRACT_APPROVED"
    assert list(tmp_path.iterdir()) == [original]

    unlink = Path.unlink
    def fail_old(path, **kwargs):
        if path == original:
            raise PermissionError("file busy")
        return unlink(path, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_old)
        revised = revise()
    assert old.source_type == PENDING_DELETE and original.exists()
    purge_replaced_contracts(db)
    assert old.source_type == DELETED and not original.exists()
    assert revised.contract_file.id != old.id


def test_concurrent_revision_commits_once(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from io import BytesIO
    from threading import Barrier
    from fastapi import UploadFile
    from app.api.v1 import contract_reviews as api
    from app.core.config import settings
    from app.models.user_notification import UserNotification

    monkeypatch.setattr(settings, "local_storage_dir", str(tmp_path / "files"))
    engine = create_engine("sqlite:///" + str(tmp_path / "oa.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        leader = _seed_user(db, "leader", [])
        reviewer = _seed_user(db, "reviewer", [_seed_role(db, "CONTRACT_REVIEWER", "Reviewer")])
        _, order = _seed_project_and_work_order(db, leader, leader)
        first = api.submit_contract_review(ContractReviewSubmitRequest(
            work_order_id=order.id, reviewer_user_id=reviewer.id), db, leader)
        approval = api.approve_contract_review(first.id, ContractReviewDecisionRequest(), db, reviewer, set())
        leader_id, order_id, approval_id = leader.id, order.id, approval.id

    ready = Barrier(2)
    def send(_):
        with Session(engine) as db:
            actor = db.get(User, leader_id)
            ready.wait(timeout=10)
            try:
                api.revise_approved_contract(order_id, approval_id, "NONE",
                    UploadFile(filename="same.pdf", file=BytesIO(b"new")), db, actor)
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, range(2))) == [200, 409]
    with Session(engine) as db:
        assert db.query(WorkOrderFile).filter_by(is_current=True).one().version_no == 2
        assert db.query(UserNotification).filter_by(title="请处理合同审核", process_status="PENDING").count() == 1
