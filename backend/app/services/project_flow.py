from fastapi import HTTPException

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder

STATUS_TO_STEP = {
    "PROJECT_CREATED": "项目创建",
    "WORK_ORDER_CREATED": "项目组成员管理",
    "CONTRACT_UPLOADED": "合同上传",
    "WAIT_PRINTROOM_OFFICIAL_CONTRACT": "合同上传",
    "WAIT_FIRST_REVIEW_SUBMIT": "报告送审",
    "FIRST_REVIEWING": "一审",
    "FIRST_REVIEW_REJECTED": "报告送审",
    "FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND": "二审",
    "WAIT_SECOND_REVIEW_SUBMIT": "二审",
    "SECOND_REVIEWING": "二审",
    "SECOND_REVIEW_REJECTED": "报告送审",
    "SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD": "三审",
    "WAIT_THIRD_REVIEW_SUBMIT": "三审",
    "THIRD_REVIEWING": "三审",
    "THIRD_REVIEW_REJECTED": "报告送审",
    "THIRD_APPROVED_WAIT_PRINTROOM": "报告出具",
    "PRINTROOM_PROCESSING": "报告出具",
    "PAPER_REPORT_ISSUED": "开具发票",
}

FLOW_STEPS = ["项目创建", "项目组成员管理", "合同上传", "报告送审", "一审", "二审", "三审", "报告出具", "开具发票", "报告归档", "已归档"]


def is_system_admin(user: User) -> bool:
    return any(item.role.code == "ADMIN" for item in user.roles)


def normalize_project_step(status: str | None, archived: bool) -> str:
    if archived:
        return "已归档"
    return STATUS_TO_STEP.get(status or "", "项目创建")


def get_project_status_display(status: str | None, archived: bool) -> str:
    return normalize_project_step(status, archived)


def assert_project_creator(project: Project, current_user: User) -> None:
    if project.deleted_at is not None:
        raise HTTPException(status_code=400, detail="项目已删除，不能重复操作")
    if project.business_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有项目创建人可以执行该操作")
    if project.archived_at is not None:
        raise HTTPException(status_code=400, detail="项目已归档，不能继续操作")


def get_user_role_in_project(project: Project, work_order: WorkOrder | None, current_user: User, is_member: bool) -> str:
    if project.business_user_id == current_user.id:
        return "创建人"
    if work_order and work_order.project_leader_id == current_user.id:
        return "项目负责人"
    if is_member:
        return "项目组成员"
    if work_order and work_order.first_reviewer_id == current_user.id:
        return "一审老师"
    if work_order and work_order.second_reviewer_id == current_user.id:
        return "二审老师"
    if work_order and work_order.third_reviewer_id == current_user.id:
        return "三审老师"
    if any(item.role.code == "PRINT_ROOM" for item in current_user.roles):
        return "文印室"
    if any(item.role.code == "FINANCE" for item in current_user.roles):
        return "财务"
    return "无权限"


def build_todo_action(step: str, user_role: str) -> str | None:
    if user_role == "一审老师" and step == "一审":
        return "请处理一审"
    if user_role == "二审老师" and step == "二审":
        return "请处理二审"
    if user_role == "三审老师" and step == "三审":
        return "请处理三审"
    if user_role == "文印室" and step == "报告出具":
        return "请上传报告扫描件"
    if user_role == "财务" and step == "开具发票":
        return "请处理开票"
    if user_role in {"创建人", "项目负责人", "项目组成员"}:
        mapping = {
            "项目创建": "请完善项目组成员",
            "项目组成员管理": "请完善项目组成员",
            "合同上传": "请上传合同",
            "报告送审": "请提交报告送审",
            "报告出具": "请上传报告扫描件",
            "开具发票": "请上传电子发票",
            "报告归档": "请办理归档",
        }
        return mapping.get(step)
    return None
