import io
import uuid
import zipfile
import xml.etree.ElementTree as ET
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import DocumentEvidence, ResearchFile, ResearchSubject, Task, User, FileStatus
from app.schemas import DocumentEvidenceResponse, ResearchFileResponse
from app.services.storage import LocalStorage

router = APIRouter(prefix="/api/files", tags=["files"])
storage = LocalStorage(settings.storage_path)


def _extract_pdf_pages(content: bytes) -> list[tuple[int | None, str]]:
    reader = PdfReader(io.BytesIO(content))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            pages.append((index, page_text))
    return pages


def _format_pages_text(pages: list[tuple[int | None, str]]) -> str:
    blocks = []
    for page_number, text in pages:
        label = f"第 {page_number} 页" if page_number else "文本片段"
        blocks.append(f"【{label}】\n{text}")
    return "\n\n".join(blocks).strip()


def _extract_docx_text(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            xml_content = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("Word 文件结构无效，请上传 .docx 文件") from exc

    root = ET.fromstring(xml_content)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        joined = "".join(texts).strip()
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs).strip()


def _extract_text_chunks(text: str, chunk_size: int = 3000) -> list[tuple[int | None, str]]:
    chunks: list[tuple[int | None, str]] = []
    clean_text = text.strip()
    for start in range(0, len(clean_text), chunk_size):
        chunk = clean_text[start:start + chunk_size].strip()
        if chunk:
            chunks.append((None, chunk))
    return chunks


def _detect_file_type(filename: str, content_type: str | None) -> tuple[str, str]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "pdf", "application/pdf"
    if lower.endswith(".docx"):
        return "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if lower.endswith(".md") or lower.endswith(".markdown"):
        return "md", "text/markdown"
    if content_type in {"text/markdown", "text/plain"} and lower.endswith((".md", ".markdown")):
        return "md", "text/markdown"
    raise HTTPException(status_code=400, detail="当前仅支持 PDF、Word docx 和 Markdown 文件")


@router.post("", response_model=ResearchFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    task_id: str | None = Form(None),
    research_subject_id: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or ""
    file_type, normalized_content_type = _detect_file_type(filename, file.content_type)

    content = await file.read(settings.max_upload_size_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"文件不能超过 {settings.max_upload_size_mb}MB")
    if file_type == "pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="文件内容不是有效的 PDF")

    if task_id:
        task = await db.get(Task, task_id)
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="任务不存在")
    if research_subject_id:
        subject = await db.get(ResearchSubject, research_subject_id)
        if not subject or subject.user_id != user.id:
            raise HTTPException(status_code=404, detail="研究对象不存在")

    try:
        if file_type == "pdf":
            pages = _extract_pdf_pages(content)
        elif file_type == "docx":
            pages = _extract_text_chunks(_extract_docx_text(content))
        else:
            pages = _extract_text_chunks(content.decode("utf-8"))
        extracted_text = _format_pages_text(pages)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {exc}") from exc

    file_id = str(uuid.uuid4())
    storage_key = f"files/{user.id}/{file_id}.{file_type}"
    storage.save(storage_key, content)
    record = ResearchFile(
        id=file_id,
        user_id=user.id,
        organization_id=user.organization_id,
        research_subject_id=research_subject_id,
        task_id=task_id,
        original_name=filename,
        storage_key=storage_key,
        content_type=normalized_content_type,
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
            research_subject_id=research_subject_id,
            source_type=file_type,
            page_number=page_number,
            chunk_index=chunk_index,
            text=page_text,
            location_label=f"第 {page_number} 页" if page_number else f"文本片段 {chunk_index + 1}",
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
    encoded_name = quote(safe_name)
    return Response(
        content=storage.read(record.storage_key),
        media_type=record.content_type,
        headers={"Content-Disposition": f"attachment; filename=file; filename*=UTF-8''{encoded_name}"},
    )
