"""AG-030：``adapter.storage`` 落盘与读取。"""
from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture
def storage_mod(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("DOCUMENT_STORAGE_DIR", str(tmp_path))
    import app.adapter.storage as storage

    return importlib.reload(storage)


def test_put_get_roundtrip(storage_mod: object, tmp_path: Path) -> None:
    put_bytes = storage_mod.put_bytes
    get_bytes = storage_mod.get_bytes
    uri = put_bytes(b"hello-pdf", rel_key="term-1/task-abc/paper.pdf")
    assert Path(uri).is_file()
    assert Path(uri).resolve().is_relative_to(tmp_path.resolve())
    assert get_bytes(uri) == b"hello-pdf"


def test_put_rejects_parent_segments(storage_mod: object) -> None:
    put_bytes = storage_mod.put_bytes
    with pytest.raises(ValueError, match=r"\.\."):
        put_bytes(b"x", rel_key="../etc/passwd")


def test_get_bytes_rejects_outside_root(storage_mod: object, tmp_path: Path) -> None:
    get_bytes = storage_mod.get_bytes
    outside = tmp_path.parent / "outside.bin"
    outside.write_bytes(b"no")
    with pytest.raises(PermissionError, match="escapes"):
        get_bytes(str(outside))
