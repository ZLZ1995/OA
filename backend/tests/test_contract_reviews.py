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
from app.schemas.contract_review import ContractReviewDecisionRequest, ContractReviewSubmitRequest


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
            file_category="CONTRACT",
            business_stage="CONTRACT",
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
            _={"PROJECT_LEADER"},
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
        _={"PROJECT_LEADER"},
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
        _={"PROJECT_LEADER"},
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
