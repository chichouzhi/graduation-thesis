"""Storage 适配层：文献上传字节落盘与按路径读取。

真源：``DocumentTask.storage_path`` 与队列载荷 ``PdfJobPayload.storage_path``；
返回值为 **绝对路径字符串**，供 ``adapter.pdf.parse_document`` 等本地打开。

根目录：环境变量 ``DOCUMENT_STORAGE_DIR``；未设置时使用仓库根下 ``instance/documents``。
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ("put_bytes", "get_bytes")


def _repo_root() -> Path:
    # app/adapter/storage/__init__.py -> parents[3] == 仓库根
    return Path(__file__).resolve().parents[3]


def _storage_root() -> Path:
    raw = os.environ.get("DOCUMENT_STORAGE_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (_repo_root() / "instance" / "documents").resolve()


def _normalize_rel_key(rel_key: str) -> str:
    key = rel_key.strip().replace("\\", "/")
    if not key or key.startswith("/"):
        raise ValueError("rel_key must be a non-empty relative path")
    parts: list[str] = []
    for p in key.split("/"):
        p = p.strip()
        if not p:
            continue
        if p == "..":
            raise ValueError("rel_key must not contain '..'")
        if p == ".":
            continue
        parts.append(p)
    if not parts:
        raise ValueError("rel_key has no path components")
    return "/".join(parts)


def _assert_under_root(resolved: Path, root: Path) -> None:
    try:
        resolved.relative_to(root)
    except ValueError as e:
        raise PermissionError("storage path escapes DOCUMENT_STORAGE_DIR") from e


def put_bytes(data: bytes, *, rel_key: str) -> str:
    """将字节写入存储根下的相对路径，返回 **绝对** ``storage_path`` 字符串。

    :param data: 上传文件内容（如 PDF 字节）。
    :param rel_key: 根下相对路径，使用 ``/`` 分隔；禁止 ``..`` 与绝对路径。
    """
    rel_norm = _normalize_rel_key(rel_key)
    root = _storage_root()
    dest = (root / rel_norm).resolve()
    _assert_under_root(dest, root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return str(dest)


def get_bytes(storage_path: str) -> bytes:
    """按 ``put_bytes`` 返回的绝对路径读取字节；禁止读取根目录之外的路径。"""
    root = _storage_root()
    candidate = Path(storage_path).expanduser()
    resolved = candidate.resolve()
    _assert_under_root(resolved, root)
    return resolved.read_bytes()
