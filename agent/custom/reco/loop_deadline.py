from typing import Optional, Union

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.define import RectType

from custom.pipeline_params import parse_pipeline_json_param
from custom.loop_deadline.store import LoopDeadlineStore
from utils import logger


def _explicit_scope_from_argv(argv_param: str) -> Optional[str]:
    """
    从 custom_recognition_param 解析 scope。
    未设置（空 JSON、无 scope 键、scope 为空字符串）→ None，表示不命中。
    """
    param = parse_pipeline_json_param(argv_param)
    scope_raw = param.get("scope", None)
    if scope_raw is None:
        return None
    scope = str(scope_raw).strip()
    if not scope:
        return None
    return scope


@AgentServer.custom_recognition("LoopDeadlineExpired")
class LoopDeadlineExpired(CustomRecognition):
    """
    超时分支：显式传入非空 scope，且已为该 scope Arm，且当前已超过截止时间 → 命中；否则不命中。
    custom_recognition_param 为空、或未含非空 scope → 视为参数未设置 → 不命中。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> Union[CustomRecognition.AnalyzeResult, Optional[RectType]]:
        try:
            scope = _explicit_scope_from_argv(argv.custom_recognition_param)
            if scope is None:
                return None
            task_id = argv.task_detail.task_id
            if not LoopDeadlineStore.is_armed(task_id, scope):
                return None
            if not LoopDeadlineStore.is_expired(task_id, scope):
                return None
            return CustomRecognition.AnalyzeResult(
                box=[0, 0, 1, 1],
                detail={"scope": scope, "expired": True},
            )
        except Exception as e:
            logger.exception(f"LoopDeadlineExpired 失败: {e}")
            return None


@AgentServer.custom_recognition("LoopDeadlineActive")
class LoopDeadlineActive(CustomRecognition):
    """
    未超时分支：显式传入非空 scope，且已为该 scope Arm，且尚未超时 → 命中；否则不命中。
    custom_recognition_param 为空、或未含非空 scope → 视为参数未设置 → 不命中。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> Union[CustomRecognition.AnalyzeResult, Optional[RectType]]:
        try:
            scope = _explicit_scope_from_argv(argv.custom_recognition_param)
            if scope is None:
                return None
            task_id = argv.task_detail.task_id
            if not LoopDeadlineStore.is_armed(task_id, scope):
                return None
            if LoopDeadlineStore.is_expired(task_id, scope):
                return None
            return CustomRecognition.AnalyzeResult(
                box=[0, 0, 1, 1],
                detail={"scope": scope, "active": True},
            )
        except Exception as e:
            logger.exception(f"LoopDeadlineActive 失败: {e}")
            return None
