"""
验证「受理侧 service → task.queue」：Chat 或 Document 入队须命中 enqueue spy。

若实现尚未提供 ChatService / DocumentService，本文件在 import 或调用阶段失败。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.arch.spy._import_helpers import import_module_or_fail

CHAT_METHOD_CANDIDATES = ("send_user_message", "post_message", "enqueue_user_turn")
DOC_METHOD_CANDIDATES = ("create_document_task", "enqueue_document_analysis", "submit_pdf_task")


def _stub_service(cls):
    svc = object.__new__(cls)
    svc.db = MagicMock()
    svc.session = MagicMock()
    return svc


def _find_method(cls, candidates):
    for name in candidates:
        fn = getattr(cls, name, None)
        if callable(fn):
            return fn
    pytest.fail(f"{cls.__name__} 缺少候选方法之一: {candidates}")


@patch("app.task.queue.enqueue")
def test_chat_service_calls_queue_on_message(mock_enqueue):
    mod = import_module_or_fail("app.chat.service.chat_service")
    cls = getattr(mod, "ChatService", None)
    if cls is None:
        pytest.fail("app.chat.service.chat_service 须定义 ChatService")
    svc = _stub_service(cls)
    send = _find_method(cls, CHAT_METHOD_CANDIDATES)
    send(
        svc,
        conversation_id="conv-1",
        content="hello",
        user_id="user-1",
    )
    mock_enqueue.assert_called()


@patch("app.task.queue.enqueue")
def test_document_service_calls_queue_on_upload(mock_enqueue):
    mod = import_module_or_fail("app.document.service.document_service")
    cls = getattr(mod, "DocumentService", None)
    if cls is None:
        pytest.fail("app.document.service.document_service 须定义 DocumentService")
    svc = _stub_service(cls)
    create = _find_method(cls, DOC_METHOD_CANDIDATES)
    create(
        svc,
        user_id="user-1",
        term_id="term-1",
        storage_path="/tmp/x.pdf",
        filename="x.pdf",
    )
    mock_enqueue.assert_called()
