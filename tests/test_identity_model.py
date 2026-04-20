"""AG-008：``users`` ORM 与 ``UserSummary`` / ``UserMe`` 字段对齐。"""
from __future__ import annotations

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole


def test_user_role_values_match_contract() -> None:
    assert {r.value for r in UserRole} == {"student", "teacher", "admin"}


def test_user_persists_and_maps_to_contract_shapes() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = User(
            username="t1",
            role=UserRole.teacher,
            display_name="Teacher One",
            email="t1@example.com",
            student_profile=None,
            teacher_profile={"dept": "CS"},
        )
        db.session.add(u)
        db.session.commit()

        loaded = db.session.get(User, u.id)
        assert loaded is not None
        assert loaded.role is UserRole.teacher

        summary = loaded.to_user_summary()
        assert summary == {
            "id": loaded.id,
            "username": "t1",
            "role": "teacher",
            "display_name": "Teacher One",
        }

        me = loaded.to_user_me()
        assert me["email"] == "t1@example.com"
        assert me["student_profile"] is None
        assert me["teacher_profile"] == {"dept": "CS"}
