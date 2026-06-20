from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import list_agents, get_agent
from app.core.database import get_db
from app.models import User
from app.schemas import AgentInfo, TaskCreate, TaskResponse, AnalyzeRequest
from app.api.deps import get_current_user
from app.services.agent_runner import run_agent_stream
from app.services.orchestrator import run_orchestrated_analysis

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentInfo])
async def list_all_agents(category: str | None = Query(None)):
    """列出所有可用 Agent"""
    return list_agents(category)


@router.get("/{name}", response_model=AgentInfo)
async def get_agent_info(name: str):
    agent = get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' 不存在")
    return agent


@router.post("/{name}/run", response_model=TaskResponse)
async def run_agent(
    name: str,
    data: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """运行单个 Agent（直接调用模式）"""
    agent = get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' 不存在")

    task = await run_agent_stream(
        agent_name=name,
        title=data.title,
        user_input=data.input_data or data.title,
        user_id=user.id,
        db=db,
    )
    return TaskResponse.model_validate(task)


@router.post("/analyze", response_model=TaskResponse)
async def analyze(
    data: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """百炼模式：Commander 自动规划 → 多 Agent 并行分析 → 汇总报告"""
    task = await run_orchestrated_analysis(
        user_input=data.input_data or data.title,
        title=data.title,
        user_id=user.id,
        db=db,
    )
    return TaskResponse.model_validate(task)
