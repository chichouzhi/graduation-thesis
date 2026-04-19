# ADR：文献任务 `pdf_parse` 与 `document_jobs` 的入队时序

## 状态

**已采纳**（与 `contract.yaml` 中 `PdfJobPayload`、`DocumentJobPayload` 及 `x-task-contracts.queues` 一致；细化 `execution_plan.md` 中「受理侧须覆盖两条队列」的语义）。

## 背景

`execution_plan.md` 要求生产默认 **`enqueue(pdf_parse)`** 且文献多段 LLM 走 **`document_jobs`**，并禁止在 API 进程内默认同步解析 PDF。若受理线程在 **`pdf_parse` 未完成** 时即入队依赖全文/分块文本的 **`document_jobs`**，易出现竞态、空读或重复解析。

OpenAPI 契约只定义 **payload 与队列键**，未写明 **由谁、在何种条件下** 发出第一批可安全消费的 `document_jobs` 消息。

## 决策

1. **受理路径（`DocumentService`，`PROC_API`）**  
   - 事务内创建 `document_tasks` 行（`pending`）并落盘存储引用后 **`commit`**。  
   - **`commit` 成功之后**：**仅** `enqueue(pdf_parse)`，载荷为 **`PdfJobPayload`**（与 `contract.yaml` 一致）。  
   - **受理路径不得**在同一次 HTTP 请求内同步跑完 PDF 全文解析或 LLM 分块。

2. **`pdf_parse` 消费路径（`task/pdf_parse_jobs.py`，`PROC_WORKER`）**  
   - 完成 **PDF→可消费中间态**（文本或结构化块写入约定存储/DB 字段，由实现写死路径）。  
   - 调用 **`use_cases.document_pipeline`**（或等价命名）得到 **分块计划与 `DocumentJobPayload` 列表**（`stage` / `chunk_index` / `max_chunks` 等与契约一致）。  
   - **在此成功路径上** 再 **`enqueue(document_jobs)`**（可一条或多条，含控制面 `chunk_index: null` 的汇总任务若需要）。  
   - **`pdf_parse` 失败**：将 `document_tasks` 置 **`failed`**（及契约字段 `error_code`/`error_message`）；**不**入队依赖解析结果的 `document_jobs`。

3. **`document_jobs` 消费路径（`task/document_jobs.py`）**  
   - 仅消费 **已具备解析前置条件** 的载荷；**不**在 job 内复制 `document_pipeline` 的分块规则（**R-TASK-BIZ** / **R-UC-ONLY**）。

## 与 `execution_plan` 字面条目的对齐说明

「**`enqueue(pdf_parse)` + `document_jobs`**」解释为：**默认生产链路必须同时使用两条队列完成文献分析**；**并非**要求 **`DocumentService` 在同一函数尾连续两次 `enqueue` 且第二次不依赖解析结果**。第二次及后续 **`document_jobs` 入队** 的 **真源触发点** 为 **`pdf_parse` worker 成功提交** 之后。

若后续修订 `execution_plan.md`，建议将该句改为显式「受理只入队 `pdf_parse`；`document_jobs` 由 `pdf_parse` 成功路径批量入队」以消除歧义。

## 后果

- **R-QUEUE-ISO** / `check-queue-keys`：两条队列名仍须在 `contract.yaml` 声明；**实现侧** `enqueue` 字面量仍须 ⊆ 契约键集合。  
- **R-SYNC-LLM** / **§5.1**：Document POST 仍只需断言 **202**、无厂商 LLM HTTP；不要求受理时即出现 `document_jobs` 队列深度。  
- **观测**：`request_id` / `document_task_id` 应贯穿 `pdf_parse` 与后续 `document_jobs`。

## 审阅

- 架构：`architecture.spec.md` **W4 / W5 / R-UC-SKIP**（`document_jobs` 仍经 `UC`→`adapter`）。  
- 契约：`contract.yaml` **§`x-task-contracts.queues`**。
