import time
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

@AgentServer.custom_action("my_3v3_kn_ying")
class my_3v3_kn_ying(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """
        3v3 点击动作
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
            # click(200, 620, t) 为下翻
            # click(1100, 620, t) 为跳跃
            click(1, 1, 3092)
            click(1100, 620, 320)
            click(1100, 620, 1110)
            click(1100, 620, 300)
            click(1100, 620, 1100)
            click(1100, 620, 100)
            click(1100, 620, 100)
            click(200, 620, 200)
            click(1100, 620, 660)
            click(1100, 620, 500)
            click(1100, 620, 128)
            click(200, 620, 99)
            click(1100, 620, 419)
            click(200, 620, 199)
            click(1100, 620, 419)
            click(1100, 620, 450)
            click(200, 620, 15650)
            click(1100, 620, 2700)
            click(1100, 620, 1600)
            click(1100, 620, 1000)
            click(1100, 620, 1000)
            click(1100, 620, 250)
            click(1100, 620, 250)
            click(1100, 620, 7000)
            click(1252, 30, 0)
            # ===================
            # 结束点击序列
            # ===================
            
            return CustomAction.RunResult(success=True)
        except Exception as e:
            import logging
            logging.error(f"执行3v3点击时出错: {e}")
            print(f"执行3v3点击时出错: {e}")
            return CustomAction.RunResult(success=False)