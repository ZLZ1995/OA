from fastapi import HTTPException

from app.models.project import Project
from app.models.user import User
from app.models.work_order import WorkOrder

PROJECT_SOURCE_LABELS = {
    "INTERNAL": "内部项目",
    "EXTERNAL": "外部项目",
}

STATUS_TO_STEP = {
    "PROJECT_CREATED": "项目创建",
    "WORK_ORDER_CREATED": "项目组成员",
    "WAIT_CONTRACT_UPLOAD": "合同初稿上传",
    "CONTRACT_UPLOADED": "合同初稿上传",
    "WAIT_PRINTROOM_OFFICIAL_CONTRACT": "合同初稿上传",
    "WAIT_CONTRACT_REVIEW_SUBMIT": "合同初稿审核",
    "CONTRACT_REVIEWING": "合同初稿审核",
    "CONTRACT_REJECTED": "合同初稿审核",
    "CONTRACT_APPROVED": "报告送审",
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
    "PAPER_REPORT_ISSUED": "发票开具",
    "REPORT_MAILING": "报告邮寄",
    "REPORT_MAILING_COMPLETED": "报告邮寄",
    "WAIT_INVOICE_INFO": "发票开具",
    "INVOICE_INFO_REJECTED": "发票开具",
    "INVOICE_PROCESSING": "发票开具",
    "INVOICE_ISSUED": "发票开具",
    "WAIT_ARCHIVE_SUBMIT": "报告归档",
    "ARCHIVE_REVIEWING": "报告归档",
    "ARCHIVE_REJECTED": "报告归档",
    "ARCHIVED": "已归档",
}

FLOW_STEPS = [
    "项目创建",
    "项目组成员",
    "合同初稿上传",
    "合同初稿审核",
    "报告送审",
    "一审",
    "二审",
    "三审",
    "报告出具",
    "报告邮寄",
    "发票开具",
    "报告归档",
    "已归档",
]

EXTERNAL_FLOW_STEPS = [
    "项目创建",
    "合同初稿上传",
    "合同初稿审核",
    "报告送审",
    "一审",
    "二审",
    "三审",
    "报告出具",
    "报告邮寄",
    "发票开具",
    "报告归档",
    "已归档",
]


def is_system_admin(user: User) -> bool:
    return any(item.role.code == "ADMIN" for item in user.roles)


def get_project_source_display(project_source: str | None) -> str:
    return PROJECT_SOURCE_LABELS.get(project_source or "INTERNAL", "内部项目")


def get_project_leader_display_name(project: Project, leader_name: str | None = None) -> str | None:
    if project.project_source == "EXTERNAL" and project.external_project_leader_name:
        return project.external_project_leader_name
    return leader_name


def get_flow_steps(project: Project) -> list[str]:
    return EXTERNAL_FLOW_STEPS if project.project_source == "EXTERNAL" else FLOW_STEPS


def normalize_project_step(status: str | None, archived: bool, project_source: str = "INTERNAL") -> str:
    if archived:
        return "已归档"
    step = STATUS_TO_STEP.get(status or "", "项目创建")
    if project_source == "EXTERNAL" and step == "项目组成员":
        return "合同初稿上传"
    return step


def get_project_status_display(status: str | None, archived: bool, project_source: str = "INTERNAL") -> str:
    return normalize_project_step(status, archived, project_source)


def assert_project_creator(project: Project, current_user: User) -> None:
    if project.deleted_at is not None:
        raise HTTPException(status_code=400, detail="项目已删除，不能重复操作")
    if project.business_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有项目创建人可以执行该操作")
    if project.archived_at is not None:
        raise HTTPException(status_code=400, detail="项目已归档，不能继续操作")


def get_user_role_in_project(project: Project, work_order: WorkOrder | None, current_user: User, is_member: bool) -> str:
    if any(item.role.code == "ADMIN" for item in current_user.roles):
        return "管理员"
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
    if work_order and work_order.contract_reviewer_id == current_user.id:
        return "合同审核人"
    if any(item.role.code == "PRINT_ROOM" for item in current_user.roles):
        return "文印室"
    if any(item.role.code == "FINANCE" for item in current_user.roles):
        return "财务"
    if work_order and work_order.archive_reviewer_id == current_user.id:
        return "档案管理员"
    if any(item.role.code == "ARCHIVE_MANAGER" for item in current_user.roles):
        return "档案管理员"
    return "无权限"


def build_todo_action(step: str, user_role: str) -> str | None:
    if user_role == "合同审核人" and step == "合同初稿审核":
        return "请处理合同初稿审核"
    if user_role == "一审老师" and step == "一审":
        return "请处理一审"
    if user_role == "二审老师" and step == "二审":
        return "请处理二审"
    if user_role == "三审老师" and step == "三审":
        return "请处理三审"
    if user_role == "三审老师" and step == "报告出具":
        return "请上传正式报告文件和合同扫描件"
    if user_role == "文印室" and step == "报告出具":
        return "请处理报告出具"
    if user_role == "文印室" and step == "报告邮寄":
        return "请填写快递单号"
    if user_role == "财务" and step == "发票开具":
        return "请处理开票"
    if user_role == "档案管理员" and step == "报告归档":
        return "请审核归档材料"
    if user_role in {"创建人", "项目负责人", "项目组成员"}:
        mapping = {
            "项目创建": "请完善项目组成员",
            "项目组成员": "请完善项目组成员",
            "合同初稿上传": "请上传合同初稿",
            "合同初稿审核": "请提交合同初稿审核",
            "报告送审": "请提交报告送审",
            "报告出具": "请跟进报告出具",
            "报告邮寄": "请填写和确认邮寄信息",
            "发票开具": "请提交开票信息",
            "报告归档": "请办理归档",
        }
        return mapping.get(step)
    return None
