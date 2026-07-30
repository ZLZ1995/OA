from sqlalchemy.orm import Session

from app.models.contract_review_record import ContractReviewRecord
from app.models.project import Project
from app.models.project_update_log import ProjectUpdateLog
from app.models.review_record import ReviewRecord
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.models.workflow_log import WorkflowLog
from app.services.oa_agent_project_access import latest_work_order
from app.services.project_flow import build_todo_action, get_user_role_in_project, normalize_project_step


def build_authorized_project_context(db: Session, current_user: User, project: Project) -> tuple[dict, set[str]]:
    work_order = latest_work_order(db, project.id)
    role = _resolve_user_project_role(db, current_user, project, work_order)
    current_step = normalize_project_step(
        work_order.current_status if work_order else None,
        project.archived_at is not None,
        project.project_source,
    )
    current_handler_name = _user_name(db, work_order.current_handler_user_id) if work_order else None
    available_action = build_todo_action(current_step, role) or _build_non_handler_action(current_handler_name)
    operation = _resolve_operation_guide(project.id, current_step, role, available_action)

    modules: set[str] = {"tasks"}
    context = {
        "project": {
            "id": project.id,
            "project_code": project.project_code,
            "project_name": project.project_name,
            "client_name": project.client_name,
            "status": project.status,
            "termination_status": project.termination_status,
            "archived": project.archived_at is not None,
        },
        "flow": {
            "current_step": current_step,
            "current_work_order_status": work_order.current_status if work_order else None,
            "current_handler_name": current_handler_name,
            "user_role_in_project": role,
            "available_action": available_action,
            "operation_entry": operation["entry"],
            "operation_url": operation["url"],
            "operation_hint": operation["hint"],
        },
        "approvals": _approval_records(db, work_order),
        "attachments": _attachment_metadata(db, work_order),
        "comments": _comment_records(db, project, work_order),
        "tasks": [
            {
                "current_step": current_step,
                "handler_name": current_handler_name,
                "suggested_action": available_action,
                "operation_entry": operation["entry"],
                "operation_url": operation["url"],
                "operation_hint": operation["hint"],
            }
        ],
    }
    if context["approvals"]:
        modules.add("approvals")
    if context["attachments"]:
        modules.add("attachments")
    if context["comments"]:
        modules.add("comments")
    return context, modules


def build_deterministic_project_answer(context: dict) -> str:
    project = context["project"]
    flow = context["flow"]
    lines = [
        f"项目：{project['project_name']}（{project['project_code']}）",
        f"客户：{project['client_name']}",
        f"当前节点：{flow['current_step']}",
        f"你的项目角色：{flow['user_role_in_project']}",
    ]
    if flow.get("current_handler_name"):
        lines.append(f"当前处理人：{flow['current_handler_name']}")
    lines.extend(
        [
            f"下一步：{flow['available_action']}",
            f"操作入口：{flow['operation_entry']}。",
            f"操作提示：{flow['operation_hint']}",
            f"直达链接：{flow['operation_url']}",
        ]
    )
    if context.get("attachments"):
        lines.append("附件：可查看附件名称、类型、上传人和上传时间；Agent 不读取附件正文。")
    return "\n".join(lines)


def _resolve_user_project_role(db: Session, current_user: User, project: Project, work_order: WorkOrder | None) -> str:
    from app.models.project_member import ProjectMember

    is_member = (
        db.query(ProjectMember.id)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == current_user.id)
        .first()
        is not None
    )
    return get_user_role_in_project(project, work_order, current_user, is_member)


def _resolve_operation_guide(project_id: int, step: str, role: str, action: str) -> dict[str, str]:
    panel_by_step = {
        "项目创建": ("members", "项目组成员", "添加项目负责人/项目组成员后，点击保存或完成成员配置。"),
        "项目组成员": ("members", "项目组成员", "添加或确认项目负责人、项目组成员后，点击完成成员配置。"),
        "合同初稿上传": ("contract", "合同初稿上传", "选择合同审核人，上传合同初稿扫描件，然后提交合同初稿审核。"),
        "合同初稿审核": ("contractReview", "合同初稿审核", "进入合同审核处理区，按当前角色提交、通过、退回或转交文印室。"),
        "报告送审": ("review", "报告送审", "上传待审报告，选择对应审核老师，然后提交送审。"),
        "一审": ("review", "报告审核", "进入报告审核面板，处理一审意见或等待一审老师处理。"),
        "二审": ("review", "报告审核", "进入报告审核面板，按当前流向提交或处理二审。"),
        "三审": ("review", "报告审核", "进入报告审核面板，按当前流向提交或处理三审。"),
        "外部审核确认": ("externalAuditConfirm", "外部审核确认", "确认是否涉及外部审核，并按页面提示继续流转。"),
        "外部审核复核": ("externalReview", "外部审核复核", "上传外部审核意见和回复文件，继续推进复核流转。"),
        "签发审核": ("signoff", "签发审核", "上传签发所需附件，或由首席评估师处理签发审核。"),
        "报告出具": ("issue", "报告出具", "上传正式报告文件和合同扫描件，或由文印室录入正式编号。"),
        "报告邮寄": ("mailing", "报告邮寄", "填写收件人、地址、电话和快递单号，并确认邮寄状态。"),
        "发票开具": ("invoice", "发票开具", "项目方提交开票信息，财务在本面板处理开票。"),
        "报告归档": ("archive", "报告归档", "提交或审核归档材料，确认底稿归档完成。"),
        "已归档": ("archive", "报告归档", "项目已归档，可在归档面板查看归档信息。"),
    }
    panel_key, panel_label, hint = panel_by_step.get(
        step,
        ("basic", "项目基本信息", "先查看项目基础信息和当前流程状态，再按页面提示进入对应办理区。"),
    )
    if "当前有权限处理流程的账号" in action:
        handler_name = action.split("当前有权限处理流程的账号：", 1)[1].split("。", 1)[0].strip()
        hint = f"当前账号不是本节点处理人，当前有权限处理流程的账号：{handler_name}。请联系该账号处理，或等待其完成后再继续。"
    return {
        "entry": f"项目详情页 > 项目流程 > {panel_label}面板",
        "url": f"/projects/{project_id}/flow?todoPanel={panel_key}",
        "hint": hint,
    }


def _build_non_handler_action(current_handler_name: str | None) -> str:
    if current_handler_name:
        return f"当前账号不是本节点处理人。当前有权限处理流程的账号：{current_handler_name}。请联系该账号处理，或等待其完成后再继续。"
    return "当前账号暂无待办操作，请在项目流程页查看详情。"


def _approval_records(db: Session, work_order: WorkOrder | None) -> list[dict]:
    if not work_order:
        return []
    review_rows = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.work_order_id == work_order.id)
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .limit(20)
        .all()
    )
    contract_rows = (
        db.query(ContractReviewRecord)
        .filter(ContractReviewRecord.work_order_id == work_order.id)
        .order_by(ContractReviewRecord.created_at.desc(), ContractReviewRecord.id.desc())
        .limit(20)
        .all()
    )
    items = [
        {
            "type": "review",
            "round": row.review_round,
            "action": row.action,
            "reviewer_name": _user_name(db, row.reviewer_user_id),
            "comment": row.comment,
            "acted_at": row.acted_at.isoformat() if row.acted_at else None,
        }
        for row in review_rows
    ]
    items.extend(
        {
            "type": "contract_review",
            "action": row.action_type,
            "operator_name": _user_name(db, row.operator_user_id),
            "reviewer_name": _user_name(db, row.reviewer_user_id),
            "comment": row.comment,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in contract_rows
    )
    return items


def _attachment_metadata(db: Session, work_order: WorkOrder | None) -> list[dict]:
    if not work_order:
        return []
    rows = (
        db.query(WorkOrderFile)
        .filter(WorkOrderFile.work_order_id == work_order.id)
        .order_by(WorkOrderFile.uploaded_at.desc(), WorkOrderFile.id.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": row.id,
            "origin_file_name": row.origin_file_name,
            "file_category": row.file_category,
            "business_stage": row.business_stage,
            "version_no": row.version_no,
            "is_current": row.is_current,
            "file_size": row.file_size,
            "uploaded_by_name": _user_name(db, row.uploaded_by),
            "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
        }
        for row in rows
    ]


def _comment_records(db: Session, project: Project, work_order: WorkOrder | None) -> list[dict]:
    workflow_rows = []
    if work_order:
        workflow_rows = (
            db.query(WorkflowLog)
            .filter(WorkflowLog.work_order_id == work_order.id, WorkflowLog.remark.isnot(None))
            .order_by(WorkflowLog.created_at.desc(), WorkflowLog.id.desc())
            .limit(20)
            .all()
        )
    update_rows = (
        db.query(ProjectUpdateLog)
        .filter(ProjectUpdateLog.project_id == project.id)
        .order_by(ProjectUpdateLog.created_at.desc(), ProjectUpdateLog.id.desc())
        .limit(20)
        .all()
    )
    items = [
        {
            "type": "workflow_log",
            "action_type": row.action_type,
            "operator_name": _user_name(db, row.operator_user_id),
            "remark": row.remark,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in workflow_rows
    ]
    items.extend(
        {
            "type": "project_update",
            "operator_name": _user_name(db, row.operator_user_id),
            "remark": row.remark,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in update_rows
    )
    return items


def _user_name(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    return db.query(User.real_name).filter(User.id == user_id).scalar()
