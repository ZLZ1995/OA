from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.project_member import ProjectMemberCompleteRequest
from app.schemas.project import ProjectCreate


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def test_create_project_returns_generated_project_code() -> None:
    from app.api.v1.projects import create_project

    db = _build_session()
    user = User(username="leader", password_hash="x", real_name="Leader", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    payload = ProjectCreate(
        project_code=None,
        undertaking_unit="中勤",
        project_name="Demo Project",
        client_name="Demo Client",
        business_user_id=user.id,
        project_leader_id=user.id,
    )

    result = create_project(payload=payload, db=db, current_user=user)

    assert result.project_code.startswith("ZQ-")
    assert result.project_name == "Demo Project"

    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == result.id).one()
    assert work_order.work_order_no == result.project_code
    assert work_order.current_status == "WORK_ORDER_CREATED"
    assert work_order.project_leader_id == user.id


def test_complete_project_members_requires_leader_and_advances_work_order() -> None:
    from app.api.v1.project_members import complete_project_members
    from app.api.v1.projects import create_project

    db = _build_session()
    user = User(username="leader", password_hash="x", real_name="Leader", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    project = create_project(
        payload=ProjectCreate(
            project_code=None,
            undertaking_unit="中勤",
            project_name="Demo Project",
            client_name="Demo Client",
            business_user_id=user.id,
            project_leader_id=user.id,
        ),
        db=db,
        current_user=user,
    )
    db.add(ProjectMember(project_id=project.id, user_id=user.id, member_role="LEADER"))
    db.commit()

    complete_project_members(
        payload=ProjectMemberCompleteRequest(project_id=project.id),
        db=db,
        _={"PROJECT_LEADER"},
    )

    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project.id).one()
    assert work_order.current_status == "WAIT_CONTRACT_UPLOAD"
    assert work_order.project_leader_id == user.id


def test_complete_contract_upload_advances_to_review_submit() -> None:
    from app.api.v1.files import complete_contract_upload
    from app.api.v1.projects import create_project

    db = _build_session()
    user = User(username="leader", password_hash="x", real_name="Leader", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    project = create_project(
        payload=ProjectCreate(
            project_code="ZQ-TEST-CONTRACT",
            undertaking_unit="涓嫟",
            project_name="Demo Project",
            client_name="Demo Client",
            business_user_id=user.id,
            project_leader_id=user.id,
        ),
        db=db,
        current_user=user,
    )
    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project.id).one()
    work_order.current_status = "CONTRACT_UPLOADED"
    work_order.contract_reviewer_id = user.id
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="CONTRACT",
            business_stage="CONTRACT",
            version_no=1,
            is_current=True,
            origin_file_name="contract.pdf",
            storage_key="contract.pdf",
            uploaded_by=user.id,
            uploaded_at=work_order.created_at,
        )
    )
    db.commit()

    complete_contract_upload(
        work_order_id=work_order.id,
        db=db,
        current_user=user,
        _={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert work_order.current_status == "WAIT_CONTRACT_REVIEW_SUBMIT"
    assert work_order.current_handler_user_id == user.id
