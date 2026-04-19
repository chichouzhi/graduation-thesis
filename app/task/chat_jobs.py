"""chat_jobs consumer (thin wiring for architecture tests)."""


def handle_chat_job(payload: dict) -> None:
    from app.use_cases import chat_orchestration as uc

    uc.run_turn(
        conversation_id=payload.get("conversation_id", ""),
        messages=[{"role": "user", "content": ""}],
        term_id=payload.get("term_id", ""),
    )


def run(payload: dict) -> None:
    handle_chat_job(payload)
