from __future__ import annotations

from typing import Any

import pytest

from .contract_validate import load_contract


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    return load_contract()
