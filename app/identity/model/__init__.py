"""Identity 域 ORM：``users`` 与契约 ``UserSummary`` / ``UserMe`` 对齐的最小列集（AG-008）。"""
from __future__ import annotations

import enum
import uuid
from typing import Any

from app.extensions import db


class UserRole(str, enum.Enum):
    """与 ``contract.yaml`` → ``UserSummary.role`` 一致：student | teacher | admin。"""

    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(db.Model):
    """``users`` 表；序列化形状见 ``to_user_summary`` / ``to_user_me``（与 OpenAPI 组件对齐）。"""

    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(128), unique=True, nullable=False, index=True)
    role = db.Column(
        db.Enum(UserRole, name="user_role", native_enum=False, length=16),
        nullable=False,
    )
    display_name = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(256), nullable=True)
    student_profile = db.Column(db.JSON, nullable=True)
    teacher_profile = db.Column(db.JSON, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)

    def to_user_summary(self) -> dict[str, Any]:
        """``UserSummary`` 必填字段子集。"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "display_name": self.display_name,
        }

    def to_user_me(self) -> dict[str, Any]:
        """``UserMe``：在 ``UserSummary`` 基础上含可空 profile / email。"""
        return {
            **self.to_user_summary(),
            "email": self.email,
            "student_profile": self.student_profile,
            "teacher_profile": self.teacher_profile,
        }


__all__ = ["User", "UserRole"]
