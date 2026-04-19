"""reconcile_jobs consumer (thin wiring for architecture tests)."""


def handle_reconcile_job(payload: dict) -> None:
    from app.use_cases.selection_reconcile import run

    run(payload)


def run(payload: dict) -> None:
    handle_reconcile_job(payload)
