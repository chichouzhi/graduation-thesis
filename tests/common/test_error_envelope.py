"""``app.common.error_envelope`` 与 ``contract.yaml`` 对齐。"""
from __future__ import annotations

import pytest

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from tests.spec.contract_validate import assert_contract_instance, load_contract

pytestmark = pytest.mark.contract


def test_errorcode_matches_contract_yaml_enum() -> None:
    contract = load_contract()
    enum_vals = (
        contract["components"]["schemas"]["ErrorEnvelope"]["properties"]["error"]["properties"]["code"]["enum"]
    )
    assert set(enum_vals) == {e.value for e in ErrorCode}


@pytest.mark.parametrize("code", list(ErrorCode))
def test_error_envelope_to_dict_validates_against_contract(
    contract: dict,
    code: ErrorCode,
) -> None:
    payload = ErrorEnvelope(code=code, message="x").to_dict()
    assert_contract_instance(contract, "ErrorEnvelope", payload, expect_valid=True, error_substrings=())


def test_error_envelope_with_details() -> None:
    contract = load_contract()
    payload = ErrorEnvelope(
        code=ErrorCode.VALIDATION_ERROR,
        message="bad",
        details={"field": "name"},
    ).to_dict()
    assert_contract_instance(contract, "ErrorEnvelope", payload, expect_valid=True, error_substrings=())


def test_invalid_error_code_rejected() -> None:
    with pytest.raises(ValueError):
        ErrorCode("NO_SUCH_CODE")
