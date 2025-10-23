from .base_node import BaseNode, ToolNode
from ..data_model import ToolModeEnum, ToolNodeParam, AgentNodeParam, ClaudeCodeParam, NodeTypeEnum, AgentModeEnum
from .questionnaire_node import QuestionnaireNode
from .loop_questionnaire_node import LoopQuestionnaireNode
from .selector_group_chat_node import SelectorGroupChatNode
from .reflective_node import ReflectiveNode
from .claude_code_node import ClaudeCodeNode
from .interactive_node import InteractiveNode
from typing import Union, Dict


class NodeFactory:
    @staticmethod
    def create_node(node_type: str, config: Union[Dict, ToolNodeParam, AgentNodeParam, ClaudeCodeParam]) -> BaseNode:
        if node_type == NodeTypeEnum.TOOL:   

            tool_type = 'unknown'
            if isinstance(config, dict):
                tool_type = config.get('tool_type', 'unknown')
            elif isinstance(config, ToolNodeParam):
                tool_type = config.tool_type

            if tool_type == ToolModeEnum.ClaudeCodeAgent:
                return ClaudeCodeNode(config)
            else:
                raise NotImplementedError(f"Unknown tool type: {tool_type}")
            
        elif node_type == NodeTypeEnum.AGENT:
            # 对于字典配置，需要判断是否包含 manager 字段来决定类型
            if isinstance(config, dict):
                config = AgentNodeParam(**config)
            elif isinstance(config, AgentNodeParam):
                config = config
            else:
                raise ValueError(f"Invalid config type for AgentNode: {type(config)}")
            
            # 对于带 manager 的标准 AgentNodeParam
            if config.manager.mode == AgentModeEnum.Questionnaire :
                return QuestionnaireNode(config)
            elif config.manager.mode == AgentModeEnum.LoopQuestionnaire:
                return LoopQuestionnaireNode(config)
            elif config.manager.mode == AgentModeEnum.SelectorGroupChat:
                return SelectorGroupChatNode(config)
            elif config.manager.mode == AgentModeEnum.ReflectiveTeam:
                return ReflectiveNode(config)
            elif config.manager.mode == AgentModeEnum.Interactive:
                return InteractiveNode(config)
            else:                          
                raise NotImplementedError(f"Unknown agent mode: {config.manager.mode}")
        else:
            raise ValueError(f"Unknown node type: {node_type}")


__all__ = ["BaseNode", 'NodeFactory']