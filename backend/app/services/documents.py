"""Text extraction for uploaded documents.

Supports PDF, DOCX, XLSX, CSV, JSON, Markdown and plain text. Everything is
extracted server-side so the browser only ever handles the raw upload.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xlsm",
    ".csv",
    ".txt",
    ".md",
    ".json",
    ".log",
    ".yaml",
    ".yml",
}

MAX_EXTRACT_CHARS = 120_000


@dataclass
class Extracted:
    text: str
    pages: int | None = None
    truncated: bool = False


class UnsupportedDocument(ValueError):
    """Raised when the file type cannot be read."""


def extract(path: Path, content_type: str | None = None) -> Extracted:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocument(
            f"Unsupported file type '{suffix or 'unknown'}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix in {".xlsx", ".xlsm"}:
        return _extract_xlsx(path)
    if suffix == ".csv":
        return _extract_csv(path)
    if suffix == ".json":
        return _extract_json(path)
    return _extract_plain(path)


def _clip(text: str) -> tuple[str, bool]:
    text = text.strip()
    if len(text) > MAX_EXTRACT_CHARS:
        return text[:MAX_EXTRACT_CHARS], True
    return text, False


def _extract_pdf(path: Path) -> Extracted:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:  # pragma: no cover - damaged page
            page_text = ""
        if page_text.strip():
            chunks.append(f"[page {index}]\n{page_text.strip()}")
    text, truncated = _clip("\n\n".join(chunks))
    return Extracted(text=text, pages=len(reader.pages), truncated=truncated)


def _extract_docx(path: Path) -> Extracted:
    import docx

    document = docx.Document(str(path))
    parts: list[str] = [p.text for p in document.paragraphs if p.text.strip()]
    for table_index, table in enumerate(document.tables, start=1):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(" | ".join(cells))
        if rows:
            parts.append(f"[table {table_index}]\n" + "\n".join(rows))
    text, truncated = _clip("\n".join(parts))
    return Extracted(text=text, truncated=truncated)


def _extract_xlsx(path: Path) -> Extracted:
    import openpyxl

    workbook = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    parts: list[str] = []
    for sheet in workbook.worksheets:
        parts.append(f"[sheet: {sheet.title}]")
        for row_index, row in enumerate(sheet.iter_rows(values_only=True)):
            if row_index >= 500:  # keep prompt size sane
                parts.append("... (sheet truncated at 500 rows)")
                break
            cells = ["" if v is None else str(v) for v in row]
            if any(c.strip() for c in cells):
                parts.append(" | ".join(cells))
    workbook.close()
    text, truncated = _clip("\n".join(parts))
    return Extracted(text=text, truncated=truncated)


def _extract_csv(path: Path) -> Extracted:
    raw = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.reader(io.StringIO(raw))
    rows: list[str] = []
    for index, row in enumerate(reader):
        if index >= 2000:
            rows.append("... (csv truncated at 2000 rows)")
            break
        rows.append(" | ".join(row))
    text, truncated = _clip("\n".join(rows))
    return Extracted(text=text, truncated=truncated)


def _extract_json(path: Path) -> Extracted:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        pretty = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        pretty = raw
    text, truncated = _clip(pretty)
    return Extracted(text=text, truncated=truncated)


def _extract_plain(path: Path) -> Extracted:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text, truncated = _clip(raw)
    return Extracted(text=text, truncated=truncated)


def excerpt(text: str, limit: int = 280) -> str:
    flat = " ".join(text.split())
    return flat[:limit] + ("…" if len(flat) > limit else "")
