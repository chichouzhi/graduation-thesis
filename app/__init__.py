"""Application root package.

分层目录（architecture.spec §0；非 ``app/api`` 单包）：

* **api** — ``app.<domain>.api``（如 ``app.chat.api``）
* **service** — ``app.<domain>.service``
* **model** — ``app.<domain>.model`` 与 ``app.model``
* **use_cases** — ``app.use_cases``
* **task** — ``app.task``（含 ``queue``、``*_jobs``）
* **adapter** — ``app.adapter``（含 ``llm`` 等）
* **worker** — ``app.worker``（进程语义占位，与 ``PROC_WORKER`` 对齐）
"""
