import time
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

@AgentServer.custom_action("fight")
class fight(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """
        fight 点击动作
        直接在代码中添加点击逻辑，格式：
        # 点击[x,y]delay t
        其中 x,y 是点击坐标，t 是延迟时间（毫秒）
        """
        try:
            # 执行点击操作的函数
            def click(x, y, delay_ms=0):
                """执行点击并延迟"""
                context.tasker.controller.post_click(x, y).wait()
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000)
            
            # ===================
            # 在这里添加你的点击序列
            # ===================
            # click(80, 360, t) 为大招原点
            # click(180, 260, t) 为小椒1式
            time.sleep(1)
            for i in range(16):
                click(80, 360, 300)
                click(180, 260, 300)
            

            return CustomAction.RunResult(success=True)
        except Exception as e:
            import logging
            logging.error(f"执行3v3点击时出错: {e}")
            print(f"执行3v3点击时出错: {e}")
            return CustomAction.RunResult(success=False)