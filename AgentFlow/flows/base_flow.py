from ..data_model import flowDetailParam, Context
from ..nodes import NodeFactory, BaseNode


import os
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
