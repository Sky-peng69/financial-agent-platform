from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    organization_id: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TaskCreate(BaseModel):
    agent_name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    input_data: str | None = None


class TaskResponse(BaseModel):
    id: str
    agent_name: str
    title: str
    status: str
    input_data: str | None = None
    output_data: str | None = None
    search_references: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AnalyzeRequest(BaseModel):
    """通用 Agent 编排请求。"""

    title: str = Field(min_length=1, max_length=500)
    input_data: str | None = None
    file_ids: list[str] = Field(default_factory=list)
    generate_report: bool = False


class AgentInfo(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    tools: list[str] = []


class ResearchFileResponse(BaseModel):
    id: str
    task_id: str | None = None
    original_name: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentEvidenceResponse(BaseModel):
    id: str
    file_id: str
    source_type: str
    page_number: int | None = None
    chunk_index: int
    text: str
    location_label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportFileResponse(BaseModel):
    format: str
    filename: str
    download_url: str


class ResearchReportResponse(BaseModel):
    id: str
    task_id: str | None = None
    title: str
    report_style: str
    review_status: str
    files: list[ReportFileResponse]
    created_at: datetime


class ResearchStartRequest(BaseModel):
    report_style: str = Field(default="institutional", max_length=50)
    formats: list[str] = Field(default_factory=lambda: ["docx", "md", "pdf"])
