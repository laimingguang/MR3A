from typing import Any, Optional

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from custom.loop_deadline.params import normalize_duration_ms, parse_pipeline_json_param
from custom.loop_deadline.store import LoopDeadlineStore
from utils import logger

_DEFAULT_SCOPE = "default"


@AgentServer.custom_action("LoopDeadlineArm")
class LoopDeadlineArm(CustomAction):
    """
    设置循环总时长截止时间。应在进入循环段前执行一次。

    custom_action_param JSON:
    {
        "duration_ms": 1800000,
        "scope": "default"
    }
    - duration_ms: 必填，非负整数
    - scope: 可选，默认 "default"；识别侧 LoopDeadlineActive / LoopDeadlineExpired 须显式传同名 scope
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        try:
            param = parse_pipeline_json_param(argv.custom_action_param)
            duration_ms = normalize_duration_ms(param.get("duration_ms"))
            if duration_ms is None:
                logger.error(
                    "LoopDeadlineArm: duration_ms 无效或缺失（需为非负整数，可为 JSON 数字或字符串）"
                )
                return CustomAction.RunResult(success=False)
            scope = str(param.get("scope", _DEFAULT_SCOPE))
            task_id = argv.task_detail.task_id
            LoopDeadlineStore.arm(task_id, scope, duration_ms)
            return CustomAction.RunResult(success=True)
        except Exception as e:
            logger.exception(f"LoopDeadlineArm 失败: {e}")
            return CustomAction.RunResult(success=False)


@AgentServer.custom_action("LoopDeadlineReset")
class LoopDeadlineReset(CustomAction):
    """
    清除截止时间。scope 省略时清除当前任务下全部 scope。

    custom_action_param JSON（均可选）:
    { "scope": "my_loop" }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        try:
            param = parse_pipeline_json_param(argv.custom_action_param)
            scope_raw: Optional[Any] = param.get("scope", None)
            scope: Optional[str]
            if scope_raw is None:
                scope = None
            else:
                scope = str(scope_raw)
            task_id = argv.task_detail.task_id
            LoopDeadlineStore.reset(task_id, scope)
            return CustomAction.RunResult(success=True)
        except Exception as e:
            logger.exception(f"LoopDeadlineReset 失败: {e}")
            return CustomAction.RunResult(success=False)
