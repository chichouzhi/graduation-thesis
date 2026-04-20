"""Chat HTTP API Blueprint（AG-004 空壳；具体路由见后续 AG-*）。"""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("chat", __name__, url_prefix="/api/v1")

from app.chat.api import routes as _routes  # noqa: F401
