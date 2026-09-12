import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import DocumentEvidence, ResearchFile, Task, User, FileStatus
from app.schemas import DocumentEvidenceResponse, ResearchFileResponse
from app.services.storage import LocalStorage

router = APIRouter(prefix="/api/files", tags=["files"])
storage = LocalStorage(settings.storage_path)


def _extract_pdf_pages(content: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(content))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            pages.append((index, page_text))
    return pages


def _format_pages_text(pages: list[tuple[int, str]]) -> str:
    return "\n\n".join(f"【第 {page_number} 页】\n{text}" for page_number, text in pages).strip()


@router.post("", response_model=ResearchFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    task_id: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf") or file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="当前仅支持 PDF 文件")

    content = await file.read(settings.max_upload_size_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"文件不能超过 {settings.max_upload_size_mb}MB")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="文件内容不是有效的 PDF")

    if task_id:
        task = await db.get(Task, task_id)
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="任务不存在")

    try:
        pages = _extract_pdf_pages(content)
        extracted_text = _format_pages_text(pages)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF 解析失败: {exc}") from exc

    file_id = str(uuid.uuid4())
    storage_key = f"files/{user.id}/{file_id}.pdf"
    storage.save(storage_key, content)
    record = ResearchFile(
        id=file_id,
        user_id=user.id,
        organization_id=user.organization_id,
        task_id=task_id,
        original_name=filename,
        storage_key=storage_key,
        content_type="application/pdf",
        size_bytes=len(content),
        extracted_text=extracted_text,
        status=FileStatus.PARSED,
    )
    db.add(record)
    for chunk_index, (page_number, page_text) in enumerate(pages):
        db.add(DocumentEvidence(
            file_id=file_id,
            user_id=user.id,
            organization_id=user.organization_id,
            source_type="pdf",
            page_number=page_number,
            chunk_index=chunk_index,
            text=page_text,
            location_label=f"第 {page_number} 页",
        ))
    await db.commit()
    await db.refresh(record)
    return ResearchFileResponse.model_validate(record)


@router.get("", response_model=list[ResearchFileResponse])
async def list_files(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResearchFile)
        .where(ResearchFile.user_id == user.id)
        .order_by(desc(ResearchFile.created_at))
    )
    return [ResearchFileResponse.model_validate(item) for item in result.scalars().all()]


@router.get("/{file_id}/evidence", response_model=list[DocumentEvidenceResponse])
async def list_file_evidence(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(ResearchFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="文件不存在")

    result = await db.execute(
        select(DocumentEvidence)
        .where(DocumentEvidence.file_id == file_id)
        .where(DocumentEvidence.user_id == user.id)
        .order_by(DocumentEvidence.chunk_index)
    )
    return [DocumentEvidenceResponse.model_validate(item) for item in result.scalars().all()]


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(ResearchFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="文件不存在")
    safe_name = record.original_name.replace("\r", "").replace("\n", "")
    return Response(
        content=storage.read(record.storage_key),
        media_type=record.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
