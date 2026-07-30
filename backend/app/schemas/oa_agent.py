from datetime import datetime

from pydantic import BaseModel, Field


class OaAgentProjectCandidate(BaseModel):
    id: int
    project_code: str
    project_name: str
    client_name: str
    current_step: str | None = None
    status_display: str | None = None


class OaAgentProjectSearchResponse(BaseModel):
    items: list[OaAgentProjectCandidate]


class OaAgentMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64)
    project_id: int | None = None


class OaAgentContextRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    project_id: int


class OaAgentSessionMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class OaAgentSessionResponse(BaseModel):
    session_id: str
    project_id: int | None = None
    messages: list[OaAgentSessionMessage] = []


class OaAgentResponse(BaseModel):
    session_id: str
    response_type: str
    answer: str | None = None
    project_id: int | None = None
    candidates: list[OaAgentProjectCandidate] = []
