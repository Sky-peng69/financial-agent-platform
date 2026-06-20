from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=100)
    role: str = "investor"


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
