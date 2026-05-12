from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.invoice import Invoice
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_user(db: Session, username: str = "leader") -> User:
    user = User(username=username, password_hash="x", real_name=username.title(), is_active=True)
    db.add(user)
    db.flush()
    return user


def _seed_project(
    db: Session,
    leader: User,
    *,
    project_code: str,
    termination_status: str | None = None,
) -> tuple[Project, WorkOrder]:
    project = Project(
        project_code=project_code,
        project_name="Demo",
        client_name="Client",
        business_user_id=leader.id,
        project_leader_id=leader.id,
        termination_status=termination_status,
        termination_reason="reason" if termination_status else None,
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no=f"WO-{project.id}",
        project_id=project.id,
        title="WO",
        current_status="WAIT_INVOICE_INFO",
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.commit()
    return project, work_order


def test_project_export_includes_progress_labels() -> None:
    from app.api.v1.project_exports import _collect_rows

    db = _build_session()
    leader = _seed_user(db)
    active_project, _ = _seed_project(db, leader, project_code="P-ACTIVE")
    archived_project, _ = _seed_project(db, leader, project_code="P-ARCHIVED")
    archived_project.archived_at = active_project.created_at
    voided_project, _ = _seed_project(db, leader, project_code="P-VOIDED", termination_status="APPROVED")
    db.commit()

    rows = _collect_rows(db, None, None, None, None, None, None, None, None, None, None)
    progress_by_no = {row["project_no"]: row["project_progress"] for row in rows}

    assert progress_by_no[active_project.project_code] == "进行中"
    assert progress_by_no[archived_project.project_code] == "已归档"
    assert progress_by_no[voided_project.project_code] == "已作废"


def test_approved_termination_is_excluded_from_todo_projects() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    approved_project, _ = _seed_project(db, leader, project_code="P-APPROVED", termination_status="APPROVED")

    result = get_workbench(db=db, current_user=leader)

    assert approved_project.id not in [item.id for item in result.todo_projects]


def test_admin_sees_pending_termination_todo() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    admin = _seed_user(db, "admin")
    admin_role = Role(code="ADMIN", name="管理员", description="", is_system_fixed=True)
    db.add(admin_role)
    db.flush()
    db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    pending_project, _ = _seed_project(db, leader, project_code="P-PENDING", termination_status="PENDING")
    db.commit()

    result = get_workbench(db=db, current_user=admin)

    assert [item.id for item in result.todo_projects] == [pending_project.id]
    assert result.todo_projects[0].can_approve_termination is True


def test_invoice_submission_does_not_change_main_workflow_status() -> None:
    from app.api.v1.finance import create_invoice
    from app.schemas.invoice import InvoiceCreate

    db = _build_session()
    leader = _seed_user(db)
    project, work_order = _seed_project(db, leader, project_code="P-INVOICE")
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = 999
    db.commit()

    create_invoice(
        payload=InvoiceCreate(
            work_order_id=work_order.id,
            invoice_info="开票单位：中勤\n测试开票信息",
            invoice_type="专票",
            amount=100,
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    invoice = db.query(Invoice).filter(Invoice.work_order_id == work_order.id).first()
    assert invoice is not None
    assert invoice.status == "SUBMITTED"
    assert work_order.current_status == "FIRST_REVIEWING"
    assert work_order.current_handler_user_id == 999


def test_invoice_submission_can_start_new_round_after_issued_invoice() -> None:
    from app.api.v1.finance import create_invoice
    from app.schemas.invoice import InvoiceCreate

    db = _build_session()
    leader = _seed_user(db)
    _, work_order = _seed_project(db, leader, project_code="P-INVOICE-MULTI")
    db.add(Invoice(
        work_order_id=work_order.id,
        invoice_no="INV-OLD",
        invoice_info="old info",
        invoice_type="专票",
        amount=100,
        status="ISSUED",
    ))
    db.commit()

    create_invoice(
        payload=InvoiceCreate(
            work_order_id=work_order.id,
            invoice_info="开票单位：中勤\n第二轮开票信息",
            invoice_type="普票",
            amount=200,
        ),
        db=db,
        current_user=leader,
        role_codes={"PROJECT_LEADER"},
    )

    invoices = db.query(Invoice).filter(Invoice.work_order_id == work_order.id).order_by(Invoice.id.asc()).all()
    assert [invoice.status for invoice in invoices] == ["ISSUED", "SUBMITTED"]
    assert invoices[1].amount == 200


def test_finance_todo_comes_from_submitted_invoice() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    finance = _seed_user(db, "finance")
    finance_role = Role(code="FINANCE", name="财务", description="", is_system_fixed=True)
    db.add(finance_role)
    db.flush()
    db.add(UserRole(user_id=finance.id, role_id=finance_role.id))
    project, work_order = _seed_project(db, leader, project_code="P-FINANCE-TODO")
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = leader.id
    db.add(Invoice(
        work_order_id=work_order.id,
        invoice_no="PENDING",
        invoice_info="info",
        invoice_type="专票",
        amount=100,
        status="SUBMITTED",
    ))
    db.commit()

    result = get_workbench(db=db, current_user=finance)

    assert [item.id for item in result.todo_projects] == [project.id]
    assert result.todo_projects[0].current_step == "财务开票"


def test_rejected_invoice_prompts_project_party_without_changing_main_status() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    project, work_order = _seed_project(db, leader, project_code="P-INVOICE-REJECTED")
    work_order.current_status = "FIRST_REVIEWING"
    work_order.current_handler_user_id = 999
    db.add(Invoice(
        work_order_id=work_order.id,
        invoice_no="PENDING",
        invoice_info="info",
        invoice_type="专票",
        amount=100,
        status="REJECTED",
    ))
    db.commit()

    result = get_workbench(db=db, current_user=leader)

    assert [item.id for item in result.todo_projects] == [project.id]
    assert result.todo_projects[0].current_step == "发票开具"
    assert result.todo_projects[0].todo_action == "开票信息被退回，请修改后重新提交"
