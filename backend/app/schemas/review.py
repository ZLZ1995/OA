from datetime import datetime

from pydantic import BaseModel, Field


class ReviewSubmitRequest(BaseModel):
    work_order_id: int
    review_round: str = Field(pattern="^(FIRST|SECOND|THIRD)$")
    reviewer_user_id: int
    comment: str | None = None


class ReviewDecisionRequest(BaseModel):
    work_order_id: int
    review_round: str = Field(pattern="^(FIRST|SECOND|THIRD)$")
    action: str = Field(pattern="^(APPROVE|REJECT_RETURN)$")
    comment: str | None = None


class ReviewRecordResponse(BaseModel):
    id: int
    work_order_id: int
    review_round: str
    reviewer_user_id: int
    action: str
    comment: str | None
    acted_at: datetime


class ReviewRecordListResponse(BaseModel):
    items: list[ReviewRecordResponse]
