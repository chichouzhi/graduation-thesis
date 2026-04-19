"""Chat orchestration UC (skeleton; calls adapter for spy tests)."""


def run_turn(conversation_id: str, messages: list, term_id: str, **kwargs) -> None:
    from app.adapter import llm as llm_mod

    llm_mod.complete(messages)
