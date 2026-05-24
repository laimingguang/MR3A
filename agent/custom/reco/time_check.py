from typing import Optional, Union

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.define import RectType

from custom.pipeline_params import parse_pipeline_json_param
from utils import logger
from utils.time import (
    DEFAULT_TIMEZONE,
    now_in_timezone,
    parse_time_of_day,
    parse_weekday,
    today_at,
)

_HIT_BOX: RectType = [0, 0, 1, 1]


def _parse_timezone(param: dict) -> str:
    tz_raw = param.get("timezone", DEFAULT_TIMEZONE)
    tz_name = str(tz_raw).strip() if tz_raw is not None else DEFAULT_TIMEZONE
    return tz_name or DEFAULT_TIMEZONE


@AgentServer.custom_recognition("IsTargetWeekday")
class IsTargetWeekday(CustomRecognition):
    """
    检验当前是否为指定星期；匹配则命中。

    参数格式:
    {
        "weekday": 0,
        "timezone": "Asia/Shanghai"
    }

    字段说明:
    - weekday: 目标星期，必填。支持 0-6 整数（0=周一）、字符串 "1"-"7"（ISO，1=周一）、
      或中英文名称（如 "星期一"、"Monday"、"周一"）。
    - timezone: 时区，可选，默认 Asia/Shanghai。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> Union[CustomRecognition.AnalyzeResult, Optional[RectType]]:
        try:
            param = parse_pipeline_json_param(argv.custom_recognition_param)
            target_weekday = parse_weekday(param.get("weekday"))
            if target_weekday is None:
                logger.error(f"IsTargetWeekday: 无效的 weekday 参数: {param.get('weekday')}")
                return None

            tz_name = _parse_timezone(param)
            now = now_in_timezone(tz_name)
            current_weekday = now.weekday()
            if current_weekday != target_weekday:
                return None

            return CustomRecognition.AnalyzeResult(
                box=_HIT_BOX,
                detail={
                    "weekday": target_weekday,
                    "current_weekday": current_weekday,
                    "now": now.isoformat(),
                    "timezone": tz_name,
                },
            )
        except Exception as e:
            logger.exception(f"IsTargetWeekday 失败: {e}")
            return None


@AgentServer.custom_recognition("TimeAfter")
class TimeAfter(CustomRecognition):
    """
    检验当前时间是否已过（大于等于）今天指定时刻；满足则命中。

    参数格式:
    {
        "hour": 4,
        "minute": 0,
        "timezone": "Asia/Shanghai"
    }

    或使用 time 字符串:
    {
        "time": "4:00"
    }

    示例: hour=4 且当前为 5:00 → 命中；当前为 3:59 → 不命中。
  边界: 当前时间等于指定时刻时也视为命中（>=）。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> Union[CustomRecognition.AnalyzeResult, Optional[RectType]]:
        try:
            param = parse_pipeline_json_param(argv.custom_recognition_param)
            target_time = parse_time_of_day(param)
            if target_time is None:
                logger.error(f"TimeAfter: 无效的时间参数: {param}")
                return None

            tz_name = _parse_timezone(param)
            now = now_in_timezone(tz_name)
            threshold = today_at(target_time, now)
            if now < threshold:
                return None

            return CustomRecognition.AnalyzeResult(
                box=_HIT_BOX,
                detail={
                    "target_time": target_time.isoformat(),
                    "now": now.isoformat(),
                    "timezone": tz_name,
                },
            )
        except Exception as e:
            logger.exception(f"TimeAfter 失败: {e}")
            return None


@AgentServer.custom_recognition("TimeBefore")
class TimeBefore(CustomRecognition):
    """
    检验当前时间是否早于今天指定时刻；满足则命中。

    参数格式:
    {
        "hour": 4,
        "minute": 0,
        "timezone": "Asia/Shanghai"
    }

    或使用 time 字符串:
    {
        "time": "4:00"
    }

    示例: hour=4 且当前为 3:00 → 命中；当前为 5:00 → 不命中。
    边界: 当前时间等于指定时刻时不命中（<）。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> Union[CustomRecognition.AnalyzeResult, Optional[RectType]]:
        try:
            param = parse_pipeline_json_param(argv.custom_recognition_param)
            target_time = parse_time_of_day(param)
            if target_time is None:
                logger.error(f"TimeBefore: 无效的时间参数: {param}")
                return None

            tz_name = _parse_timezone(param)
            now = now_in_timezone(tz_name)
            threshold = today_at(target_time, now)
            if now >= threshold:
                return None

            return CustomRecognition.AnalyzeResult(
                box=_HIT_BOX,
                detail={
                    "target_time": target_time.isoformat(),
                    "now": now.isoformat(),
                    "timezone": tz_name,
                },
            )
        except Exception as e:
            logger.exception(f"TimeBefore 失败: {e}")
            return None
