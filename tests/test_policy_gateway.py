"""AG-006：PolicyGateway 门面签名与 extensions 依赖注入点。"""
from __future__ import annotations

import pytest

from app.common.policy import CONTRACT_QUEUE_NAMES, PolicyDenied, PolicyGateway
from app.common.error_envelope import ErrorCode


def test_contract_queue_names_match_known_contract_keys() -> None:
    assert CONTRACT_QUEUE_NAMES == frozenset(
        ("chat_jobs", "pdf_parse", "document_jobs", "keyword_jobs", "reconcile_jobs")
    )


def test_assert_can_enqueue_default_allows_contract_queue() -> None:
    PolicyGateway.assert_can_enqueue(queue="reconcile_jobs", application_id="a1")


def test_assert_can_enqueue_rejects_unknown_queue_name() -> None:
    with pytest.raises(ValueError, match="contract.yaml"):
        PolicyGateway.assert_can_enqueue(queue="unknown_queue")


def test_policy_denied_carries_error_code() -> None:
    err = PolicyDenied("depth", code=ErrorCode.QUEUE_UNAVAILABLE)
    assert err.code is ErrorCode.QUEUE_UNAVAILABLE
    assert err.message == "depth"


def test_create_app_registers_policy_gateway() -> None:
    from app import create_app
    from app.extensions import get_policy_gateway

    app = create_app()
    with app.app_context():
        assert app.extensions.get("policy_gateway") is PolicyGateway
        assert get_policy_gateway() is PolicyGateway


def test_get_policy_gateway_without_app_context_falls_back() -> None:
    from app.extensions import get_policy_gateway

    assert get_policy_gateway() is PolicyGateway
