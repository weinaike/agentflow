from ..nodes import BaseNode
from ..data_model import SequentialFlowParam, Context, NodeOutput
from .base_flow import BaseFlow

from typing import List, Dict, Union
import os
import json
import logging
from graphviz import Digraph
from collections import deque
import subprocess
logger = logging.getLogger(__name__)


class SequentialFlow(BaseFlow):
    def __init__(self, config : Union[Dict, SequentialFlowParam]):
        if isinstance(config, dict):
            self._flow_param = SequentialFlowParam(**config)
        else:
            self._flow_param = config

        self._nodes : List[BaseNode] = []
        logger.debug(f'---{self._flow_param.flow_id} {self._flow_param.flow_name} start---')
        logger.debug(json.dumps(self._flow_param.model_dump(), indent=4, ensure_ascii=False))
        self._nodes = self.create_node(self._flow_param)
        logger.debug(f'---{self._flow_param.flow_id} {self._flow_param.flow_name} over---')
        dot, graph = self._draw_flow_graph()
        self._topological_order = self._topological_sort(graph)
        self.process = None

    def _draw_flow_graph(self, highlight_node_id = None):
        '''绘制流程图'''
        flow_name = self._flow_param.flow_name
        dot = Digraph(comment=flow_name)
        dot.attr(label=flow_name, labelloc='t', fontsize='20')

        # Add nodes to the graph
        for node in self._flow_param.nodes:    
            if node.id == highlight_node_id:
                dot.node(node.id, node.name, style='filled', color='lightblue')
            else:
                dot.node(node.id, node.name)
        
        graph = {node.id: [] for node in self._flow_param.nodes}
        # Add edges based on inputs
        for node in self._flow_param.nodes:
            for input_node in node.inputs:
                if input_node not in graph:
                    continue
                dot.edge(input_node, node.id)
                graph[input_node].append(node.id)
               
        file = os.path.join(self._flow_param.workspace_path, flow_name)

        # Save and render the graph
        try:
            dot.render(file, format='png', cleanup=True)
            if highlight_node_id is not None:
                self.process = subprocess.Popen(["eog", f"{file}.png"])
        except Exception as e:
            logger.error(f"Error in rendering flow graph: {e}")
        return dot, graph
    
    
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
        context.flow_description[self._flow_param.flow_id] = self._flow_param.description   
        for node_id in self._topological_order:
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


        return context
