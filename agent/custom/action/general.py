import os
import json
from datetime import datetime

from PIL import Image
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from utils import logger
from custom.reco import Count


@AgentServer.custom_action("DisableNode")
class DisableNode(CustomAction):
    """
    将特定 node 设置为 disable 状态 。

    参数格式:
    {
        "node_name": "结点名称"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        node_name = json.loads(argv.custom_action_param)["node_name"]

        context.override_pipeline({f"{node_name}": {"enabled": False}})

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("NodeOverride")
class NodeOverride(CustomAction):
    """
    在 node 中执行 pipeline_override 。

    参数格式:
    {
        "node_name": {"被覆盖参数": "覆盖值",...},
        "node_name1": {"被覆盖参数": "覆盖值",...}
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        ppover = json.loads(argv.custom_action_param)

        if not ppover:
            logger.warning("No ppover")
            return CustomAction.RunResult(success=True)

        logger.debug(f"NodeOverride: {ppover}")
        context.override_pipeline(ppover)

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("ResetCount")
class ResetCount(CustomAction):
    """
    重置计数器。

    参数格式:
    {
        "node_name": String # 目标计数器节点名称，不存在时重置全部节点
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        if not argv.custom_action_param:
            Count.reset_count()
            return CustomAction.RunResult(success=True)

        param = json.loads(argv.custom_action_param)
        if not param:
            Count.reset_count()
            return CustomAction.RunResult(success=True)

        node_name = param.get("node_name", None)
        Count.reset_count(node_name)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("AddExpected")
class AddExpected(CustomAction):
    """
    给目标节点的expected参数添加值(单个)

    参数格式:
    {
        "node_name": "TargetNode",  // 目标节点名称
        "value": "NewValue",         // 要添加的值
        "delimiter": "|"             // 值之间的分隔符，默认为"|"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        param = json.loads(argv.custom_action_param)
        node_name = param.get("node_name")
        value = param.get("value")
        delimiter = param.get("delimiter", "|")
        
        if not node_name or not value:
            logger.error("缺少必要参数: node_name 或 value")
            return CustomAction.RunResult(success=False)
        
        # 获取目标节点的当前配置
        node_data = context.get_node_data(node_name)
        if not node_data:
            logger.error(f"未找到节点: {node_name}")
            return CustomAction.RunResult(success=False)
        
        # 获取当前的expected值
        current_expected = node_data.get("recognition", {}).get("param", {}).get("expected", "")
        
        # 解析当前值并添加新值
        if isinstance(current_expected, str):
            current_values = current_expected.split(delimiter) if current_expected else []
        else:
            # 处理列表中的每个元素，检查是否包含分隔符
            current_values = []
            for item in current_expected:
                if delimiter in item:
                    # 如果元素包含分隔符，拆分后添加
                    current_values.extend(item.split(delimiter))
                else:
                    # 否则直接添加
                    current_values.append(item)
        
        # 确保值不重复
        if value not in current_values:
            current_values.append(value)
        
        # 构建新的expected值
        if isinstance(current_expected, str):
            new_expected = delimiter.join(current_values)
        else:
            # 保持列表格式
            new_expected = current_values
        
        # 更新节点配置
        context.override_pipeline({
            node_name: {
                "recognition": {
                    "param": {
                        "expected": new_expected
                    }
                }
            }
        })
        
        logger.debug(f"已为节点 {node_name} 添加值: {value}，新的expected: {new_expected}")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("SubExpected")
class SubExpected(CustomAction):
    """
    从目标节点的expected参数中移除值(单个)

    参数格式:
    {
        "node_name": "TargetNode",  // 目标节点名称
        "value": "ValueToRemove",     // 要移除的值
        "delimiter": "|"              // 值之间的分隔符，默认为"|"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        param = json.loads(argv.custom_action_param)
        node_name = param.get("node_name")
        value = param.get("value")
        delimiter = param.get("delimiter", "|")
        
        if not node_name or not value:
            logger.error("缺少必要参数: node_name 或 value")
            return CustomAction.RunResult(success=False)
        
        # 获取目标节点的当前配置
        node_data = context.get_node_data(node_name)
        if not node_data:
            logger.error(f"未找到节点: {node_name}")
            return CustomAction.RunResult(success=False)
        
        # 获取当前的expected值
        current_expected = node_data.get("recognition", {}).get("param", {}).get("expected", "")
        
        # 解析当前值并移除指定值
        if isinstance(current_expected, str):
            current_values = current_expected.split(delimiter) if current_expected else []
        else:
            # 处理列表中的每个元素，检查是否包含分隔符
            current_values = []
            for item in current_expected:
                if delimiter in item:
                    # 如果元素包含分隔符，拆分后添加
                    current_values.extend(item.split(delimiter))
                else:
                    # 否则直接添加
                    current_values.append(item)
        
        # 移除指定值
        if value in current_values:
            current_values.remove(value)
        
        # 构建新的expected值
        if isinstance(current_expected, str):
            new_expected = delimiter.join(current_values)
        else:
            # 保持列表格式
            new_expected = current_values
        
        # 更新节点配置
        context.override_pipeline({
            node_name: {
                "recognition": {
                    "param": {
                        "expected": new_expected
                    }
                }
            }
        })
        
        logger.debug(f"已从节点 {node_name} 移除值: {value}，新的expected: {new_expected}")
        return CustomAction.RunResult(success=True)

