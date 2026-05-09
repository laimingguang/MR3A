"""
弹窗守护：在主任务运行期间，按节流频率检查并关闭好友/网络等弹窗。

实现说明（重要）：
    1. 自起的 threading.Thread 里调任何 Maa IPC 都会触发 AgentServer 内部错误，
       且 post_*().wait() 会因响应路由问题而死锁。本模块**不使用线程**，全部
       逻辑跑在 Maa 回调线程内。
    2. TaskerEventSink 只接收 Tasker.Task.* 事件（任务两端各一次），任务执行
       期间不会触发；要在节点流转期间被回调，必须用 ContextEventSink。
    3. **绝不使用** controller.post_screencap()、tasker.post_recognition()、
       tasker.post_action() 这种 "post + wait()" 异步接口——它们在 Context 回调
       线程里会死锁（线程在 wait，响应没法被同一线程分派回来）。
       改用：
         - controller.cached_image  ：同步读，空就跳过本轮等下一轮（主任务每做
           一次识别都会自带截图，cached_image 自然会被填上）。
         - context.run_recognition(name, image)  ：**同步** sync API。
         - context.run_action(name, box, reco)   ：**同步** sync API。

请在 assets/resource/pipeline/弹窗守护.json（或合并后的资源）中定义与
``DEFAULT_DISMISS_NODE_NAMES`` 同名的节点；顺序即优先级。
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Set, Tuple

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, ContextEventSink
from maa.event_sink import NotificationType
from maa.tasker import Tasker, TaskerEventSink

from utils.logger import logger

# 与弹窗守护.json 中节点名一致；前者优先识别（可自行调整顺序）
DEFAULT_DISMISS_NODE_NAMES: Tuple[str, ...] = (
    "好友弹窗取消邀请",
)

# 至少多久检查一次（秒）；Node.* 回调远高频，等价"上限频率"。
DEFAULT_POLL_INTERVAL_SEC: float = 1.5

# 注：点击后让 UI 关闭动画走完不在 Python 侧 sleep，而是在 pipeline JSON 的
# 节点上配 "post_delay": <ms>。run_action 走的是节点完整定义，会自带 pre_delay
# / post_delay。不 settle 的话主任务紧接着的下一次识别会拍到「弹窗正在消失」
# 的中间帧，容易识别失败 → 触发 JumpBack/Retry。


class _WatchdogCore:
    """两个 sink 共享的状态与检查逻辑。"""

    def __init__(
        self,
        dismiss_node_names: Tuple[str, ...] = DEFAULT_DISMISS_NODE_NAMES,
        poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
    ):
        self.dismiss_node_names = dismiss_node_names
        self.poll_interval_sec = poll_interval_sec

        self._scan_lock = threading.Lock()
        self._last_check_ts: float = 0.0
        self._warned_missing: Set[str] = set()
        # 当前正在守护的 task_id（仅用于日志）；-1 表示尚未感知到任务
        self._current_task_id: int = -1
        # 是否已确认 cached_image 至少被填过一次。
        # 主任务每完成一次识别（Succeeded/Failed）后，cached_image 一定刷新过；
        # 在那之前调用会让 C++ 层 MaaControllerCachedImage 抛 "image is empty" ERR。
        # 用这个 flag 把首次 ERR 也消掉。
        self._image_ready: bool = False

    # -------- 检查（由 ContextEventSink 在 Maa 回调线程上调用） --------

    def maybe_check(self, context: Context, task_id: int = -1) -> None:
        # 任务切换检测：第一次见到新 task_id 就报"已启动"
        # （绕过 Tasker.Task.Starting 在某些环境下不触发的问题）
        if task_id > 0 and task_id != self._current_task_id:
            if self._current_task_id != -1:
                logger.debug(f"弹窗守护已停止 task_id={self._current_task_id}")
            self._current_task_id = task_id
            logger.debug(
                f"弹窗守护已启动 task_id={task_id} "
                f"nodes={self.dismiss_node_names} "
                f"interval={self.poll_interval_sec}s"
            )

        # 节流：未到下一轮就立刻返回（保证回调"尽快返回"语义）
        now = time.monotonic()
        if now - self._last_check_ts < self.poll_interval_sec:
            return
        # 同线程重入保护（识别/点击中框架可能再触发回调，避免再进来一遍）
        if not self._scan_lock.acquire(blocking=False):
            return
        try:
            self._last_check_ts = now
            logger.debug("[弹窗守护] 开始一轮检查")
            self._do_check(context)
            logger.debug("[弹窗守护] 本轮检查结束")
        except Exception as e:
            logger.exception(f"弹窗守护检查异常: {e!r}")
        finally:
            self._scan_lock.release()

    def notify_task_finished(self, task_id: int) -> None:
        """TaskerSink 在 Succeeded/Failed 时调用，复位当前任务。"""
        if task_id == self._current_task_id and task_id != -1:
            logger.debug(f"弹窗守护已停止 task_id={task_id}")
            self._current_task_id = -1

    def mark_image_ready(self) -> None:
        """ContextSink 收到首个 Recognition 完成事件时调用。"""
        if not self._image_ready:
            self._image_ready = True
            logger.debug("[弹窗守护] 首张截图就绪，开始访问 cached_image")

    def _do_check(self, context: Context) -> None:
        # 1) tasker.stopping —— 同步只读，安全
        try:
            if context.tasker.stopping:
                logger.debug("[弹窗守护] tasker.stopping=True，跳过")
                return
        except Exception as e:
            logger.exception(f"[弹窗守护] 读取 tasker.stopping 异常: {e!r}")
            return

        # 2) cached_image —— 同步只读
        # 首张截图就绪前，绝不调用（避免 C++ 层 "image is empty" ERR 噪音）
        if not self._image_ready:
            logger.debug("[弹窗守护] 等待首张截图就绪，跳过")
            return
        img = self._acquire_image(context)
        if img is None:
            logger.debug("[弹窗守护] cached_image 为空/失败，跳过本轮")
            return
        logger.debug(f"[弹窗守护] 拿到截图，shape={getattr(img, 'shape', '?')}")

        # 3) 对每个守护节点 run_recognition（同步），命中再 run_action（同步）
        for name in self.dismiss_node_names:
            # 节点存在性检查（仅用于一次性 warning）
            try:
                node_check = context.get_node_object(name)
            except Exception as e:
                logger.exception(f"弹窗守护：读取节点 {name!r} 失败: {e!r}")
                continue
            if node_check is None:
                if name not in self._warned_missing:
                    self._warned_missing.add(name)
                    logger.warning(
                        f"弹窗守护：未找到 pipeline 节点 {name!r}，"
                        f"请检查弹窗守护.json 是否已加载"
                    )
                continue

            # 同步识别
            try:
                reco_detail = context.run_recognition(name, img)
            except Exception as e:
                logger.exception(f"弹窗守护：识别 {name!r} 异常: {e!r}")
                continue
            if reco_detail is None:
                logger.debug(f"[弹窗守护] {name!r} run_recognition 返回 None")
                continue
            if not reco_detail.hit:
                logger.debug(f"[弹窗守护] {name!r} 未命中")
                continue

            # 命中：同步点击
            box = reco_detail.box if reco_detail.box is not None else (0, 0, 0, 0)
            try:
                act_detail = context.run_action(name, box, "")
            except Exception as e:
                logger.exception(f"弹窗守护：执行 {name!r} 异常: {e!r}")
                continue

            ok = bool(act_detail and act_detail.success)
            logger.debug(
                f"弹窗守护：已处理（节点 {name}）"
                f"{'' if ok else '（动作返回 success=False）'}"
            )
            # 关闭动画的 settle 由节点自身 "post_delay" 提供（run_action 会自带）
            return

    def _acquire_image(self, context: Context) -> Optional[numpy.ndarray]:
        """仅使用 cached_image，绝不调用 post_screencap。"""
        try:
            img = context.tasker.controller.cached_image
        except Exception:
            return None
        return img if img is not None else None


# 模块级共享 core；两个 sink 都引用它
_core = _WatchdogCore()


@AgentServer.tasker_sink()
class PopupWatchdog(TaskerEventSink):
    """生命周期 sink：仅打日志，便于排查启停时点。"""

    @staticmethod
    def maybe_tick(context: Context) -> None:
        """供长 sleep 的自定义动作主动调用，保证长动作期间也能检测弹窗。

        必须在「Maa 回调线程」上下文里调用（CustomAction.run 内部就是该线程）。
        """
        _core.maybe_check(context)

    @staticmethod
    def configure(
        dismiss_node_names: Optional[Tuple[str, ...]] = None,
        poll_interval_sec: Optional[float] = None,
    ) -> None:
        """运行时调整守护参数（如需要）。"""
        if dismiss_node_names is not None:
            _core.dismiss_node_names = dismiss_node_names
        if poll_interval_sec is not None:
            _core.poll_interval_sec = poll_interval_sec

    def on_tasker_task(
        self,
        tasker: Tasker,
        noti_type: NotificationType,
        detail: TaskerEventSink.TaskerTaskDetail,
    ):
        logger.debug(
            f"[弹窗守护] on_tasker_task type={noti_type.name} "
            f"task_id={detail.task_id} entry={detail.entry!r}"
        )
        if detail.entry == "MaaTaskerPostStop":
            return
        # "已启动" 由 ContextSink 在首次见到新 task_id 时报；
        # 这里只负责"已停止"——任务结束时复位 core 状态。
        if noti_type in (NotificationType.Succeeded, NotificationType.Failed):
            _core.notify_task_finished(detail.task_id)


@AgentServer.context_sink()
class _PopupCheckSink(ContextEventSink):
    """检查 sink：在 Maa 回调线程内做节流检查。"""

    def on_node_pipeline_node(
        self,
        context: Context,
        noti_type: NotificationType,
        detail: ContextEventSink.NodePipelineNodeDetail,
    ):
        if noti_type != NotificationType.Starting:
            return
        _core.maybe_check(context, task_id=detail.task_id)

    def on_node_next_list(
        self,
        context: Context,
        noti_type: NotificationType,
        detail: ContextEventSink.NodeNextListDetail,
    ):
        # 备份触发点：有些场景 PipelineNode 频次较低，NextList 同时存在
        if noti_type != NotificationType.Starting:
            return
        _core.maybe_check(context, task_id=detail.task_id)

    def on_node_recognition(
        self,
        context: Context,
        noti_type: NotificationType,
        detail: ContextEventSink.NodeRecognitionDetail,
    ):
        # Recognition 一旦完成（成功/失败均可），controller.cached_image 就一定
        # 被填充过；之后我们再去读才不会让 C++ 层抛 "image is empty" ERR。
        if noti_type in (NotificationType.Succeeded, NotificationType.Failed):
            _core.mark_image_ready()
