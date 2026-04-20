"""AG-029：``adapter.pdf.parse_document`` 解析入口。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.adapter.pdf import PdfParseError, parse_document


def test_parse_document_reads_blank_page_pdf() -> None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as buf:
        path = buf.name
    try:
        w = PdfWriter()
        w.add_blank_page(width=200, height=200)
        with open(path, "wb") as f:
            w.write(f)

        out = parse_document(path)
        assert out["page_count"] == 1
        assert len(out["pages"]) == 1
        assert out["pages"][0]["page_index"] == 0
        assert isinstance(out["pages"][0]["text"], str)
        assert isinstance(out["full_text"], str)
    finally:
        Path(path).unlink(missing_ok=True)


def test_parse_document_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        parse_document("/nonexistent/path/that/does/not/exist.pdf")


def test_parse_document_invalid_bytes_not_pdf() -> None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"not a pdf")
        path = tmp.name
    try:
        with pytest.raises(PdfParseError):
            parse_document(path)
    finally:
        Path(path).unlink(missing_ok=True)
