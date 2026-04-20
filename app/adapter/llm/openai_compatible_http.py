"""OpenAI 兼容 Chat Completions HTTP 客户端（单文件厂商实现，AG-028）。

通过环境变量或构造函数注入 ``base_url`` / ``api_key`` / ``model``；与多数国内兼容网关一致。
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any, Final
from urllib.parse import urljoin

from app.adapter.llm.client import LlmClient
from app.common.error_envelope import ErrorCode

# 有限重试 K（不含首次请求）：与 execution_plan「禁止无限重试」一致
K_RETRIES: Final[int] = 3
_BACKOFF_BASE_S: Final[float] = 0.5
_BACKOFF_CAP_S: Final[float] = 8.0
_DEFAULT_TIMEOUT_S: Final[float] = 60.0

# 非消息体字段，不写入 OpenAI 兼容 JSON body
_SKIP_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "conversation_id",
        "term_id",
        "user_id",
        "request_id",
        "job_id",
        "user_message_id",
        "assistant_message_id",
    }
)


class LlmTransportError(RuntimeError):
    """厂商 HTTP 失败；``error_code`` 与 ``contract.yaml`` → ``ErrorEnvelope.error.code`` 对齐。"""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        http_status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.http_status = http_status
        self.details = details


class OpenAiCompatibleHttpClient(LlmClient):
    """``POST {base_url}/chat/completions``；Bearer ``api_key``。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        max_retries: int = K_RETRIES,
    ) -> None:
        self._base = base_url.rstrip("/") + "/"
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._max_retries = max_retries

    def complete(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> dict[str, Any]:
        url = urljoin(self._base, "chat/completions")
        payload: dict[str, Any] = {"model": self._model, "messages": messages}
        for k, v in kwargs.items():
            if k in _SKIP_PAYLOAD_KEYS or v is None:
                continue
            payload[k] = v

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                    raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                return self._parse_completion_json(data)
            except urllib.error.HTTPError as e:
                status = e.code
                err_body = _read_http_error_body(e)
                if not _should_retry_http(status, attempt, self._max_retries):
                    raise _map_http_error(status, err_body) from e
                last_exc = e
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt >= self._max_retries:
                    raise LlmTransportError(
                        f"LLM HTTP 网络失败（已重试 {self._max_retries} 次）: {e}",
                        error_code=ErrorCode.DOMAIN_ERROR.value,
                        http_status=None,
                        details={"attempt": attempt},
                    ) from e
                last_exc = e
            if attempt < self._max_retries:
                _sleep_backoff(attempt)
        assert last_exc is not None
        raise LlmTransportError(
            "LLM HTTP 在有限重试后仍失败",
            error_code=ErrorCode.DOMAIN_ERROR.value,
            details={"last_error": repr(last_exc)},
        )

    @staticmethod
    def _parse_completion_json(data: dict[str, Any]) -> dict[str, Any]:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return {"content": ""}
        first = choices[0]
        if not isinstance(first, dict):
            return {"content": ""}
        msg = first.get("message")
        if isinstance(msg, dict) and "content" in msg:
            c = msg.get("content")
            return {"content": c if isinstance(c, str) else str(c)}
        # 兼容部分网关 ``text`` 字段
        if "text" in first and isinstance(first.get("text"), str):
            return {"content": first["text"]}
        return {"content": ""}


def openai_compatible_client_from_environ() -> OpenAiCompatibleHttpClient | None:
    """若配置了 ``LLM_HTTP_API_KEY``（或 ``OPENAI_API_KEY``）则构造客户端，否则 ``None``。"""
    key = os.environ.get("LLM_HTTP_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key or not str(key).strip():
        return None
    base = (
        os.environ.get("LLM_HTTP_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    model = os.environ.get("LLM_HTTP_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    timeout_raw = os.environ.get("LLM_HTTP_TIMEOUT_S")
    timeout_s = _DEFAULT_TIMEOUT_S
    if timeout_raw and timeout_raw.strip():
        try:
            timeout_s = float(timeout_raw.strip())
        except ValueError:
            pass
    return OpenAiCompatibleHttpClient(
        base_url=base.strip(),
        api_key=str(key).strip(),
        model=model.strip(),
        timeout_s=timeout_s,
    )


def _read_http_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — 仅消费响应体用于排障
        return ""


def _should_retry_http(status: int, attempt: int, max_retries: int) -> bool:
    if attempt >= max_retries:
        return False
    return status in (408, 429, 500, 502, 503, 504)


def _map_http_error(status: int, body: str) -> LlmTransportError:
    if status == 429:
        return LlmTransportError(
            "LLM 厂商限流或配额不足",
            error_code=ErrorCode.LLM_RATE_LIMITED.value,
            http_status=status,
            details={"body_preview": body[:512]},
        )
    if status in (401, 403):
        return LlmTransportError(
            "LLM 鉴权失败",
            error_code=ErrorCode.UNAUTHORIZED.value,
            http_status=status,
            details={"body_preview": body[:512]},
        )
    return LlmTransportError(
        f"LLM HTTP 错误 {status}",
        error_code=ErrorCode.DOMAIN_ERROR.value,
        http_status=status,
        details={"body_preview": body[:512]},
    )


def _sleep_backoff(attempt: int) -> None:
    exp = min(_BACKOFF_CAP_S, _BACKOFF_BASE_S * (2**attempt))
    jitter = random.uniform(0, _BACKOFF_BASE_S)
    time.sleep(exp + jitter)


__all__ = (
    "K_RETRIES",
    "LlmTransportError",
    "OpenAiCompatibleHttpClient",
    "openai_compatible_client_from_environ",
)
