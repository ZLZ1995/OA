from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.services.project_field_normalizer import (
    EVALUATION_BUSINESS_NATURES,
    PROJECT_SOURCES,
    REPORT_TYPES,
    normalize_evaluation_business_nature,
    normalize_external_project_leader_name,
    normalize_project_source,
    normalize_report_type,
    normalize_undertaking_unit,
)


class ProjectBase(BaseModel):
    project_code: str = Field(min_length=1, max_length=64)
    undertaking_unit: str = Field(min_length=1, max_length=32)
    project_name: str = Field(min_length=1, max_length=255)
    client_name: str = Field(min_length=1, max_length=255)
    evaluation_business_nature: str | None = Field(default=None, min_length=1, max_length=64)
    report_type: str = Field(default="评估报告", min_length=1, max_length=32)
    valuation_base_date: date | None = None
    business_salesman: str = Field(default="", max_length=255)
    project_amount: float | None = Field(default=None, ge=0)
    project_source: str = Field(default="INTERNAL", min_length=1, max_length=16)
    external_project_leader_name: str | None = Field(default=None, max_length=255)
    business_user_id: int
    project_leader_id: int
    department_id: int | None = None
    start_date: date | None = None
    due_date: date | None = None
    status: str = Field(default="ACTIVE", max_length=32)
    description: str | None = None

    @model_validator(mode="after")
    def validate_project_fields(self) -> "ProjectBase":
        self.undertaking_unit = normalize_undertaking_unit(self.undertaking_unit)
        self.evaluation_business_nature = normalize_evaluation_business_nature(self.evaluation_business_nature)
        if self.evaluation_business_nature not in EVALUATION_BUSINESS_NATURES:
            raise ValueError("评估业务性质不合法")
        self.report_type = normalize_report_type(self.report_type)
        if self.report_type not in REPORT_TYPES:
            raise ValueError("报告类型不合法")
        self.project_source = normalize_project_source(self.project_source)
        if self.project_source not in PROJECT_SOURCES:
            raise ValueError("项目来源不合法")
        self.external_project_leader_name = normalize_external_project_leader_name(self.external_project_leader_name)
        if self.project_source != "EXTERNAL":
            self.external_project_leader_name = None
        self.business_salesman = self.business_salesman.strip()
        return self


class ProjectCreate(ProjectBase):
    project_code: str | None = None


class ProjectUpdate(BaseModel):
    undertaking_unit: str | None = Field(default=None, min_length=1, max_length=32)
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    evaluation_business_nature: str | None = Field(default=None, min_length=1, max_length=64)
    report_type: str | None = Field(default=None, min_length=1, max_length=32)
    valuation_base_date: date | None = None
    business_salesman: str | None = Field(default=None, min_length=1, max_length=255)
    project_amount: float | None = Field(default=None, ge=0)
    project_source: str | None = Field(default=None, min_length=1, max_length=16)
    external_project_leader_name: str | None = Field(default=None, max_length=255)
    business_user_id: int | None = None
    project_leader_id: int | None = None
    department_id: int | None = None
    start_date: date | None = None
    due_date: date | None = None
    status: str | None = Field(default=None, max_length=32)
    description: str | None = None


class ProjectResponse(ProjectBase):
    id: int
    project_source_display: str = "评估一部"
    project_leader_display_name: str | None = None
    display_project_leader_name: str | None = None
    report_no: str | None = None
    contract_no: str | None = None
    status_display: str = "项目创建"
    contract_review_status: str | None = None
    contract_review_status_display: str | None = None
    termination_status: str | None = None
    termination_reason: str | None = None
    termination_requested_by: int | None = None
    termination_requested_at: datetime | None = None
    termination_approved_by: int | None = None
    termination_approved_at: datetime | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
