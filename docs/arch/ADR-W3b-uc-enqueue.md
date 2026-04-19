# ADR: 启用 W3b（`UC` → `task/queue` 入队）

## 状态

默认 **拒绝**（本毕设交付 **W3b=关**，仅 **W3** `SVC` → `app.task.queue`）。

## 背景

`architecture.spec.md` **§1.1 W3b** 允许编排层直接调用入队门面，以降低部分用例的间接层数；但与 **R-QUEUE-CONSIST**、**R-POLICY-SVC**（Policy 须在 `SVC` 入队路径）组合时，易出现 **Policy 与事务边界** 重复或遗漏。

## 决策

若团队启用 **W3b**，须同时满足：

1. **import-linter**：`forbidden_api_use_cases` 等合约仍禁止 `API`→`UC`；**W3b 仅** 放开 `UC`→`app.task` 中 **唯一** 允许的 `queue`（或同级 `enqueue`）模块，**不得** import `*_jobs.py`。
2. **Policy**：凡经 **W3b** 入队的路径，**仍须** 在 **同一业务事务** 内已由 **`SVC` 调用 Policy** 或 **在 `UC` 入口显式复用** `SVC` 已写入的 **Policy 断言结果**（二选一写进代码评审记录），且 **`commit` 先于 `enqueue`** 不变。
3. **CI**：在 `architecture.spec.md` **§5** 打开对应 **`W3b` 门禁**（由仓库 `Makefile`/CI yaml 写死开关名）。

## 后果

- 文档与 **import-linter** 须同步更新；未通过本 ADR 评审前 **保持 W3b 关闭**。
