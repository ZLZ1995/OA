from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.issue_feedbacks import create_issue_feedback, list_issue_feedbacks, resolve_issue_feedback, suspend_issue_feedback
from app.db.base import Base
from app.models.role import Role
from app.models.user import User
from app.models.user_notification import UserNotification
from app.models.user_role import UserRole
from app.schemas.issue_feedback import IssueFeedbackCreate, IssueFeedbackSuspendRequest


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_users(db: Session) -> tuple[User, User]:
    admin_role = Role(code="ADMIN", name="admin", description="", is_system_fixed=True)
    user = User(username="submitter", password_hash="x", real_name="Submitter", is_active=True)
    admin = User(username="admin", password_hash="x", real_name="Admin", is_active=True)
    db.add_all([admin_role, user, admin])
    db.flush()
    db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    db.commit()
    return user, admin


def test_issue_feedback_submit_resolve_and_suspend() -> None:
    db = _build_session()
    submitter, admin = _seed_users(db)

    created = create_issue_feedback(
        IssueFeedbackCreate(project_no="ZQ-001", process_step="报告送审", detail="按钮无反应"),
        db=db,
        current_user=submitter,
    )
    assert created.status == "PENDING"
    assert db.query(UserNotification).filter(UserNotification.user_id == admin.id).count() == 1

    listed = list_issue_feedbacks(db=db, _={"ADMIN"})
    assert len(listed.items) == 1

    resolved = resolve_issue_feedback(created.id, db=db, current_user=admin, _={"ADMIN"})
    assert resolved.status == "RESOLVED"
    assert db.query(UserNotification).filter(UserNotification.user_id == submitter.id).count() == 1

    suspended = suspend_issue_feedback(
        created.id,
        IssueFeedbackSuspendRequest(suspend_note="need support"),
        db=db,
        current_user=admin,
        _={"ADMIN"},
    )
    assert suspended.status == "TECH_SUPPORT"
    assert suspended.suspend_note == "need support"
