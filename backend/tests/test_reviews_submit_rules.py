import sys

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
from app.schemas.review import ReviewSubmitRequest

pytestmark = pytest.mark.skipif(sys.version_info < (3, 11), reason="requires Python 3.11+ for StrEnum imports")


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


def test_submit_review_rejects_reviewer_without_round_role() -> None:
    from app.api.v1.reviews import submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)

    payload = ReviewSubmitRequest(
        work_order_id=work_order.id,
        review_round="FIRST",
        reviewer_user_id=reviewer.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        submit_review(payload=payload, db=db, current_user=leader, _={"PROJECT_LEADER"})

    assert exc_info.value.status_code == 400
    assert "不具备FIRST轮审核角色" in str(exc_info.value.detail)


def test_submit_review_accepts_reviewer_with_round_role() -> None:
    from app.api.v1.reviews import submit_review

    db = _build_session()
    leader, reviewer, _, work_order = _seed_basic(db)

    first_role = db.query(Role).filter(Role.code == "FIRST_REVIEWER").first()
    assert first_role is not None
    db.add(UserRole(user_id=reviewer.id, role_id=first_role.id))
    db.commit()

    payload = ReviewSubmitRequest(
        work_order_id=work_order.id,
        review_round="FIRST",
        reviewer_user_id=reviewer.id,
    )

    result = submit_review(payload=payload, db=db, current_user=leader, _={"PROJECT_LEADER"})
    assert result.reviewer_user_id == reviewer.id
    assert result.review_round == "FIRST"
