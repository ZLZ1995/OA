from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.oa_agent import (
    OaAgentContextRequest,
    OaAgentMessageRequest,
    OaAgentProjectSearchResponse,
    OaAgentResponse,
    OaAgentSessionMessage,
    OaAgentSessionResponse,
)
from app.services.oa_agent_audit import record_agent_module_access
from app.services.oa_agent_context import build_authorized_project_context
from app.services.oa_agent_llm import generate_agent_answer
from app.services.oa_agent_project_access import (
    build_project_candidate,
    get_accessible_project,
    search_accessible_projects,
    search_accessible_projects_from_message,
)
from app.services.oa_agent_session import (
    append_agent_message,
    clear_agent_sessions,
    get_or_create_agent_session,
)

router = APIRouter(prefix="/oa-agent", tags=["OA Agent"])


@router.get("/projects/search", response_model=OaAgentProjectSearchResponse)
def search_projects(
    keyword: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OaAgentProjectSearchResponse:
    projects = search_accessible_projects(db, current_user, keyword, limit=10)
    return OaAgentProjectSearchResponse(
        items=[build_project_candidate(db, project) for project in projects]
    )


@router.post("/context", response_model=OaAgentSessionResponse)
def set_context(
    payload: OaAgentContextRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OaAgentSessionResponse:
    project = get_accessible_project(db, current_user, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="未找到可访问的项目")
    session = get_or_create_agent_session(current_user.id, payload.session_id)
    session.project_id = project.id
    return _serialize_session(session)


@router.get("/session", response_model=OaAgentSessionResponse)
def get_session(
    session_id: str | None = None,
    current_user: User = Depends(get_current_user),
) -> OaAgentSessionResponse:
    session = get_or_create_agent_session(current_user.id, session_id)
    return _serialize_session(session)


@router.delete("/session", status_code=204)
def clear_session(current_user: User = Depends(get_current_user)) -> None:
    clear_agent_sessions(current_user.id)


@router.post("/messages", response_model=OaAgentResponse)
def send_message(
    payload: OaAgentMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OaAgentResponse:
    session = get_or_create_agent_session(current_user.id, payload.session_id)
    append_agent_message(session, "user", payload.message)

    project_id = payload.project_id or session.project_id
    if project_id:
        project = get_accessible_project(db, current_user, project_id)
        if not project:
            answer = "未找到可访问的项目。请确认项目名称或联系管理员确认权限。"
            append_agent_message(session, "assistant", answer)
            return OaAgentResponse(
                session_id=session.session_id,
                response_type="permission_denied",
                answer=answer,
            )
        session.project_id = project.id
        answer = _generate_project_answer(db, current_user, session.session_id, payload.message, project)
        append_agent_message(session, "assistant", answer)
        return OaAgentResponse(
            session_id=session.session_id,
            response_type="answer",
            answer=answer,
            project_id=project.id,
        )

    candidates = search_accessible_projects_from_message(db, current_user, payload.message, limit=10)
    if len(candidates) == 1:
        project = candidates[0]
        session.project_id = project.id
        answer = _generate_project_answer(db, current_user, session.session_id, payload.message, project)
        append_agent_message(session, "assistant", answer)
        return OaAgentResponse(
            session_id=session.session_id,
            response_type="answer",
            answer=answer,
            project_id=project.id,
        )
    if len(candidates) > 1:
        answer = "找到多个相关项目，请先选择一个项目后继续提问。"
        append_agent_message(session, "assistant", answer)
        return OaAgentResponse(
            session_id=session.session_id,
            response_type="candidates",
            answer=answer,
            candidates=[build_project_candidate(db, item) for item in candidates],
        )

    answer = "我可以协助查询项目进度和说明下一步操作。请提供项目名称、项目编号或客户名称。"
    append_agent_message(session, "assistant", answer)
    return OaAgentResponse(
        session_id=session.session_id,
        response_type="answer",
        answer=answer,
    )


def _serialize_session(session) -> OaAgentSessionResponse:
    return OaAgentSessionResponse(
        session_id=session.session_id,
        project_id=session.project_id,
        messages=[
            OaAgentSessionMessage(
                role=item.role,
                content=item.content,
                created_at=item.created_at,
            )
            for item in session.messages
        ],
    )


def _generate_project_answer(db: Session, current_user: User, session_id: str, message: str, project) -> str:
    context, modules = build_authorized_project_context(db, current_user, project)
    record_agent_module_access(
        db,
        user_id=current_user.id,
        project_id=project.id,
        session_id=session_id,
        modules=modules,
    )
    db.commit()
    return generate_agent_answer(message, context)
