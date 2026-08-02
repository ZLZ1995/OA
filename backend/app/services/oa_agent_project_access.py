import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.services.project_flow import get_project_status_display, normalize_project_step


def is_agent_admin(user: User) -> bool:
    return user.username == settings.initial_admin_username or any(
        item.role.code == "ADMIN" for item in user.roles
    )


def accessible_project_query(db: Session, user: User):
    query = db.query(Project).filter(Project.deleted_at.is_(None))
    if is_agent_admin(user):
        return query

    member_project_ids = select(ProjectMember.project_id).filter(
        ProjectMember.user_id == user.id
    )
    reviewer_project_ids = select(WorkOrder.project_id).filter(
        or_(
            WorkOrder.contract_reviewer_id == user.id,
            WorkOrder.first_reviewer_id == user.id,
            WorkOrder.second_reviewer_id == user.id,
            WorkOrder.third_reviewer_id == user.id,
            WorkOrder.chief_appraiser_user_id == user.id,
            WorkOrder.archive_reviewer_id == user.id,
            WorkOrder.current_handler_user_id == user.id,
        )
    )
    return query.filter(
        or_(
            Project.business_user_id == user.id,
            Project.project_leader_id == user.id,
            Project.id.in_(member_project_ids),
            Project.id.in_(reviewer_project_ids),
        )
    )


def get_accessible_project(db: Session, user: User, project_id: int) -> Project | None:
    return accessible_project_query(db, user).filter(Project.id == project_id).first()


def latest_work_order(db: Session, project_id: int) -> WorkOrder | None:
    return (
        db.query(WorkOrder)
        .filter(WorkOrder.project_id == project_id)
        .order_by(WorkOrder.id.desc())
        .first()
    )


def search_accessible_projects(db: Session, user: User, keyword: str, limit: int = 10) -> list[Project]:
    value = f"%{keyword.strip()}%"
    if not keyword.strip():
        return []
    return (
        accessible_project_query(db, user)
        .filter(
            or_(
                Project.project_name.like(value),
                Project.project_code.like(value),
                Project.client_name.like(value),
            )
        )
        .order_by(Project.id.desc())
        .limit(limit)
        .all()
    )


def search_accessible_projects_from_message(db: Session, user: User, message: str, limit: int = 10) -> list[Project]:
    projects_by_id: dict[int, Project] = {}
    for keyword in extract_project_keywords(message):
        for project in search_accessible_projects(db, user, keyword, limit=limit):
            projects_by_id.setdefault(project.id, project)
            if len(projects_by_id) >= limit:
                return list(projects_by_id.values())
    return list(projects_by_id.values())


def extract_project_keywords(message: str) -> list[str]:
    text = message.strip()
    if not text:
        return []

    keywords: list[str] = []
    for value in re.findall(r"[A-Za-z]{1,10}-\d{4,}(?:-\d+)*|\d{2,}", text):
        if value not in keywords:
            keywords.append(value)

    for value in _extract_chinese_alias_keywords(text):
        if value not in keywords:
            keywords.append(value)

    normalized = re.sub(r"[，。！？、；：,.!?;:\r\n\t]+", " ", text)
    stop_words = [
        "请问",
        "帮我",
        "查询",
        "查一下",
        "查下",
        "看看",
        "这个",
        "那个",
        "项目",
        "客户",
        "名称",
        "编号",
        "现在",
        "当前",
        "目前",
        "进度",
        "流程",
        "状态",
        "到哪一步",
        "到哪了",
        "下一步",
        "怎么操作",
        "如何操作",
        "该怎么做",
        "怎么做",
        "怎么办",
        "是什么",
        "是多少",
        "一下",
        "吗",
        "呢",
        "了",
    ]
    cleaned = normalized
    for word in stop_words:
        cleaned = cleaned.replace(word, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    for candidate in [cleaned, *re.split(r"\s+", normalized), *re.split(r"\s+", cleaned)]:
        value = candidate.strip()
        if len(value) < 2:
            continue
        if value not in keywords:
            keywords.append(value)
    return keywords


def _extract_chinese_alias_keywords(text: str) -> list[str]:
    aliases: list[str] = []
    for match in re.finditer(r"([\u4e00-\u9fff]{2,24})(?:有限责任公司|股份有限公司|有限公司|公司|集团|项目)", text):
        value = match.group(1).strip()
        _append_alias(aliases, value)
        for marker in ("公司", "集团"):
            if marker in value:
                _append_alias(aliases, value.split(marker, 1)[0])

    for value in re.findall(r"[\u4e00-\u9fff]{2,12}", text):
        if value.endswith(("项目", "公司", "集团")):
            _append_alias(aliases, value[:-2])

    return aliases


def _append_alias(aliases: list[str], value: str) -> None:
    cleaned = value.strip()
    if len(cleaned) < 2:
        return
    if cleaned in {
        "现在",
        "当前",
        "项目",
        "客户",
        "流程",
        "重新",
        "申请",
        "评估",
    }:
        return
    if cleaned not in aliases:
        aliases.append(cleaned)


def build_project_candidate(db: Session, project: Project) -> dict:
    work_order = latest_work_order(db, project.id)
    current_status = work_order.current_status if work_order else None
    current_step = normalize_project_step(
        current_status, project.archived_at is not None, project.project_source
    )
    return {
        "id": project.id,
        "project_code": project.project_code,
        "project_name": project.project_name,
        "client_name": project.client_name,
        "current_step": current_step,
        "status_display": get_project_status_display(
            current_status, project.archived_at is not None, project.project_source
        ),
    }
