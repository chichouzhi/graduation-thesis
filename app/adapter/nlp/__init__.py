"""NLP 适配层：同步 Jieba 分词，供 ``TopicService`` 等写画像路径调用。

**约束（与 ``architecture.spec.md`` R-RECOMMEND-NLP 等一致）**

- 本模块 **仅** 做入参文本 → 词序列的 **纯内存** 计算，**不** 访问 ORM、**不** 对业务库做批量写回。
- **推荐域** 不得用本模块「在线重推理」替代 Topic 侧既定的 Jieba + ``keyword_jobs`` 画像写路径；调用方负责仅在合法业务入口使用。

真源：``spec/execution_plan.md`` 阶段 3 Topic — Jieba **同步**；LLM 抽词仅入队。
"""

from __future__ import annotations

import jieba

__all__ = ("tokenize",)


def tokenize(text: str) -> list[str]:
    """对单段文本做 Jieba 精确模式分词，返回非空词序列（顺序与 ``jieba.cut`` 一致）。

    :param text: 课题标题/摘要等单条输入；空或仅空白则返回 ``[]``。
    """
    if not text:
        return []
    stripped = text.strip()
    if not stripped:
        return []
    return [t.strip() for t in jieba.cut(stripped, cut_all=False) if t.strip()]
