from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.oa_agent_audit_log import OaAgentAuditLog
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.services.oa_agent_audit import record_agent_module_access
from app.services.oa_agent_context import build_authorized_project_context
from app.services.oa_agent_llm import ensure_operation_guide
from app.services.oa_agent_project_access import (
    extract_project_keywords,
    get_accessible_project,
    search_accessible_projects,
    search_accessible_projects_from_message,
)


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_user(db: Session, username: str) -> User:
    user = User(
        username=username,
        password_hash="x",
        real_name=username.title(),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _seed_admin(db: Session, username: str = "admin") -> User:
    user = _seed_user(db, username)
    role = Role(code="ADMIN", name="ADMIN", description="", is_system_fixed=True)
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def _seed_project(
    db: Session,
    leader: User,
    *,
    project_code: str,
    project_name: str = "Alpha Project",
    client_name: str = "Alpha Client",
) -> tuple[Project, WorkOrder]:
    project = Project(
        project_code=project_code,
        project_name=project_name,
        client_name=client_name,
        business_user_id=leader.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no=f"WO-{project.id}",
        project_id=project.id,
        title=project.project_name,
        current_status="WAIT_FIRST_REVIEW_SUBMIT",
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
    )
    db.add(work_order)
    db.flush()
    return project, work_order


def test_agent_search_limits_regular_user_to_owned_projects() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    other = _seed_user(db, "other")
    own_project, _ = _seed_project(db, leader, project_code="P-OWN")
    _seed_project(db, other, project_code="P-OTHER")
    db.commit()

    rows = search_accessible_projects(db, leader, "P-", limit=10)

    assert [item.id for item in rows] == [own_project.id]
    assert get_accessible_project(db, leader, own_project.id) is not None


def test_agent_search_allows_project_member() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    member = _seed_user(db, "member")
    project, _ = _seed_project(db, leader, project_code="P-MEMBER")
    db.add(ProjectMember(project_id=project.id, user_id=member.id, member_role="MEMBER"))
    db.commit()

    rows = search_accessible_projects(db, member, "member", limit=10)

    assert [item.id for item in rows] == [project.id]


def test_agent_search_allows_reviewer() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    reviewer = _seed_user(db, "reviewer")
    project, work_order = _seed_project(db, leader, project_code="P-REVIEW")
    work_order.first_reviewer_id = reviewer.id
    db.commit()

    rows = search_accessible_projects(db, reviewer, "review", limit=10)

    assert [item.id for item in rows] == [project.id]


def test_agent_search_allows_admin_to_all_projects() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    admin = _seed_admin(db)
    first_project, _ = _seed_project(db, leader, project_code="P-ADMIN-1")
    second_project, _ = _seed_project(db, leader, project_code="P-ADMIN-2")
    db.commit()

    rows = search_accessible_projects(db, admin, "admin", limit=10)

    assert {item.id for item in rows} == {first_project.id, second_project.id}


def test_agent_search_does_not_reveal_inaccessible_project_by_id() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    outsider = _seed_user(db, "outsider")
    project, _ = _seed_project(db, leader, project_code="P-HIDDEN")
    db.commit()

    assert get_accessible_project(db, outsider, project.id) is None


def test_agent_project_candidates_are_limited_to_ten() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    for index in range(12):
        _seed_project(db, leader, project_code=f"P-LIMIT-{index:02d}", project_name="Limit Project")
    db.commit()

    rows = search_accessible_projects(db, leader, "limit", limit=10)

    assert len(rows) == 10


def test_agent_extracts_project_keyword_from_natural_language_question() -> None:
    keywords = extract_project_keywords("请问 Alpha Project 现在到哪一步了")

    assert "Alpha Project" in keywords


def test_agent_extracts_embedded_numeric_project_keyword() -> None:
    keywords = extract_project_keywords("111合同初稿上传下一步怎么操作")

    assert keywords[0] == "111"


def test_agent_message_search_uses_extracted_project_keyword() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    project, _ = _seed_project(db, leader, project_code="P-NATURAL", project_name="Alpha Project")
    db.commit()

    rows = search_accessible_projects_from_message(db, leader, "请问 Alpha Project 现在到哪一步了", limit=10)

    assert [item.id for item in rows] == [project.id]


def test_agent_attachment_context_exposes_metadata_only() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    project, work_order = _seed_project(db, leader, project_code="P-FILE")
    db.add(
        WorkOrderFile(
            work_order_id=work_order.id,
            file_category="REPORT",
            business_stage="FIRST_REVIEW",
            version_no=1,
            is_current=True,
            origin_file_name="report.docx",
            storage_key="private/path/report.docx",
            file_size=128,
            uploaded_by=leader.id,
            uploaded_at=datetime.now(),
        )
    )
    db.commit()

    context, modules = build_authorized_project_context(db, leader, project)

    assert "attachments" in modules
    assert context["attachments"][0]["origin_file_name"] == "report.docx"
    assert "storage_key" not in context["attachments"][0]


def test_agent_sensitive_module_access_writes_module_level_audit() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    project, _ = _seed_project(db, leader, project_code="P-AUDIT")
    db.commit()

    record_agent_module_access(
        db,
        user_id=leader.id,
        project_id=project.id,
        session_id="s1",
        modules={"attachments", "comments", "non_sensitive"},
    )
    db.commit()

    rows = db.query(OaAgentAuditLog).order_by(OaAgentAuditLog.module.asc()).all()
    assert [row.module for row in rows] == ["attachments", "comments"]
    assert all(row.action == "READ" for row in rows)


def test_agent_operation_entry_points_to_member_panel() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    project, work_order = _seed_project(db, leader, project_code="P-MEMBER-ENTRY")
    work_order.current_status = "WORK_ORDER_CREATED"
    db.commit()

    context, _ = build_authorized_project_context(db, leader, project)

    assert context["flow"]["operation_entry"] == "项目详情页 > 项目流程 > 项目组成员面板"
    assert context["flow"]["operation_url"] == f"/projects/{project.id}/flow?todoPanel=members"
    assert "添加" in context["flow"]["operation_hint"]


def test_agent_operation_entry_points_to_contract_upload_panel() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    project, work_order = _seed_project(db, leader, project_code="P-CONTRACT-ENTRY")
    work_order.current_status = "WAIT_CONTRACT_UPLOAD"
    db.commit()

    context, _ = build_authorized_project_context(db, leader, project)

    assert context["flow"]["operation_entry"] == "项目详情页 > 项目流程 > 合同初稿上传面板"
    assert context["flow"]["operation_url"] == f"/projects/{project.id}/flow?todoPanel=contract"
    assert "上传合同初稿" in context["flow"]["operation_hint"]


def test_agent_non_handler_guidance_names_current_handler() -> None:
    db = _build_session()
    leader = _seed_user(db, "leader")
    admin = _seed_admin(db)
    project, work_order = _seed_project(db, leader, project_code="P-HANDLER")
    work_order.current_status = "WAIT_CONTRACT_UPLOAD"
    db.commit()

    context, _ = build_authorized_project_context(db, admin, project)

    assert "当前有权限处理流程的账号：Leader" in context["flow"]["available_action"]
    assert "当前有权限处理流程的账号：Leader" in context["flow"]["operation_hint"]


def test_agent_llm_answer_replaces_generic_operation_entry() -> None:
    context = {
        "flow": {
            "operation_entry": "项目详情页 > 项目流程 > 合同初稿上传面板",
            "operation_url": "/projects/1/flow?todoPanel=contract",
            "operation_hint": "选择合同审核人，上传合同初稿扫描件，然后提交合同初稿审核。",
        }
    }

    answer = ensure_operation_guide(
        "下一步：请上传合同初稿\n操作入口：项目详情页 > 项目流程。",
        context,
    )

    assert "操作入口：项目详情页 > 项目流程。" not in answer
    assert "操作入口：项目详情页 > 项目流程 > 合同初稿上传面板。" in answer
    assert "操作提示：选择合同审核人" in answer
    assert "直达链接：/projects/1/flow?todoPanel=contract" in answer


def test_agent_llm_answer_preserves_non_handler_guidance() -> None:
    context = {
        "flow": {
            "available_action": "当前账号不是本节点处理人。当前有权限处理流程的账号：张立志。请联系该账号处理，或等待其完成后再继续。",
            "current_handler_name": "张立志",
            "operation_entry": "项目详情页 > 项目流程 > 合同初稿上传面板",
            "operation_url": "/projects/1/flow?todoPanel=contract",
            "operation_hint": "当前账号不是本节点处理人，当前有权限处理流程的账号：张立志。请联系该账号处理，或等待其完成后再继续。",
        }
    }

    answer = ensure_operation_guide(
        "当前处理人：张立志\n下一步操作：当前暂无待办操作。",
        context,
    )

    assert "当前有权限处理流程的账号：张立志" in answer
    assert "操作提示：当前账号不是本节点处理人" in answer


def test_agent_llm_answer_deduplicates_operation_links_and_hints() -> None:
    context = {
        "flow": {
            "operation_entry": "项目详情页 > 项目流程 > 合同初稿上传面板",
            "operation_url": "/projects/1/flow?todoPanel=contract",
            "operation_hint": "选择合同审核人，上传合同初稿扫描件，然后提交合同初稿审核。",
        }
    }

    answer = ensure_operation_guide(
        "\n".join(
            [
                "下一步：请上传合同初稿",
                "操作入口：项目详情页 > 项目流程",
                "操作链接：/projects/1/flow?todoPanel=contract",
                "提示：按页面提示处理。",
            ]
        ),
        context,
    )

    assert answer.count("操作入口：") == 1
    assert answer.count("操作提示：") == 1
    assert answer.count("直达链接：") == 1
    assert "操作链接：" not in answer
    assert "提示：按页面提示处理。" not in answer
