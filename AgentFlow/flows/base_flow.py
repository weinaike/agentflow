from ..data_model import flowDetailParam, Context
from ..nodes import NodeFactory, BaseNode


import os
from graphviz import Digraph
import subprocess
import toml
import logging
from abc import ABC, abstractmethod
from typing import  Dict, Union, List, Optional
logger = logging.getLogger(__name__)

class BaseFlow(ABC):
    def __init__(self, config: Union[Dict, flowDetailParam]):
        self._flow_param: flowDetailParam 
        self._nodes: List[BaseNode] 

       
    @abstractmethod
    async def run(self, context: Context, specific_node: list[str] = [], flow_execute : bool = True) -> Context:
        pass

    def should_node_run(self, node_id :str, specific_node: list[str] = [], flow_execute : bool = True) -> bool:
        if flow_execute:
            if specific_node and node_id not in specific_node:
                return False
            else:
                return True
        else:
            return False            

    @property
    def id (self) -> str:
        return self._flow_param.flow_id
    
    
    def get_node(self, node_id: str) -> BaseNode:
        for node in self._nodes:
            if node.id == node_id:
                return node
        return None

    def create_node(self, flow_param: flowDetailParam) -> List[BaseNode]:
        nodes : List[BaseNode] = []

        if not os.path.exists(flow_param.workspace_path):
            os.makedirs(flow_param.workspace_path)

        for node in flow_param.nodes:
            node.workspace_path = flow_param.workspace_path
            node.backup_dir = flow_param.backup_dir
            node.llm_config = flow_param.llm_config
            node.flow_id = flow_param.flow_id

            config_path = os.path.dirname(flow_param.config)
            config_file = os.path.join(config_path, node.config)
            with open(config_file, 'r') as f:
                node_config = f.read()
            try:
                node_config = toml.loads(node_config)
                node_type = node_config['type']
                node_config.update(node.model_dump())
                node_config['output'] = {"address": os.path.join(node.workspace_path, node.config.replace('toml', 'md')),
                                          "description": node.name}                                          
                nodes.append(NodeFactory.create_node(node_type, node_config))

            except Exception as e:
                print(f"Error in reading config file: {config_file}, {e}")
                raise e
        return nodes

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