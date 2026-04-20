"""PDF 解析适配层：文档级入口，供 ``use_cases`` / worker 编排经 UC 调用。

真源：``PdfJobPayload.storage_path`` 落盘后由本模块读取；``app.task`` 不得直连本包
（见 ``spec/architecture.spec.md`` R-UC-SKIP）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

__all__ = ("PdfParseError", "parse_document")


class PdfParseError(Exception):
    """无法打开、解密或逐页抽取文本时抛出（由编排层映射为任务失败语义）。"""


def parse_document(
    path: str | os.PathLike[str],
    *,
    password: str | None = None,
) -> dict[str, Any]:
    """从本地路径读取 PDF，按页抽取纯文本，返回可 JSON 序列化的结构。

    :param path: 存储层提供的绝对或相对路径（与契约 ``storage_path`` 一致）。
    :param password: 加密 PDF 的密码；未加密则保持 ``None``。
    :returns: ``page_count``、``pages``（``page_index`` + ``text``）、``full_text``（页间 ``\\n\\n`` 拼接）。
    """
    resolved = Path(path)
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))

    try:
        reader = PdfReader(str(resolved), strict=False, password=password)
    except PdfReadError as e:
        raise PdfParseError(str(e)) from e
    except Exception as e:  # pragma: no cover - 防御性；pypdf 版本差异
        raise PdfParseError(str(e)) from e

    pages_out: list[dict[str, Any]] = []
    chunk_texts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
        except Exception as e:
            raise PdfParseError(f"extract_text failed at page_index={i}: {e}") from e
        normalized = text if text else ""
        pages_out.append({"page_index": i, "text": normalized})
        chunk_texts.append(normalized)

    full = "\n\n".join(chunk_texts)
    return {
        "page_count": len(reader.pages),
        "pages": pages_out,
        "full_text": full,
    }
