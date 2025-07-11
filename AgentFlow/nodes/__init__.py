from .base_node import BaseNode, ToolNode
from ..data_model import ToolNodeParam, AgentNodeParam, NodeTypeEnum, AgentModeEnum
from .questionnaire_node import QuestionnaireNode
from .loop_questionnaire_node import LoopQuestionnaireNode
from .selector_group_chat_node import SelectorGroupChatNode
from .reflective_node import ReflectiveNode
from typing import Union, Dict


class NodeFactory:
    @staticmethod
    def create_node(node_type: str, config: Union[Dict, ToolNodeParam, AgentNodeParam]) -> BaseNode:
        if node_type == NodeTypeEnum.TOOL:   
            if isinstance(config, dict):
                config = ToolNodeParam(**config)         
            return ToolNode(config)
        elif node_type == NodeTypeEnum.AGENT:
            if isinstance(config, dict):
                config = AgentNodeParam(**config)
            
            if config.manager.mode == AgentModeEnum.Questionnaire :
                return QuestionnaireNode(config)
            elif config.manager.mode == AgentModeEnum.LoopQuestionnaire:
                return LoopQuestionnaireNode(config)
            elif config.manager.mode == AgentModeEnum.SelectorGroupChat:
                return SelectorGroupChatNode(config)
            elif config.manager.mode == AgentModeEnum.ReflectiveTeam:
                return ReflectiveNode(config)
            else:                          
                NotImplementedError(f"Unknown agent mode: {config.manager.mode}")
        else:
            raise ValueError(f"Unknown node type: {node_type}")


__all__ = ["BaseNode", 'NodeFactory']