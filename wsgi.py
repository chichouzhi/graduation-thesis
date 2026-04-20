"""WSGI 入口：生产/CI 可用 ``gunicorn wsgi:app`` 或 ``flask --app wsgi run``。"""
from __future__ import annotations

from app import create_app

app = create_app()
