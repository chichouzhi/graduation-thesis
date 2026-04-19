"""LLM adapter surface (stubs only)."""


class LlmClient:
    def chat(self, *args, **kwargs):
        pass


def complete(*args, **kwargs):
    pass


def invoke_chat(*args, **kwargs):
    pass


def call(*args, **kwargs):
    """最小统一入口名；占位 dict，集成测可 patch。"""
    _ = (args, kwargs)
    return {"content": ""}
