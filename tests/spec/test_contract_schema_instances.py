"""基于 contract.yaml 的 JSON 契约测试。

1. 参数化用例：手写实例 + ``assert_contract_instance``（失败分支带 ``error_substrings``）。
2. ``TestImplementationOutputsMatchContract``：真实 ``app`` 路径 + 同一套校验。
"""
from __future__ import annotations

from typing import Any

import pytest

from .contract_validate import assert_contract_instance, schema_by_name, validate_instance

pytestmark = pytest.mark.contract

_OMIT_STATUS = object()


def _valid_message(
    *,
    msg_id: str,
    conversation_id: str,
    role: str,
    content: str,
    status: str | None | object = _OMIT_STATUS,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": msg_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "created_at": "2026-01-02T03:04:05Z",
    }
    if status is not _OMIT_STATUS:
        base["status"] = status
    return base


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            "PostUserMessageRequest",
            {"content": "ok", "client_request_id": None, "seq": 0},
            True,
            (),
            id="post_msg_ok_with_null_optionals_and_seq_zero",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": "a" * 8000},
            True,
            (),
            id="post_msg_ok_long_content",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {},
            False,
            ("missing required property 'content'",),
            id="post_msg_missing_content",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": ""},
            False,
            ("minLength",),
            id="post_msg_empty_content",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": None},
            False,
            ("$.content", "null"),
            id="post_msg_null_content",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": 42},
            False,
            ("$.content", "string"),
            id="post_msg_content_wrong_type",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": "ok", "seq": 1.5},
            False,
            ("$.seq", "integer"),
            id="post_msg_seq_float",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": "ok", "seq": "1"},
            False,
            ("$.seq", "integer"),
            id="post_msg_seq_string",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": "ok", "seq": -1},
            True,
            (),
            id="post_msg_seq_negative_allowed_by_contract",
        ),
        pytest.param(
            "PostUserMessageRequest",
            {"content": "ok", "client_request_id": ["x"]},
            False,
            ("$.client_request_id", "string"),
            id="post_msg_client_request_id_wrong_type",
        ),
    ],
)
def test_post_user_message_request_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param("CreateConversationRequest", {"term_id": "term-1"}, True, (), id="conv_ok"),
        pytest.param(
            "CreateConversationRequest",
            {"term_id": "term-1", "title": "", "context_ref_id": None},
            True,
            (),
            id="conv_ok_empty_title",
        ),
        pytest.param(
            "CreateConversationRequest",
            {"term_id": ""},
            True,
            (),
            id="conv_empty_term_id_allowed_if_no_minlength",
        ),
        pytest.param(
            "CreateConversationRequest",
            {},
            False,
            ("missing required property 'term_id'",),
            id="conv_missing_term_id",
        ),
        pytest.param(
            "CreateConversationRequest",
            {"term_id": None},
            False,
            ("$.term_id", "null"),
            id="conv_null_term_id",
        ),
        pytest.param(
            "CreateConversationRequest",
            {"term_id": "t", "context_type": "general"},
            True,
            (),
            id="conv_ok_context_type",
        ),
        pytest.param(
            "CreateConversationRequest",
            {"term_id": "t", "context_type": "invalid"},
            False,
            ("enum violation",),
            id="conv_bad_context_type",
        ),
    ],
)
def test_create_conversation_request_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param("TopicReviewRequest", {"action": "approve"}, True, (), id="topic_review_ok"),
        pytest.param(
            "TopicReviewRequest",
            {"action": "reject", "comment": ""},
            True,
            (),
            id="topic_review_reject",
        ),
        pytest.param(
            "TopicReviewRequest",
            {},
            False,
            ("missing required property 'action'",),
            id="topic_review_missing_action",
        ),
        pytest.param(
            "TopicReviewRequest",
            {"action": None},
            False,
            ("$.action", "null"),
            id="topic_review_null_action",
        ),
        pytest.param(
            "TopicReviewRequest",
            {"action": "hold"},
            False,
            ("enum violation",),
            id="topic_review_illegal_action",
        ),
    ],
)
def test_topic_review_request_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1", "priority": 1},
            True,
            (),
            id="app_ok_p1",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1", "priority": 2},
            True,
            (),
            id="app_ok_p2",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1", "priority": 0},
            False,
            ("enum violation",),
            id="app_priority_zero",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1", "priority": 3},
            False,
            ("enum violation",),
            id="app_priority_three",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1"},
            False,
            ("missing required property 'priority'",),
            id="app_missing_priority",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"term_id": "tm-1", "priority": 1},
            False,
            ("missing required property 'topic_id'",),
            id="app_missing_topic_id",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "priority": 1},
            False,
            ("missing required property 'term_id'",),
            id="app_missing_term_id",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1", "priority": True},
            False,
            ("$.priority", "integer"),
            id="app_priority_bool",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1", "priority": 1.0},
            False,
            ("$.priority", "integer"),
            id="app_priority_float",
        ),
        pytest.param(
            "CreateApplicationRequest",
            {"topic_id": "tp-1", "term_id": "tm-1", "priority": None},
            False,
            ("$.priority", "null"),
            id="app_null_priority",
        ),
    ],
)
def test_create_application_request_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            "CreateTopicRequest",
            {
                "title": "课题",
                "summary": "摘要",
                "requirements": "要求",
                "capacity": 1,
                "term_id": "term-1",
            },
            True,
            (),
            id="topic_create_ok_min_capacity",
        ),
        pytest.param(
            "CreateTopicRequest",
            {
                "title": "课题",
                "summary": "摘要",
                "requirements": "要求",
                "capacity": 0,
                "term_id": "term-1",
            },
            False,
            ("< minimum",),
            id="topic_create_capacity_zero",
        ),
        pytest.param(
            "CreateTopicRequest",
            {
                "summary": "摘要",
                "requirements": "要求",
                "capacity": 1,
                "term_id": "term-1",
            },
            False,
            ("missing required property 'title'",),
            id="topic_create_missing_title",
        ),
        pytest.param(
            "CreateTopicRequest",
            {
                "title": "课题",
                "summary": "摘要",
                "requirements": "要求",
                "capacity": 1,
            },
            False,
            ("missing required property 'term_id'",),
            id="topic_create_missing_term_id",
        ),
    ],
)
def test_create_topic_request_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            "ErrorEnvelope",
            {"error": {"code": "VALIDATION_ERROR", "message": "bad"}},
            True,
            (),
            id="err_ok",
        ),
        pytest.param(
            "ErrorEnvelope",
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "missing",
                    "details": {"path": "/x"},
                },
            },
            True,
            (),
            id="err_ok_details",
        ),
        pytest.param(
            "ErrorEnvelope",
            {},
            False,
            ("missing required property 'error'",),
            id="err_missing_error",
        ),
        pytest.param(
            "ErrorEnvelope",
            {"error": "x"},
            False,
            ("$.error", "object"),
            id="err_error_not_object",
        ),
        pytest.param(
            "ErrorEnvelope",
            {"error": {"message": "only"}},
            False,
            ("missing required property 'code'",),
            id="err_missing_code",
        ),
        pytest.param(
            "ErrorEnvelope",
            {"error": {"code": "NOT_FOUND"}},
            False,
            ("missing required property 'message'",),
            id="err_missing_message",
        ),
        pytest.param(
            "ErrorEnvelope",
            {"error": {"code": "NOT_FOUND", "message": None}},
            False,
            ("$.error.message", "null"),
            id="err_null_message",
        ),
        pytest.param(
            "ErrorEnvelope",
            {"error": {"code": "NO_SUCH_CODE", "message": "x"}},
            False,
            ("enum violation",),
            id="err_bad_code_enum",
        ),
        pytest.param(
            "ErrorEnvelope",
            {"error": {"code": None, "message": "x"}},
            False,
            ("$.error.code", "null"),
            id="err_null_code",
        ),
    ],
)
def test_error_envelope_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            _valid_message(msg_id="m0", conversation_id="c1", role="user", content="hi"),
            True,
            (),
            id="msg_user_omit_status",
        ),
        pytest.param(
            _valid_message(
                msg_id="m1",
                conversation_id="c1",
                role="user",
                content="hi",
                status=None,
            ),
            True,
            (),
            id="msg_user_null_status",
        ),
        pytest.param(
            _valid_message(
                msg_id="m2",
                conversation_id="c1",
                role="assistant",
                content="",
                status="pending",
            ),
            True,
            (),
            id="msg_assistant_pending",
        ),
        pytest.param(
            _valid_message(
                msg_id="m2b",
                conversation_id="c1",
                role="assistant",
                content="x",
            ),
            True,
            (),
            id="msg_assistant_omit_status_schema_allows",
        ),
        pytest.param(
            _valid_message(
                msg_id="m3",
                conversation_id="c1",
                role="assistant",
                content="",
                status="bogus",
            ),
            False,
            ("enum violation",),
            id="msg_assistant_bad_status",
        ),
        pytest.param(
            {
                "id": "m4",
                "conversation_id": "c1",
                "role": "system",
                "content": "sys",
                "created_at": "2026-01-02T03:04:05Z",
            },
            True,
            (),
            id="msg_system_role",
        ),
        pytest.param(
            {
                "id": "m5",
                "conversation_id": "c1",
                "role": "wizard",
                "content": "x",
                "created_at": "2026-01-02T03:04:05Z",
            },
            False,
            ("enum violation",),
            id="msg_bad_role",
        ),
        pytest.param(
            {
                "id": "m6",
                "conversation_id": "c1",
                "role": "user",
                "content": "x",
                "created_at": "not-a-datetime",
            },
            False,
            ("ISO-8601",),
            id="msg_bad_datetime",
        ),
        pytest.param(
            {
                "id": "m7",
                "conversation_id": "c1",
                "role": "user",
                "content": 1,
                "created_at": "2026-01-02T03:04:05Z",
            },
            False,
            ("$.content", "string"),
            id="msg_content_wrong_type",
        ),
    ],
)
def test_message_schema_contract(
    contract: dict[str, Any],
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        "Message",
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            "ChatJobPayload",
            {
                "job_id": "job-1",
                "conversation_id": "conv-1",
                "user_message_id": "um-1",
                "assistant_message_id": "am-1",
                "term_id": "term-1",
                "user_id": "user-1",
                "content": "hello",
            },
            True,
            (),
            id="chat_job_ok",
        ),
        pytest.param(
            "ChatJobPayload",
            {
                "job_id": "job-1",
                "conversation_id": "conv-1",
                "user_message_id": "um-1",
                "assistant_message_id": "am-1",
                "term_id": "term-1",
                "user_id": "user-1",
                "content": "hello",
                "dispatch_attempt": 0,
            },
            True,
            (),
            id="chat_job_dispatch_zero",
        ),
        pytest.param(
            "ChatJobPayload",
            {
                "job_id": "job-1",
                "conversation_id": "conv-1",
                "user_message_id": "um-1",
                "assistant_message_id": "am-1",
                "term_id": "term-1",
                "user_id": "user-1",
                "content": "hello",
                "dispatch_attempt": -1,
            },
            False,
            ("< minimum",),
            id="chat_job_dispatch_negative",
        ),
        pytest.param(
            "ChatJobPayload",
            {
                "conversation_id": "conv-1",
                "user_message_id": "um-1",
                "assistant_message_id": "am-1",
                "term_id": "term-1",
                "user_id": "user-1",
            },
            False,
            ("missing required property 'job_id'",),
            id="chat_job_missing_job_id",
        ),
        pytest.param(
            "ChatJobPayload",
            {
                "job_id": "job-1",
                "conversation_id": "conv-1",
                "user_message_id": "um-1",
                "assistant_message_id": "am-1",
                "term_id": "term-1",
                "user_id": "user-1",
            },
            False,
            ("missing required property 'content'",),
            id="chat_job_missing_content",
        ),
        pytest.param(
            "ChatJobPayload",
            {
                "job_id": "job-1",
                "conversation_id": "conv-1",
                "user_message_id": "um-1",
                "assistant_message_id": "am-1",
                "term_id": "term-1",
                "user_id": "user-1",
                "content": "",
            },
            False,
            ("minLength",),
            id="chat_job_empty_content",
        ),
    ],
)
def test_chat_job_payload_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            "PdfJobPayload",
            {
                "document_task_id": "dt-1",
                "user_id": "u1",
                "storage_path": "/data/x.pdf",
                "term_id": "t1",
            },
            True,
            (),
            id="pdf_job_ok",
        ),
        pytest.param(
            "PdfJobPayload",
            {
                "document_task_id": "dt-1",
                "user_id": "u1",
                "storage_path": "/data/x.pdf",
                "term_id": "t1",
                "stage": "full_parse",
            },
            False,
            ("enum violation",),
            id="pdf_job_bad_stage",
        ),
        pytest.param(
            "PdfJobPayload",
            {"user_id": "u1", "storage_path": "/data/x.pdf", "term_id": "t1"},
            False,
            ("missing required property 'document_task_id'",),
            id="pdf_job_missing_document_task_id",
        ),
    ],
)
def test_pdf_job_payload_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("schema_name", "instance", "expect_valid", "error_substrings"),
    [
        pytest.param(
            "KeywordJobPayload",
            {
                "keyword_job_id": "kj-1",
                "topic_id": "tp-1",
                "term_id": "tm-1",
                "text_snapshot": "snap",
                "requested_by_user_id": "u1",
            },
            True,
            (),
            id="keyword_job_ok",
        ),
        pytest.param(
            "KeywordJobPayload",
            {
                "topic_id": "tp-1",
                "term_id": "tm-1",
                "text_snapshot": "snap",
                "requested_by_user_id": "u1",
            },
            False,
            ("missing required property 'keyword_job_id'",),
            id="keyword_job_missing_id",
        ),
        pytest.param(
            "ReconcileJobPayload",
            {"reconcile_job_id": "rj-1", "scope": "full_table", "term_id": None},
            True,
            (),
            id="reconcile_ok_full",
        ),
        pytest.param(
            "ReconcileJobPayload",
            {"reconcile_job_id": "rj-2", "scope": "by_term", "term_id": "term-9"},
            True,
            (),
            id="reconcile_ok_by_term",
        ),
        pytest.param(
            "ReconcileJobPayload",
            {"reconcile_job_id": "", "scope": "full_table"},
            True,
            (),
            id="reconcile_empty_id_allowed_if_no_minlength",
        ),
        pytest.param(
            "ReconcileJobPayload",
            {"scope": "full_table"},
            False,
            ("missing required property 'reconcile_job_id'",),
            id="reconcile_missing_id",
        ),
        pytest.param(
            "ReconcileJobPayload",
            {"reconcile_job_id": "rj-4", "scope": "slice"},
            False,
            ("enum violation",),
            id="reconcile_bad_scope",
        ),
    ],
)
def test_queue_payload_schemas_contract(
    contract: dict[str, Any],
    schema_name: str,
    instance: dict[str, Any],
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        schema_name,
        instance,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("raw", "expect_valid", "error_substrings"),
    [
        pytest.param("pending", True, (), id="async_pending"),
        pytest.param("running", True, (), id="async_running"),
        pytest.param("done", True, (), id="async_done"),
        pytest.param("failed", True, (), id="async_failed"),
        pytest.param("queued", False, ("enum violation",), id="async_bad_literal"),
        pytest.param("PENDING", False, ("enum violation",), id="async_wrong_case"),
        pytest.param("", False, ("enum violation",), id="async_empty"),
    ],
)
def test_async_task_status_enum_contract(
    contract: dict[str, Any],
    raw: str,
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        "AsyncTaskStatus",
        raw,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    ("app_status", "expect_valid", "error_substrings"),
    [
        pytest.param("pending", True, (), id="flow_pending"),
        pytest.param("withdrawn", True, (), id="flow_withdrawn"),
        pytest.param("accepted", True, (), id="flow_accepted"),
        pytest.param("rejected", True, (), id="flow_rejected"),
        pytest.param("superseded", True, (), id="flow_superseded"),
        pytest.param("completed", False, ("enum violation",), id="flow_completed_not_in_contract"),
    ],
)
def test_application_flow_status_enum_contract(
    contract: dict[str, Any],
    app_status: str,
    expect_valid: bool,
    error_substrings: tuple[str, ...],
) -> None:
    assert_contract_instance(
        contract,
        "ApplicationFlowStatus",
        app_status,
        expect_valid=expect_valid,
        error_substrings=error_substrings,
    )


@pytest.mark.parametrize(
    "queue_key",
    [
        pytest.param("chat_jobs", id="q_chat"),
        pytest.param("document_jobs", id="q_document"),
        pytest.param("pdf_parse", id="q_pdf"),
        pytest.param("keyword_jobs", id="q_keyword"),
        pytest.param("reconcile_jobs", id="q_reconcile"),
    ],
)
def test_x_task_contracts_queue_payload_schema_refs_resolve_and_reject_empty_payload(
    contract: dict[str, Any],
    queue_key: str,
) -> None:
    queues = contract["x-task-contracts"]["queues"]
    entry = queues[queue_key]
    ref = entry["payload_schema"]
    assert isinstance(ref, str) and ref.startswith("#/components/schemas/")
    name = ref.rsplit("/", 1)[-1]
    schema = schema_by_name(contract, name)
    assert schema.get("type") == "object", f"{name} must be an object schema"
    assert schema.get("required"), f"{name} must declare required fields"
    errs = validate_instance({}, schema, contract)
    assert errs, f"empty object must fail {name}, got no errors"
    assert any("missing required property" in e for e in errs), (
        f"{name}: expected missing-field errors, got: {errs}"
    )


def test_async_task_status_enum_matches_state_machine_states(contract: dict[str, Any]) -> None:
    schema_enum = list(schema_by_name(contract, "AsyncTaskStatus")["enum"])
    machine_states = contract["x-task-contracts"]["state_machines"]["llm_and_document_worker_tasks"][
        "states"
    ]
    assert len(set(schema_enum)) == 4
    assert set(schema_enum) == set(machine_states), (
        "AsyncTaskStatus enum must equal state_machines.llm_and_document_worker_tasks.states"
    )
    assert schema_enum == machine_states, (
        "AsyncTaskStatus enum order should match state_machines.states declaration order"
    )


class TestImplementationOutputsMatchContract:
    """骨架/实现产出的 JSON 须满足 contract；未完成对齐前本组用例应为红色。"""

    def test_create_chat_return_matches_post_user_message_response(
        self,
        contract: dict[str, Any],
    ) -> None:
        from app.chat.service.chat_service import create_chat

        body = create_chat(
            conversation_id="conv-contract-impl-1",
            term_id="term-contract-impl-1",
            user_id="user-contract-impl-1",
            content="hello-contract-impl",
        )
        assert isinstance(body, dict), "create_chat must return a dict (HTTP 202 JSON body)"
        errors = validate_instance(
            body,
            schema_by_name(contract, "PostUserMessageResponse"),
            contract,
        )
        assert errors == [], (
            "create_chat body must satisfy PostUserMessageResponse (including Message required fields); "
            f"errors: {errors}"
        )

    def test_create_chat_enqueue_payload_matches_chat_job_payload(
        self,
        contract: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}

        def capture_enqueue_chat_jobs(
            payload: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> dict[str, str]:
            captured["queue_name"] = "chat_jobs"
            captured["payload"] = payload
            captured["kwargs"] = kwargs
            return {"job_id": "00000000-0000-0000-0000-000000000099"}

        monkeypatch.setattr(
            "app.chat.service.chat_service.queue_mod.enqueue_chat_jobs",
            capture_enqueue_chat_jobs,
            raising=True,
        )
        from app.chat.service.chat_service import create_chat

        create_chat(
            conversation_id="conv-contract-impl-2",
            term_id="term-contract-impl-1",
            user_id="user-contract-impl-1",
            content="enqueue-shape",
        )
        assert captured.get("queue_name") == "chat_jobs", "must enqueue chat_jobs per contract"
        payload = captured.get("payload")
        assert isinstance(payload, dict), "enqueue payload must be a dict"
        errors = validate_instance(
            payload,
            schema_by_name(contract, "ChatJobPayload"),
            contract,
        )
        assert errors == [], f"enqueue payload must satisfy ChatJobPayload; errors: {errors}"

    def test_document_create_task_enqueue_payload_matches_pdf_job_payload(
        self,
        contract: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}

        def capture_enqueue_pdf_parse(
            payload: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> dict[str, str]:
            captured["queue_name"] = "pdf_parse"
            captured["payload"] = payload
            captured["kwargs"] = kwargs
            return {"job_id": "00000000-0000-0000-0000-000000000088"}

        monkeypatch.setattr(
            "app.document.service.document_service.queue_mod.enqueue_pdf_parse",
            capture_enqueue_pdf_parse,
            raising=True,
        )
        from app import create_app
        from app.extensions import db
        from app.identity.model import User, UserRole
        from app.terms.model import Term
        from app.document.service.document_service import DocumentService

        app = create_app()
        with app.app_context():
            db.create_all()
            user = User(username="ct-doc-u1", role=UserRole.student, display_name="u1")
            term = Term(name="ct-doc-term")
            db.session.add_all([user, term])
            db.session.commit()
            DocumentService().create_document_task(
                user_id=user.id,
                term_id=term.id,
                storage_path="/tmp/x.pdf",
                filename="x.pdf",
            )
        assert captured.get("queue_name") == "pdf_parse"
        payload = captured["payload"]
        assert isinstance(payload, dict)
        errors = validate_instance(
            payload,
            schema_by_name(contract, "PdfJobPayload"),
            contract,
        )
        assert errors == [], f"DocumentService enqueue payload must satisfy PdfJobPayload; errors: {errors}"

    def test_document_create_task_202_body_matches_document_task_schema(
        self,
        contract: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "app.document.service.document_service.queue_mod.enqueue_pdf_parse",
            lambda *_a, **_k: {"job_id": "00000000-0000-0000-0000-000000000089"},
            raising=True,
        )
        from app import create_app
        from app.extensions import db
        from app.identity.model import User, UserRole
        from app.terms.model import Term
        from app.document.service.document_service import DocumentService

        app = create_app()
        with app.app_context():
            db.create_all()
            user = User(username="ct-doc-u2", role=UserRole.student, display_name="u2")
            term = Term(name="ct-doc-term-2")
            db.session.add_all([user, term])
            db.session.commit()
            body = DocumentService().create_document_task(
                user_id=user.id,
                term_id=term.id,
                storage_path="/tmp/contract-doc.pdf",
                filename="contract-doc.pdf",
            )
        errors = validate_instance(
            body,
            schema_by_name(contract, "DocumentTask"),
            contract,
        )
        assert errors == [], f"POST /document-tasks 202 DocumentTask body; errors: {errors}"

    def test_topic_get_body_matches_topic_schema(
        self,
        contract: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
            lambda *_a, **_k: {"job_id": "00000000-0000-0000-0000-000000000090"},
            raising=True,
        )
        from app import create_app
        from app.extensions import db
        from app.identity.model import User, UserRole
        from app.terms.model import Term
        from app.topic.service.topic_service import TopicService

        app = create_app()
        with app.app_context():
            db.create_all()
            teacher = User(username="ct-topic-get", role=UserRole.teacher, display_name="t")
            term = Term(name="ct-topic-term")
            db.session.add_all([teacher, term])
            db.session.commit()
            created = TopicService().create_topic_as_teacher(
                teacher.id,
                {
                    "title": "T",
                    "summary": "S",
                    "requirements": "R",
                    "capacity": 3,
                    "term_id": term.id,
                },
            )
            body = TopicService().get_topic(created["id"])
        assert body is not None
        errors = validate_instance(
            body,
            schema_by_name(contract, "Topic"),
            contract,
        )
        assert errors == [], f"GET /topics/{{topic_id}} Topic body; errors: {errors}"

    def test_selection_accept_enqueue_payload_matches_reconcile_job_payload(
        self,
        contract: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}

        def capture_enqueue(
            queue_name: str,
            payload: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> dict[str, str]:
            captured["queue_name"] = queue_name
            captured["payload"] = payload
            captured["kwargs"] = kwargs
            return {"job_id": "00000000-0000-0000-0000-000000000077"}

        monkeypatch.setattr(
            "app.task.queue.enqueue",
            capture_enqueue,
            raising=True,
        )
        from app import create_app
        from app.extensions import db
        from app.identity.model import User, UserRole
        from app.selection.model import Application, ApplicationFlowStatus
        from app.terms.model import Term
        from app.topic.model import Topic, TopicStatus
        from app.selection.service.selection_service import SelectionService

        app = create_app()
        with app.app_context():
            db.create_all()
            student = User(username="ct-sel-stu", role=UserRole.student, display_name="stu")
            teacher = User(username="ct-sel-tea", role=UserRole.teacher, display_name="tea")
            term = Term(name="ct-sel-term")
            db.session.add_all([student, teacher, term])
            db.session.commit()
            topic = Topic(
                title="ct-topic",
                summary="s",
                requirements="r",
                capacity=2,
                selected_count=0,
                teacher_id=teacher.id,
                term_id=term.id,
                status=TopicStatus.published,
            )
            db.session.add(topic)
            db.session.commit()
            app_row = Application(
                student_id=student.id,
                topic_id=topic.id,
                term_id=term.id,
                priority=1,
                status=ApplicationFlowStatus.pending,
            )
            db.session.add(app_row)
            db.session.commit()

            SelectionService().teacher_accept_application(
                application_id=app_row.id,
                action="accept",
                teacher_id=teacher.id,
            )
        assert captured.get("queue_name") == "reconcile_jobs"
        payload = captured["payload"]
        assert isinstance(payload, dict)
        errors = validate_instance(
            payload,
            schema_by_name(contract, "ReconcileJobPayload"),
            contract,
        )
        assert errors == [], (
            "SelectionService teacher_accept enqueue payload must satisfy ReconcileJobPayload; "
            f"errors: {errors}"
        )


def test_contract_openapi_document_validates_when_openapi_spec_validator_installed(
    contract: dict[str, Any],
) -> None:
    try:
        from openapi_spec_validator import validate_spec  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        pytest.skip("openapi-spec-validator not installed")
    validate_spec(contract)
    assert contract["openapi"] == "3.0.3"
    ver = contract["info"]["version"]
    assert isinstance(ver, str) and ver.strip() != ""
    assert contract.get("paths"), "contract must declare paths"
    schemas = contract.get("components", {}).get("schemas", {})
    assert len(schemas) >= 10, "components.schemas should be non-trivial"
