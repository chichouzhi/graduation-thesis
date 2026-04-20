"""Recommendations HTTP API Blueprint（AG-004 空壳；具体路由见后续 AG-*）。"""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("recommendations", __name__, url_prefix="/api/v1")

from app.recommendations.api import routes as _routes  # noqa: F401
