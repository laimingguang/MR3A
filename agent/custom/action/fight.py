import time
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from custom.pipeline_params import parse_pipeline_json_param
from utils import logger


def _coerce_fight_mode(value: Any) -> int:
    """0/1/2；缺省或非法时返回 0。"""
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        if value in (0, 1, 2):
            return value
        logger.warning(f"fight: mode 非法 ({value})，使用 0")
        return 0
    if isinstance(value, str):
        s = value.strip()
        if s in ("0", "1", "2"):
            return int(s)
        if s == "":
            return 0
        logger.warning(f"fight: mode 非法 ({value!r})，使用 0")
        return 0
    logger.warning(f"fight: mode 类型不支持 ({type(value).__name__})，使用 0")
    return 0


@AgentServer.custom_action("fight")
class fight(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """
        fight 点击动作。

        custom_action_param（可选，JSON 字符串或对象）:
            { "mode": 0 | 1 | 2 }

        mode 0 为通用大招
        mode 1 为小椒大招
        mode 2 为卫鲤大招
        未传、空对象或缺省 mode 时视为模式 0（通用大招）。
        

        """
        try:
            param = parse_pipeline_json_param(argv.custom_action_param)
            mode = _coerce_fight_mode(param.get("mode", 0))

            def click(x: int, y: int, delay_ms: int = 0) -> None:
                context.tasker.controller.post_click(x, y).wait()
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000)

            # click(80, 360, t) 为大招原点
            # click(180, 260, t) 为小椒1式
            # click(210, 350, t) 为卫鲤2式
            # mode 0 为通用大招
            # mode 1 为小椒大招
            # mode 2 为卫鲤大招
            if mode == 0:
                for _ in range(50):
                    click(80, 360, 200)
            elif mode == 1:
                for _ in range(25):
                    click(80, 360, 100)
                    click(180, 260, 100)
            elif mode == 2:
                click(80, 360, 200)
                for _ in range(25):
                    click(210, 350, 200)

            return CustomAction.RunResult(success=True)
        except Exception as e:
            logger.exception(f"fight 执行出错: {e}")
            return CustomAction.RunResult(success=False)
