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
    """百炼编排模式：只需提供标题和分析内容，Commander 自动分配 Agent"""
    title: str = Field(min_length=1, max_length=500)
    input_data: str | None = None


class AgentInfo(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    tools: list[str] = []


class ResearchFileResponse(BaseModel):
    id: str
    research_subject_id: str | None = None
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
    research_subject_id: str | None = None
    source_type: str
    page_number: int | None = None
    chunk_index: int
    text: str
    location_label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceSnippetResponse(BaseModel):
    id: str
    file_id: str
    page_number: int | None = None
    location_label: str
    text: str

    model_config = {"from_attributes": True}


class ResearchSubjectCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    ticker: str | None = Field(default=None, max_length=50)
    industry: str | None = Field(default=None, max_length=100)
    current_view: str | None = None
    confidence_level: str | None = Field(default=None, max_length=20)
    evidence_strength: str | None = Field(default=None, max_length=20)


class ResearchSubjectResponse(BaseModel):
    id: str
    company_name: str
    ticker: str | None = None
    industry: str | None = None
    status: str
    current_view: str | None = None
    confidence_level: str | None = None
    evidence_strength: str | None = None
    last_view_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchClaimCreate(BaseModel):
    content: str = Field(min_length=1)
    direction: str = Field(default="neutral", max_length=20)
    confidence_level: str = Field(default="medium", max_length=20)
    evidence_strength: str = Field(default="medium", max_length=20)
    status: str = Field(default="needs_review", max_length=30)


class ResearchAssetReviewUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, max_length=30)
    review_note: str | None = None


class ResearchClaimResponse(BaseModel):
    id: str
    research_subject_id: str
    content: str
    direction: str
    confidence_level: str
    evidence_strength: str
    status: str
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: str = "needs_review"
    evidence_items: list[EvidenceSnippetResponse] = Field(default_factory=list)
    review_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchAssumptionCreate(BaseModel):
    content: str = Field(min_length=1)
    category: str = Field(default="business", max_length=50)
    confidence_level: str = Field(default="medium", max_length=20)
    status: str = Field(default="active", max_length=30)


class ResearchAssumptionResponse(BaseModel):
    id: str
    research_subject_id: str
    content: str
    category: str
    confidence_level: str
    status: str
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: str = "needs_review"
    evidence_items: list[EvidenceSnippetResponse] = Field(default_factory=list)
    review_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchChallengeCreate(BaseModel):
    question: str = Field(min_length=1)
    claim_id: str | None = None
    risk_level: str = Field(default="medium", max_length=20)
    suggested_action: str | None = None


class ResearchChallengeResponse(BaseModel):
    id: str
    research_subject_id: str
    claim_id: str | None = None
    question: str
    risk_level: str
    suggested_action: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionMemoCreate(BaseModel):
    current_conclusion: str = Field(min_length=1)
    key_basis: str | None = None
    biggest_uncertainty: str | None = None
    suggested_action: str | None = None
    review_status: str = Field(default="ai_draft", max_length=30)


class DecisionMemoResponse(BaseModel):
    id: str
    research_subject_id: str
    current_conclusion: str
    key_basis: str | None = None
    biggest_uncertainty: str | None = None
    suggested_action: str | None = None
    review_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchSubjectWorkspaceResponse(BaseModel):
    subject: ResearchSubjectResponse
    claims: list[ResearchClaimResponse]
    assumptions: list[ResearchAssumptionResponse]
    challenges: list[ResearchChallengeResponse]
    decision_memos: list[DecisionMemoResponse]
    evidence_count: int
