"""PROC_WORKER 占位（architecture.spec §0）；真实消费逻辑在 app.task.*_jobs。"""


def run_once() -> int:
    """TODO: 从 broker 拉取并处理任务；返回本 tick 处理条数。"""
    return 0
