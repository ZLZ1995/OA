from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.archive import ArchiveDecisionRequest, ArchiveSubmitRequest
from app.schemas.contract_review import ContractReviewDecisionRequest, ContractReviewSubmitRequest
from app.schemas.invoice import InvoiceCreate
from app.schemas.project import ProjectCreate
from app.schemas.project_member import ProjectMemberBatchCreate, ProjectMemberCompleteRequest
from app.schemas.print_room import IssuePaperReportRequest
from app.schemas.report_mailing import ReportMailingDecisionRequest, ReportMailingExpressRequest, ReportMailingSubmitRequest
from app.schemas.review import ReviewDecisionRequest, ReviewSubmitRequest
from app.workflows.states import WorkOrderStatus


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


def _seed_roles_and_users(db: Session) -> dict[str, User]:
    roles = {
        "ADMIN": _seed_role(db, "ADMIN", "管理员"),
        "PROJECT_LEADER": _seed_role(db, "PROJECT_LEADER", "项目负责人"),
        "PROJECT_MEMBER": _seed_role(db, "PROJECT_MEMBER", "项目组成员"),
        "CONTRACT_REVIEWER": _seed_role(db, "CONTRACT_REVIEWER", "合同审核人"),
        "FIRST_REVIEWER": _seed_role(db, "FIRST_REVIEWER", "一审人员"),
        "SECOND_REVIEWER": _seed_role(db, "SECOND_REVIEWER", "二审人员"),
        "THIRD_REVIEWER": _seed_role(db, "THIRD_REVIEWER", "三审人员"),
        "CHIEF_APPRAISER": _seed_role(db, "CHIEF_APPRAISER", "首席评估师"),
        "PRINT_ROOM": _seed_role(db, "PRINT_ROOM", "文印室"),
        "FINANCE": _seed_role(db, "FINANCE", "财务人员"),
        "ARCHIVE_MANAGER": _seed_role(db, "ARCHIVE_MANAGER", "档案管理员"),
    }
    return {
        "admin": _seed_user(db, "admin", "管理员", [roles["ADMIN"]]),
        "creator": _seed_user(db, "creator", "创建人", [roles["PROJECT_LEADER"], roles["PROJECT_MEMBER"]]),
        "leader": _seed_user(db, "leader", "项目负责人", [roles["PROJECT_LEADER"], roles["PROJECT_MEMBER"]]),
        "member": _seed_user(db, "member", "项目组成员", [roles["PROJECT_MEMBER"]]),
        "contract": _seed_user(db, "contract", "合同审核", [roles["CONTRACT_REVIEWER"]]),
        "first": _seed_user(db, "first", "一审", [roles["FIRST_REVIEWER"]]),
        "second": _seed_user(db, "second", "二审", [roles["SECOND_REVIEWER"]]),
        "third": _seed_user(db, "third", "三审", [roles["THIRD_REVIEWER"]]),
        "chief": _seed_user(db, "chief", "首席评估师", [roles["CHIEF_APPRAISER"]]),
        "print_room": _seed_user(db, "printroom", "文印室", [roles["PRINT_ROOM"]]),
        "finance": _seed_user(db, "finance", "财务", [roles["FINANCE"]]),
        "archive": _seed_user(db, "archive", "档案", [roles["ARCHIVE_MANAGER"]]),
    }


def _latest_work_order(db: Session, project_id: int) -> WorkOrder:
    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()
    assert work_order is not None
    return work_order


def _add_current_file(db: Session, work_order: WorkOrder, category: str, stage: str, user: User, name: str = "file.pdf") -> WorkOrderFile:
    row = WorkOrderFile(
        work_order_id=work_order.id,
        file_category=category,
        business_stage=stage,
        version_no=1,
        is_current=True,
        origin_file_name=name,
        storage_key=name,
        file_size=128,
        uploaded_by=user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _create_project_bundle(db: Session) -> tuple[dict[str, User], Project, WorkOrder]:
    from app.api.v1.projects import create_project

    users = _seed_roles_and_users(db)
    project = create_project(
        payload=ProjectCreate(
            undertaking_unit="中勤",
            project_name="产品级冒烟项目",
            client_name="测试客户",
            evaluation_business_nature="其他",
            report_type="评估报告",
            valuation_base_date=date(2026, 5, 16),
            business_salesman="业务员",
            project_amount=1000,
            project_source="INTERNAL",
            business_user_id=users["creator"].id,
            project_leader_id=users["leader"].id,
        ),
        db=db,
        current_user=users["creator"],
    )
    work_order = _latest_work_order(db, project.id)
    return users, db.query(Project).filter(Project.id == project.id).one(), work_order


def test_smoke_01_project_creation_creates_initial_work_order() -> None:
    db = _build_session()
    _, project, work_order = _create_project_bundle(db)

    assert project.project_code.startswith("ZQ-")
    assert project.undertaking_unit == "中勤"
    assert work_order.current_status == WorkOrderStatus.WORK_ORDER_CREATED.value
    assert work_order.current_handler_user_id == project.project_leader_id


def test_smoke_02_project_members_complete_moves_to_contract_upload() -> None:
    from app.api.v1.project_members import batch_create_project_member, complete_project_members

    db = _build_session()
    users, project, work_order = _create_project_bundle(db)

    batch_create_project_member(
        payload=ProjectMemberBatchCreate(project_id=project.id, user_ids=[users["leader"].id], member_role="项目负责人"),
        db=db,
        _={"ADMIN", "PROJECT_LEADER"},
    )
    batch_create_project_member(
        payload=ProjectMemberBatchCreate(project_id=project.id, user_ids=[users["member"].id], member_role="项目组成员"),
        db=db,
        _={"ADMIN", "PROJECT_LEADER"},
    )
    complete_project_members(
        payload=ProjectMemberCompleteRequest(project_id=project.id),
        db=db,
        current_user=users["leader"],
        _={"PROJECT_LEADER"},
    )

    db.refresh(work_order)
    assert work_order.current_status == WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value
    assert db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count() == 2


def test_smoke_03_contract_review_approval_moves_to_report_submit() -> None:
    from app.api.v1.contract_reviews import approve_contract_review, submit_contract_review

    db = _build_session()
    users, project, work_order = _create_project_bundle(db)
    work_order.current_status = WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT.value
    work_order.contract_reviewer_id = users["contract"].id
    _add_current_file(db, work_order, "CONTRACT_DRAFT", "CONTRACT_DRAFT", users["leader"], "contract.pdf")
    db.commit()

    submitted = submit_contract_review(
        payload=ContractReviewSubmitRequest(work_order_id=work_order.id, reviewer_user_id=users["contract"].id, comment="提交合同初审"),
        db=db,
        current_user=users["leader"],
        _={"PROJECT_LEADER"},
    )
    approve_contract_review(
        record_id=submitted.id,
        payload=ContractReviewDecisionRequest(comment="合同通过"),
        db=db,
        current_user=users["contract"],
        _={"CONTRACT_REVIEWER"},
    )

    db.refresh(work_order)
    assert work_order.current_status == WorkOrderStatus.CONTRACT_APPROVED.value
    assert work_order.current_handler_user_id == project.project_leader_id


def test_smoke_04_review_and_signoff_move_to_print_room() -> None:
    from app.api.v1.reviews import decide_review, submit_review
    from app.api.v1.signoff import approve_signoff, enter_signoff_review

    db = _build_session()
    users, _, work_order = _create_project_bundle(db)
    work_order.current_status = WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT.value
    work_order.current_handler_user_id = users["leader"].id
    work_order.third_reviewer_id = users["third"].id
    work_order.chief_appraiser_user_id = users["chief"].id
    _add_current_file(db, work_order, "REPORT_ZIP", "REVIEW_THIRD", users["leader"], "review.zip")
    db.commit()

    submit_review(
        payload=ReviewSubmitRequest(work_order_id=work_order.id, review_round="THIRD", reviewer_user_id=users["third"].id, comment="提交三审"),
        db=db,
        current_user=users["leader"],
        role_codes={"PROJECT_LEADER"},
    )
    decide_review(
        payload=ReviewDecisionRequest(work_order_id=work_order.id, review_round="THIRD", action="APPROVE", comment="三审通过"),
        db=db,
        current_user=users["third"],
        _={"THIRD_REVIEWER"},
    )
    db.refresh(work_order)
    assert work_order.current_status == WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value

    _add_current_file(db, work_order, "FORMAL_REPORT", "FORMAL_REPORT", users["leader"], "formal.pdf")
    _add_current_file(db, work_order, "FINAL_CONTRACT_SCAN", "FINAL_CONTRACT_SCAN", users["leader"], "contract-scan.pdf")
    enter_signoff_review(work_order.id, db=db, current_user=users["leader"], _={"PROJECT_LEADER"})
    approve_signoff(work_order.id, db=db, current_user=users["chief"], _={"CHIEF_APPRAISER"})

    db.refresh(work_order)
    assert work_order.current_status == WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value


def test_smoke_05_print_room_and_mailing_move_to_archive_submit() -> None:
    from app.api.v1.print_room import issue_paper_report
    from app.api.v1.report_mailing import confirm_report_mailing, submit_report_mailing, submit_report_mailing_express

    db = _build_session()
    users, _, work_order = _create_project_bundle(db)
    work_order.current_status = WorkOrderStatus.PRINTROOM_PROCESSING.value
    work_order.current_handler_user_id = users["print_room"].id
    work_order.print_room_handler_id = users["print_room"].id
    db.commit()

    issue_paper_report(
        payload=IssuePaperReportRequest(work_order_id=work_order.id, paper_report_no="R-001", copy_count=2, remark="出具报告"),
        db=db,
        current_user=users["print_room"],
        _={"PRINT_ROOM"},
    )
    db.refresh(work_order)
    assert work_order.current_status == WorkOrderStatus.WAIT_INVOICE_INFO.value

    submit_report_mailing(
        work_order_id=work_order.id,
        payload=ReportMailingSubmitRequest(receiver_name="张三", receiver_phone="13800138000", receiver_address="测试地址"),
        db=db,
        current_user=users["leader"],
    )
    submit_report_mailing_express(
        work_order_id=work_order.id,
        payload=ReportMailingExpressRequest(express_no="SF123456"),
        db=db,
        current_user=users["print_room"],
    )
    confirm_report_mailing(
        work_order_id=work_order.id,
        payload=ReportMailingDecisionRequest(remark="确认收到"),
        db=db,
        current_user=users["leader"],
    )

    db.refresh(work_order)
    assert work_order.current_status == WorkOrderStatus.WAIT_ARCHIVE_SUBMIT.value
    assert work_order.mailing_status == "COMPLETED"


def test_smoke_06_invoice_and_archive_complete_business_chain() -> None:
    from app.api.v1.archives import approve_archive, finalize_archive, submit_archive
    from app.api.v1.finance import complete_invoice, confirm_invoice, create_invoice

    db = _build_session()
    users, project, work_order = _create_project_bundle(db)
    work_order.current_status = WorkOrderStatus.WAIT_INVOICE_INFO.value
    db.commit()

    invoice = create_invoice(
        payload=InvoiceCreate(
            work_order_id=work_order.id,
            invoice_info="开票单位：中勤\n测试客户",
            invoice_type="专票",
            amount=300,
            finance_handler_id=users["finance"].id,
        ),
        db=db,
        current_user=users["leader"],
        role_codes={"PROJECT_LEADER"},
    )
    complete_invoice(invoice.id, db=db, current_user=users["finance"], _={"FINANCE"})
    confirm_invoice(invoice.id, db=db, current_user=users["leader"], role_codes={"PROJECT_LEADER"})

    submit_archive(
        payload=ArchiveSubmitRequest(work_order_id=work_order.id, reviewer_user_id=users["archive"].id, submission_type="ONLINE", remark="提交归档"),
        db=db,
        current_user=users["leader"],
    )
    approve_archive(
        payload=ArchiveDecisionRequest(work_order_id=work_order.id, remark="归档通过"),
        db=db,
        current_user=users["archive"],
        _={"ARCHIVE_MANAGER"},
    )
    finalize_archive(
        payload=ArchiveDecisionRequest(work_order_id=work_order.id, remark="最终归档"),
        db=db,
        current_user=users["leader"],
    )

    db.refresh(project)
    db.refresh(work_order)
    assert work_order.current_status == WorkOrderStatus.ARCHIVED.value
    assert project.archived_at is not None
