"""arch spy 测：未落地 app/ 前整组失败（architecture.spec R-POLICY-SVC / M-CHAIN-WORKER）。"""
from __future__ import annotations

from pathlib import Path

import pytest

# tests/arch/spy/conftest.py → parents[3] == 仓库根
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session", autouse=True)
def _require_nonempty_app_package() -> None:
    app_dir = REPO_ROOT / "app"
    if not app_dir.is_dir():
        pytest.fail(
            "tests/arch/spy：仓库根须存在 app/ 目录；未初始化应用包前本组测试预期失败。"
        )
    # 仅有空目录不算已落地；至少要有可 import 的包结构
    init_py = app_dir / "__init__.py"
    if not init_py.is_file():
        pytest.fail(
            "tests/arch/spy：app/__init__.py 缺失；请先创建 Python 包 app 后再跑本组测试。"
        )
