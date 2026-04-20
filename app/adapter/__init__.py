"""Integration boundary (`ADAPTER` in ``architecture.spec.md``).

子包（编排经 ``use_cases`` 引用；``app.task`` 不得直连 ``app.adapter``）：

- ``app.adapter.llm`` — 大模型调用
- ``app.adapter.pdf`` — PDF 解析封装
- ``app.adapter.nlp`` — 分词 / 轻量 NLP（如同步 Jieba）
- ``app.adapter.storage`` — 对象存储与路径封装

**对外导入约定**

- 从子包导入具体符号，例如 ``from app.adapter.llm import call``；避免依赖未文档化的深层模块路径。
- 允许 ``from app.adapter import llm`` 等形式仅引用**子包模块对象**（与标准库包布局一致）；不得从根包导入业务函数/类（见 ``__all__``）。
- 根包 ``app.adapter`` **不**聚合重导出各子包的业务符号，以降低隐式耦合与循环引用风险；后续能力在对应子包内演进（如 AG-027+）。

真源：``docs/architecture/system-architecture.md`` §3；分层规则 ``spec/architecture.spec.md``（W5、W6）。
"""

# 仅声明可经 ``from app.adapter import *`` 或静态工具识别的子包名；不包含各子包内的函数/类。
__all__ = ("llm", "pdf", "nlp", "storage")
