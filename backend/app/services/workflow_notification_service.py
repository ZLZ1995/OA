from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.services.notification_service import create_notification

WORKFLOW_MESSAGE_TYPE = "WORKFLOW"
WORKFLOW_BIZ_TYPE = "WORKFLOW_TRANSFER"


@dataclass(frozen=True)
class WorkflowMessageTemplate:
    title: str
    content: str
    cc_title: str
    cc_content: str


def _format_comment(comment: str | None) -> str:
    value = (comment or "").strip()
    return value or "-"


def _project_member_ids(db: Session, project_id: int) -> list[int]:
    rows = (
        db.query(ProjectMember.user_id)
        .filter(ProjectMember.project_id == project_id, ProjectMember.member_role == "MEMBER")
        .all()
    )
    return [item[0] for item in rows]


def _is_project_member(db: Session, project_id: int, user_id: int) -> bool:
    return (
        db.query(ProjectMember.id)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id, ProjectMember.member_role == "MEMBER")
        .first()
        is not None
    )


def resolve_workflow_cc_users(db: Session, project: Project, receiver_user_id: int | None) -> list[int]:
    if not receiver_user_id:
        return []

    if receiver_user_id == project.project_leader_id:
        return [user_id for user_id in _project_member_ids(db, project.id) if user_id != receiver_user_id]

    if _is_project_member(db, project.id, receiver_user_id) and project.project_leader_id != receiver_user_id:
        return [project.project_leader_id]

    return []


def build_workflow_message_templates(
    *,
    action_name: str,
    work_order: WorkOrder,
    project: Project,
    sender_user: User,
    receiver_user: User | None,
    comment: str | None = None,
) -> WorkflowMessageTemplate:
    receiver_name = receiver_user.real_name if receiver_user else "待处理人"
    project_code = project.project_code
    project_name = project.project_name
    client_name = project.client_name
    work_order_no = work_order.work_order_no
    current_step = work_order.current_status
    comment_text = _format_comment(comment)

    cc_content = (
        f"项目流程发生更新，当前由{receiver_name}办理。\n"
        f"动作：{action_name}\n"
        f"项目编号：{project_code}\n"
        f"项目名称：{project_name}\n"
        f"工单号：{work_order_no}\n"
        f"当前节点：{current_step}"
    )

    templates: dict[str, tuple[str, str]] = {
        "WAIT_CONTRACT_UPLOAD_ASSIGNED": (
            "请处理合同上传",
            (
                f"{sender_user.real_name}已创建项目流程，请你办理合同初稿上传。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请上传合同初稿"
            ),
        ),
        "CONTRACT_UPLOAD_COMPLETED": (
            "请处理合同审核",
            (
                f"{sender_user.real_name}已完成合同初稿上传，请你提交合同审核。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请提交合同初稿审核"
            ),
        ),
        "SUBMIT_CONTRACT_REVIEW": (
            "请处理合同审核",
            (
                f"{sender_user.real_name}已向你提交合同初稿审核。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请审核合同初稿\n"
                f"备注：{comment_text}"
            ),
        ),
        "APPROVE_CONTRACT_REVIEW": (
            "请处理一审流程",
            (
                f"{sender_user.real_name}已完成合同初稿审核，请继续办理报告送审。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请提交一审"
            ),
        ),
        "REJECT_CONTRACT_REVIEW": (
            "请修改后重提合同",
            (
                f"{sender_user.real_name}已退回合同初稿，请修改后重新提交。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}\n"
                "下一步：请修正后重新提交合同审核"
            ),
        ),
        "SUBMIT_FIRST": (
            "请处理一审流程",
            (
                f"{sender_user.real_name}已向你提交一审任务。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                "当前节点：FIRST_REVIEWING\n"
                "下一步：请完成一审\n"
                f"备注：{comment_text}"
            ),
        ),
        "SUBMIT_SECOND": (
            "请处理二审流程",
            (
                f"{sender_user.real_name}已向你提交二审任务。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                "当前节点：SECOND_REVIEWING\n"
                "下一步：请完成二审\n"
                f"备注：{comment_text}"
            ),
        ),
        "SUBMIT_THIRD": (
            "请处理三审流程",
            (
                f"{sender_user.real_name}已向你提交三审任务。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                "当前节点：THIRD_REVIEWING\n"
                "下一步：请完成三审\n"
                f"备注：{comment_text}"
            ),
        ),
        "FIRST_APPROVE": (
            "请处理二审流程",
            (
                f"{sender_user.real_name}已完成一审，请继续办理二审提交流程。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请提交二审"
            ),
        ),
        "SECOND_APPROVE": (
            "请处理三审流程",
            (
                f"{sender_user.real_name}已完成二审，请继续办理三审提交流程。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请提交三审"
            ),
        ),
        "THIRD_APPROVE": (
            "请处理报告出具",
            (
                f"{sender_user.real_name}已完成三审，请继续办理报告出具准备。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请完善报告出具信息并转文印室"
            ),
        ),
        "FIRST_REJECT_RETURN": (
            "请修改后重提一审",
            (
                f"{sender_user.real_name}已退回一审材料，请修改后重新提交。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "SECOND_REJECT_RETURN": (
            "请修改后重提二审",
            (
                f"{sender_user.real_name}已退回二审材料，请修改后重新提交。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "THIRD_REJECT_RETURN": (
            "请修改后重提三审",
            (
                f"{sender_user.real_name}已退回三审材料，请修改后重新提交。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "TRANSFER_PRINTROOM": (
            "请处理报告出具",
            (
                f"{sender_user.real_name}已将流程转至你办理报告出具。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请办理报告出具"
            ),
        ),
        "ROLLBACK_THIRD": (
            "请处理三审退回事项",
            (
                f"{sender_user.real_name}已将流程退回给你，请重新处理三审后续事项。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "CONTRACT_ERROR": (
            "请修改后重提合同",
            (
                f"{sender_user.real_name}已将流程退回项目方，请修正合同相关内容后继续办理。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "REPORT_ERROR": (
            "请处理报告问题",
            (
                f"{sender_user.real_name}已将报告问题退回给你，请继续处理。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"备注：{comment_text}"
            ),
        ),
        "ISSUE_PAPER_REPORT": (
            "请处理后续流程",
            (
                f"{sender_user.real_name}已完成报告出具，请继续办理后续流程。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请处理开票或邮寄"
            ),
        ),
        "SUBMIT_MAILING": (
            "请处理报告邮寄",
            (
                f"{sender_user.real_name}已提交报告邮寄任务，请你填写邮寄信息。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}"
            ),
        ),
        "RESUBMIT_MAILING": (
            "请处理报告邮寄",
            (
                f"{sender_user.real_name}已重新提交报告邮寄任务，请你填写邮寄信息。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}"
            ),
        ),
        "PRINT_ROOM_SUBMIT_EXPRESS": (
            "请核对并确认邮寄",
            (
                f"{sender_user.real_name}已填写快递信息，请你确认报告邮寄。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请确认邮寄结果\n"
                f"备注：{comment_text}"
            ),
        ),
        "PROJECT_CONFIRM_MAILING": (
            "请处理开票或归档",
            (
                f"{sender_user.real_name}已确认报告邮寄完成，请继续办理后续流程。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                "下一步：请继续办理开票或归档"
            ),
        ),
        "SUBMIT_INVOICE_INFO": (
            "请处理发票开具",
            (
                f"{sender_user.real_name}已提交开票信息，请你办理开票。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"备注：{comment_text}"
            ),
        ),
        "REJECT_INVOICE_INFO": (
            "请修改后重提开票信息",
            (
                f"{sender_user.real_name}已退回开票信息，请修改后重新提交。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "FINANCE_COMPLETE_INVOICE": (
            "请核对并确认开票",
            (
                f"{sender_user.real_name}已完成开票，请你确认开票结果。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}"
            ),
        ),
        "PROJECT_CONFIRM_INVOICE": (
            "请处理后续流程",
            (
                f"{sender_user.real_name}已确认发票结果，请继续办理后续流程。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}"
            ),
        ),
        "PROJECT_RETURN_INVOICE": (
            "发票已退回，请处理",
            (
                f"{sender_user.real_name}已将发票退回给你，请重新处理。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "WITHDRAW_INVOICE_INFO": (
            "请处理后续流程",
            (
                f"{sender_user.real_name}已撤回开票信息，请继续办理后续流程。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}"
            ),
        ),
        "ARCHIVE_SUBMIT_ONLINE": (
            "请处理归档审核",
            (
                f"{sender_user.real_name}已提交归档审核，请你办理归档审核。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"备注：{comment_text}"
            ),
        ),
        "ARCHIVE_SUBMIT_OFFLINE": (
            "请处理归档审核",
            (
                f"{sender_user.real_name}已提交线下归档审核，请你办理归档审核。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"备注：{comment_text}"
            ),
        ),
        "ARCHIVE_APPROVE": (
            "请处理归档完成",
            (
                f"{sender_user.real_name}已完成归档审核，请继续办理归档完成操作。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}"
            ),
        ),
        "ARCHIVE_REJECT": (
            "请修改后重提归档材料",
            (
                f"{sender_user.real_name}已退回归档材料，请修改后重新提交。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"退回说明：{comment_text}"
            ),
        ),
        "ARCHIVE_FINALIZE": (
            "项目归档已完成",
            (
                f"{sender_user.real_name}已完成归档，项目流程结束。\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                "当前节点：已归档"
            ),
        ),
    }

    cc_title_map = {
        "WAIT_CONTRACT_UPLOAD_ASSIGNED": "合同初稿上传已发起",
        "CONTRACT_UPLOAD_COMPLETED": "合同初稿已上传",
        "SUBMIT_CONTRACT_REVIEW": "合同审核已提交",
        "APPROVE_CONTRACT_REVIEW": "合同审核已完成",
        "REJECT_CONTRACT_REVIEW": "合同初稿已退回",
        "SUBMIT_FIRST": "一审任务已提交",
        "SUBMIT_SECOND": "二审任务已提交",
        "SUBMIT_THIRD": "三审任务已提交",
        "FIRST_APPROVE": "一审已完成",
        "SECOND_APPROVE": "二审已完成",
        "THIRD_APPROVE": "三审已完成",
        "FIRST_REJECT_RETURN": "一审材料已退回",
        "SECOND_REJECT_RETURN": "二审材料已退回",
        "THIRD_REJECT_RETURN": "三审材料已退回",
        "TRANSFER_PRINTROOM": "报告出具已流转",
        "ROLLBACK_THIRD": "三审后续已退回",
        "CONTRACT_ERROR": "合同问题已退回",
        "REPORT_ERROR": "报告问题已退回",
        "ISSUE_PAPER_REPORT": "报告出具已完成",
        "SUBMIT_MAILING": "报告邮寄已提交",
        "RESUBMIT_MAILING": "报告邮寄已重新提交",
        "PRINT_ROOM_SUBMIT_EXPRESS": "邮寄信息已填写",
        "PROJECT_CONFIRM_MAILING": "报告邮寄已确认",
        "SUBMIT_INVOICE_INFO": "开票信息已提交",
        "REJECT_INVOICE_INFO": "开票信息已退回",
        "FINANCE_COMPLETE_INVOICE": "发票已开具",
        "PROJECT_CONFIRM_INVOICE": "开票结果已确认",
        "PROJECT_RETURN_INVOICE": "发票已退回",
        "WITHDRAW_INVOICE_INFO": "开票信息已撤回",
        "ARCHIVE_SUBMIT_ONLINE": "归档审核已提交",
        "ARCHIVE_SUBMIT_OFFLINE": "线下归档已提交",
        "ARCHIVE_APPROVE": "归档审核已完成",
        "ARCHIVE_REJECT": "归档材料已退回",
        "ARCHIVE_FINALIZE": "项目归档已完成",
    }

    title, content = templates.get(
        action_name,
        (
            "请处理流程任务",
            (
                f"{sender_user.real_name}已将工单流转至你处理。\n"
                f"动作：{action_name}\n"
                f"项目编号：{project_code}\n"
                f"项目名称：{project_name}\n"
                f"客户名称：{client_name}\n"
                f"工单号：{work_order_no}\n"
                f"当前节点：{current_step}\n"
                f"备注：{comment_text}"
            ),
        ),
    )
    cc_title = cc_title_map.get(action_name, "流程任务已流转")

    return WorkflowMessageTemplate(
        title=title,
        content=content,
        cc_title=cc_title,
        cc_content=cc_content,
    )


def send_workflow_notification(
    db: Session,
    *,
    project: Project,
    work_order: WorkOrder,
    sender_user: User,
    receiver_user_id: int | None,
    action_name: str,
    comment: str | None = None,
    link_type: str = "PROJECT",
    link_target_id: int | None = None,
    biz_id: int | None = None,
) -> None:
    if not receiver_user_id:
        return
    if sender_user.id == receiver_user_id:
        return

    receiver_user = db.query(User).filter(User.id == receiver_user_id, User.is_active.is_(True)).first()
    if not receiver_user:
        return

    templates = build_workflow_message_templates(
        action_name=action_name,
        work_order=work_order,
        project=project,
        sender_user=sender_user,
        receiver_user=receiver_user,
        comment=comment,
    )
    cc_user_ids = resolve_workflow_cc_users(db, project, receiver_user_id)
    effective_biz_id = biz_id or work_order.id
    target_id = link_target_id if link_target_id is not None else project.id

    create_notification(
        db,
        user_id=receiver_user_id,
        biz_type=WORKFLOW_BIZ_TYPE,
        biz_id=effective_biz_id,
        title=templates.title,
        content=templates.content,
        message_type=WORKFLOW_MESSAGE_TYPE,
        priority="NORMAL",
        sender_user_id=sender_user.id,
        project_id=project.id,
        work_order_id=work_order.id,
        process_status="PENDING",
        cc_flag=False,
        group_key=f"WORK_ORDER:{work_order.id}",
        link_type=link_type,
        link_target_id=target_id,
    )

    for cc_user_id in cc_user_ids:
        if cc_user_id == receiver_user_id:
            continue
        create_notification(
            db,
            user_id=cc_user_id,
            biz_type=WORKFLOW_BIZ_TYPE,
            biz_id=effective_biz_id,
            title=templates.cc_title,
            content=templates.cc_content,
            message_type=WORKFLOW_MESSAGE_TYPE,
            priority="NORMAL",
            sender_user_id=sender_user.id,
            project_id=project.id,
            work_order_id=work_order.id,
            process_status="PENDING",
            cc_flag=True,
            group_key=f"WORK_ORDER:{work_order.id}",
            link_type=link_type,
            link_target_id=target_id,
        )
