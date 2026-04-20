"""reconcile_jobs consumer：绑定 ORM session 后调用 ``use_cases.selection_reconcile``（W4）。"""


def handle_reconcile_job(payload: dict) -> None:
    from app.extensions import db
    from app.use_cases.selection_reconcile import reconcile_assignments

    reconcile_assignments(payload, session=db.session)


def run(payload: dict) -> None:
    handle_reconcile_job(payload)
