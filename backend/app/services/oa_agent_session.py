from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class OaAgentStoredMessage:
    role: str
    content: str
    created_at: datetime


@dataclass
class OaAgentStoredSession:
    session_id: str
    user_id: int
    project_id: int | None = None
    messages: list[OaAgentStoredMessage] = field(default_factory=list)


_SESSIONS: dict[tuple[int, str], OaAgentStoredSession] = {}


def get_or_create_agent_session(user_id: int, session_id: str | None = None) -> OaAgentStoredSession:
    resolved_session_id = session_id or uuid4().hex
    key = (user_id, resolved_session_id)
    session = _SESSIONS.get(key)
    if session is None:
        session = OaAgentStoredSession(session_id=resolved_session_id, user_id=user_id)
        _SESSIONS[key] = session
    return session


def append_agent_message(session: OaAgentStoredSession, role: str, content: str) -> None:
    session.messages.append(
        OaAgentStoredMessage(role=role, content=content, created_at=datetime.now())
    )
    if len(session.messages) > 20:
        session.messages = session.messages[-20:]


def clear_agent_sessions(user_id: int) -> None:
    for key in [key for key in _SESSIONS if key[0] == user_id]:
        _SESSIONS.pop(key, None)
