from datetime import datetime

from pydantic import BaseModel, Field


class ReviewSubmitRequest(BaseModel):
    work_order_id: int
    review_round: str = Field(pattern="^(FIRST|SECOND|THIRD|EXTERNAL_FIRST|EXTERNAL_SECOND|EXTERNAL_THIRD)$")
    reviewer_user_id: int
    comment: str | None = None


class ReviewDecisionRequest(BaseModel):
    work_order_id: int
    review_round: str = Field(pattern="^(FIRST|SECOND|THIRD|EXTERNAL_FIRST|EXTERNAL_SECOND|EXTERNAL_THIRD)$")
    action: str = Field(pattern="^(APPROVE|REJECT_RETURN)$")
    comment: str | None = None


class ReviewApprovalRoutingRequest(BaseModel):
    work_order_id: int
    review_round: str = Field(pattern="^(FIRST|SECOND|EXTERNAL_FIRST|EXTERNAL_SECOND)$")
    route_mode: str = Field(pattern="^(REVIEWER_SELECT_NEXT|RETURN_TO_PROJECT_LEADER)$")
    comment: str | None = None


class ReviewRecallRoutingRequest(BaseModel):
    work_order_id: int
    review_round: str = Field(pattern="^(SECOND|THIRD|EXTERNAL_SECOND|EXTERNAL_THIRD)$")
    comment: str | None = None


class ReviewAssigneeChangeRequest(BaseModel):
    work_order_id: int
    review_round: str = Field(pattern="^(FIRST|SECOND|THIRD|EXTERNAL_FIRST|EXTERNAL_SECOND|EXTERNAL_THIRD)$")
    reviewer_user_id: int
    comment: str | None = None


class ReviewRecordResponse(BaseModel):
    id: int
    work_order_id: int
    review_round: str
    reviewer_user_id: int
    reviewer_name: str | None = None
    action: str
    comment: str | None
    acted_at: datetime
    source_record_id: int | None = None
    source_round_comment: str | None = None
    source_round_reviewer_name: str | None = None
    auto_carried_from_previous: bool = False
    transferred_to_next: bool = False
    transferred_to_round: str | None = None


class ReviewRecordListResponse(BaseModel):
    items: list[ReviewRecordResponse]


class ReviewCandidateResponse(BaseModel):
    user_id: int
    username: str
    real_name: str


class ReviewCandidateListResponse(BaseModel):
    items: list[ReviewCandidateResponse]
