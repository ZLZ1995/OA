from sqlalchemy.orm import Session

from app.models.oa_agent_audit_log import OaAgentAuditLog

SENSITIVE_MODULES = {"approvals", "attachments", "comments", "tasks"}


def record_agent_module_access(
    db: Session,
    *,
    user_id: int,
    project_id: int,
    session_id: str,
    modules: set[str],
) -> None:
    for module in sorted(modules.intersection(SENSITIVE_MODULES)):
        db.add(
            OaAgentAuditLog(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                module=module,
                action="READ",
            )
        )
