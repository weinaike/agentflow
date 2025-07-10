from ..nodes import BaseNode
from ..data_model import SequentialFlowParam, Context, NodeOutput
from .base_flow import BaseFlow

from typing import  Dict, Union, List, Optional, AsyncGenerator, Union
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.base import Response
import os
import json
import logging
from collections import deque

logger = logging.getLogger(__name__)


class SequentialFlow(BaseFlow):

    component_config_schema = SequentialFlowParam
    component_provider_override = "AgentFlow.flows.SequentialFlow"

    def __init__(self, config : Union[Dict, SequentialFlowParam]):
        if isinstance(config, dict):
            self._flow_param = SequentialFlowParam(**config)
        else:
            self._flow_param = config

        self._nodes : List[BaseNode] = []
        logger.debug(f'---{self._flow_param.flow_id} {self._flow_param.flow_name} start---')
        logger.debug(json.dumps(self._flow_param.model_dump(), indent=4, ensure_ascii=False))
    
    async def before_run(self, context: Context, specific_node: list[str] = []):
        self._nodes = await self.create_node(self._flow_param)
        if context.input_func:
            for node in self._nodes:
                node.set_input_func(context.input_func)
        
        dot, graph = self._draw_flow_graph()
        self._topological_order = self._topological_sort(graph)
        self.process = None

    def _topological_sort(self, graph):
        '''拓扑排序, 根据依赖关系，确定节点执行顺序'''
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1

        # Collect nodes with zero in-degree
        zero_in_degree_queue = deque([node for node in graph if in_degree[node] == 0])

        topological_order = []
        while zero_in_degree_queue:
            node = zero_in_degree_queue.popleft()
            topological_order.append(node)

            # Decrease the in-degree of neighboring nodes
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    zero_in_degree_queue.append(neighbor)

        if len(topological_order) == len(graph):
            return topological_order
        else:
            raise ValueError("Graph has at least one cycle")


    async def run(self, context : Context, specific_node = [], flow_execute = True) -> Context:
        await self.before_run(context, specific_node)

        context.flow_description[self._flow_param.flow_id] = self._flow_param.description   
        for node_id in self._topological_order:
            if context.cancellation_token and context.cancellation_token.is_cancelled():
                logger.info(f"Flow {self.id} cancelled, stop running.")
                break

            self._draw_flow_graph(highlight_node_id=node_id)
            node = self.get_node(node_id)
            assert node is not None
            if self.should_node_run(node_id, specific_node, flow_execute):                
                await node.run(context)
            else:
                logger.info(f"Skip node {self.id}.{node_id}")
               
            context.node_output[f'{self.id}.{node_id}'] = node.get_NodeOutput()
            if self.process :
                self.process.terminate()
                self.process = None

        await self.after_run(context)

        return context

    async def run_stream(self, context: Context, specific_node: list[str] = [], flow_execute: bool = True
                         ) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage| Response | Context], None]:
        await self.before_run(context, specific_node)
        context.flow_description[self._flow_param.flow_id] = self._flow_param.description
        for node_id in self._topological_order:
            self._draw_flow_graph(highlight_node_id=node_id)
            node = self.get_node(node_id)
            assert node is not None
            if self.should_node_run(node_id, specific_node, flow_execute):
                async for msg in node.run_stream(context):
                    if isinstance(msg, (BaseChatMessage, BaseAgentEvent, Response)):
                        yield msg
                    elif isinstance(msg, Context):
                        context = msg
            else:
                logger.info(f"Skip node {self.id}.{node_id}")

            context.node_output[f'{self.id}.{node_id}'] = node.get_NodeOutput()
            if self.process:
                self.process.terminate()
                self.process = None
        await self.after_run(context)

