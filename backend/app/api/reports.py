from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response
from urllib.parse import quote

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import ResearchReport, User
from app.services.report_builder import file_from_manifest

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{report_id}/download/{fmt}")
async def download_report(
    report_id: str,
    fmt: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(ResearchReport, report_id)
    if not report or report.user_id != user.id:
        raise HTTPException(status_code=404, detail="报告不存在")
    try:
        content, content_type, filename = file_from_manifest(report, fmt)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="报告文件不存在") from exc
    safe_name = filename.replace("\r", "").replace("\n", "")
    encoded_name = quote(safe_name)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename=report.{fmt}; filename*=UTF-8''{encoded_name}"},
    )
