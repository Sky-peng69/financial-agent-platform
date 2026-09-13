import html
import json
import re
import textwrap
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO

from app.core.config import settings
from app.models import ResearchReport, User
from app.services.storage import LocalStorage

storage = LocalStorage(settings.storage_path)

REPORT_FORMATS = {"md", "docx", "pdf"}
REPORT_STYLES: dict[str, dict[str, str]] = {
    "institutional": {
        "label": "机构投研深度版",
        "instruction": (
            "生成面向证券公司和基金公司投研人员的机构投研深度报告。"
            "结构应包含核心结论、公司概况、行业与竞争格局、基本面分析、估值讨论、风险提示、待核验事项和来源说明。"
            "语言专业、结论先行，关键数字必须标注来源或待核验。"
        ),
    },
    "executive": {
        "label": "管理层摘要版",
        "instruction": (
            "生成面向管理层或评委快速阅读的摘要型报告。"
            "压缩篇幅，优先呈现核心判断、关键依据、主要风险、下一步建议。"
            "避免冗长展开，所有不确定信息必须标注待核验。"
        ),
    },
    "risk_review": {
        "label": "风险审查版",
        "instruction": (
            "生成面向金融风控和合规审查的研究报告。"
            "重点呈现来源可靠性、关键数字可追溯性、反方挑战、风险等级、证据缺口和人工复核事项。"
            "不得输出个性化买卖建议。"
        ),
    },
}


def normalize_formats(formats: list[str] | None) -> list[str]:
    selected = []
    for item in formats or ["docx", "md", "pdf"]:
        value = item.lower().strip()
        if value in REPORT_FORMATS and value not in selected:
            selected.append(value)
    return selected or ["docx", "md", "pdf"]


def normalize_report_style(style: str | None) -> str:
    value = (style or "institutional").strip()
    return value if value in REPORT_STYLES else "institutional"


def build_report_prompt(
    *,
    title: str,
    user_input: str,
    report_style: str,
) -> str:
    style = REPORT_STYLES[normalize_report_style(report_style)]
    return f"""请生成一份可导出的正式金融研究报告。

报告标题：{title}
用户需求：{user_input}
报告风格：{style["label"]}
风格要求：{style["instruction"]}

硬性要求：
1. 必须使用 Markdown 输出，便于后续导出 Word、PDF 和 Markdown 文件。
2. 必须包含“AI 生成草稿”“生成时间”“风险提示”“来源说明”“待核验事项”。
3. 关键财务数字、估值、市值、股价、利润、收入、现金流等不得凭空生成；来源不充分时写“待核验”。
4. 优先引用交易所公告、公司定期报告、公司官网、监管披露和权威金融信息源。
5. 不得输出面向个人投资者的个性化买卖指令。
"""


def report_response(report: ResearchReport) -> dict:
    files = json.loads(report.file_manifest)
    return {
        "id": report.id,
        "research_subject_id": report.research_subject_id,
        "task_id": report.task_id,
        "title": report.title,
        "report_style": report.report_style,
        "review_status": report.review_status,
        "created_at": report.created_at.isoformat(),
        "files": [
            {
                "format": item["format"],
                "filename": item["filename"],
                "download_url": f"/api/reports/{report.id}/download/{item['format']}",
            }
            for item in files
        ],
    }


def create_report_record(
    *,
    user: User,
    title: str,
    markdown: str,
    report_style: str,
    formats: list[str],
    task_id: str | None = None,
    research_subject_id: str | None = None,
) -> ResearchReport:
    report_id = str(uuid.uuid4())
    safe_title = _safe_filename(title)
    selected_formats = normalize_formats(formats)
    style = normalize_report_style(report_style)
    manifest = []

    for fmt in selected_formats:
        filename = f"{safe_title}.{fmt}"
        storage_key = f"reports/{user.id}/{report_id}/{filename}"
        content, content_type = _render_report_file(markdown, fmt)
        storage.save(storage_key, content)
        manifest.append({
            "format": fmt,
            "filename": filename,
            "storage_key": storage_key,
            "content_type": content_type,
        })

    return ResearchReport(
        id=report_id,
        user_id=user.id,
        organization_id=user.organization_id,
        research_subject_id=research_subject_id,
        task_id=task_id,
        title=title,
        report_style=style,
        content_markdown=markdown,
        file_manifest=json.dumps(manifest, ensure_ascii=False),
        review_status="ai_draft",
    )


def file_from_manifest(report: ResearchReport, fmt: str) -> tuple[bytes, str, str]:
    target_format = fmt.lower().strip()
    for item in json.loads(report.file_manifest):
        if item["format"] == target_format:
            return (
                storage.read(item["storage_key"]),
                item["content_type"],
                item["filename"],
            )
    raise KeyError(target_format)


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\r\n]+", "-", value).strip(" .-")
    return cleaned[:80] or "弈金研究报告"


def _render_report_file(markdown: str, fmt: str) -> tuple[bytes, str]:
    if fmt == "md":
        return markdown.encode("utf-8"), "text/markdown; charset=utf-8"
    if fmt == "docx":
        return _markdown_to_docx(markdown), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if fmt == "pdf":
        return _markdown_to_pdf(markdown), "application/pdf"
    raise ValueError(f"不支持的报告格式: {fmt}")


def _markdown_lines(markdown: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            lines.append(("p", ""))
            continue
        if line.startswith("# "):
            lines.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            lines.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            lines.append(("h3", line[4:].strip()))
        elif line.startswith(("- ", "* ")):
            lines.append(("bullet", line[2:].strip()))
        elif line.startswith(">"):
            lines.append(("quote", line.lstrip("> ").strip()))
        elif re.match(r"^\|.*\|$", line):
            lines.append(("table", line))
        else:
            lines.append(("p", line))
    return lines


def _markdown_to_docx(markdown: str) -> bytes:
    body = []
    for kind, text in _markdown_lines(markdown):
        escaped = html.escape(_strip_markdown_marks(text))
        if not escaped:
            body.append('<w:p/>')
            continue
        if kind == "h1":
            body.append(_docx_paragraph(escaped, style="Title"))
        elif kind == "h2":
            body.append(_docx_paragraph(escaped, style="Heading1"))
        elif kind == "h3":
            body.append(_docx_paragraph(escaped, style="Heading2"))
        elif kind == "bullet":
            body.append(_docx_paragraph(f"• {escaped}"))
        elif kind == "table":
            body.append(_docx_paragraph(escaped))
        else:
            body.append(_docx_paragraph(escaped))

    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {''.join(body)}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>'''

    styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:eastAsia="Microsoft YaHei"/><w:sz w:val="22"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="34"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
</w:styles>'''

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>''')
        docx.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
        docx.writestr("word/_rels/document.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''')
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles_xml)
    return buffer.getvalue()


def _docx_paragraph(text: str, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{style_xml}<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def _strip_markdown_marks(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text


def _markdown_to_plain_text(markdown: str) -> str:
    text_lines = []
    for kind, text in _markdown_lines(markdown):
        if kind == "table":
            text = text.replace("|", "  ")
        prefix = "" if kind != "bullet" else "• "
        text_lines.append(prefix + _strip_markdown_marks(text))
    return "\n".join(text_lines)


def _wrap_pdf_text(text: str, width: int = 42) -> list[str]:
    wrapped: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(line, width=width, break_long_words=False) or [line])
    return wrapped


def _markdown_to_pdf(markdown: str) -> bytes:
    lines = _wrap_pdf_text(_markdown_to_plain_text(markdown))
    pages: list[list[str]] = []
    for index in range(0, len(lines), 42):
        pages.append(lines[index:index + 42])
    if not pages:
        pages = [["弈金研究报告", "", "无内容"]]

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"))

    for page_index, page_lines in enumerate(pages):
        page_obj = 3 + page_index * 2
        content_obj = page_obj + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> >>] >> >> >> >> "
            f"/Contents {content_obj} 0 R >>"
        .encode("ascii"))
        stream = _pdf_content_stream(page_lines)
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")

    return _build_pdf(objects)


def _pdf_content_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "50 790 Td", "16 TL"]
    for line in lines:
        safe_line = line[:90]
        commands.append(f"<{safe_line.encode('utf-16-be').hex().upper()}> Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def _build_pdf(objects: list[bytes]) -> bytes:
    output = bytearray(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)
