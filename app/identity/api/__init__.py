"""Identity HTTP API Blueprint（AG-004；``POST /auth/login`` 见 AG-082）。"""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("identity", __name__, url_prefix="/api/v1")

from app.identity.api import routes as _routes  # noqa: F401
