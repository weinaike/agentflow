from .flows import BaseFlow, FlowFactory
from .nodes import BaseNode
from .data_model import WorkflowsParam, Context

import os
import toml
import json
import logging
from typing import Dict, List
# Configure logging
import asyncio
import argparse

logger = logging.getLogger(__name__)


def load_config(config_file: str) -> WorkflowsParam:
    with open(config_file, 'r') as f:
        config = f.read()
    config = toml.loads(config)
    if 'backup_dir' not in config:
        config['backup_dir'] = os.path.join(config['workspace_path'], 'cache')
    config['description'] += f"\n** 项目文件备份目录 (backup_dir) ** : {config['backup_dir']}\n"
    return WorkflowsParam(**config)


# Define the workflows class
class Workflows:
    def __init__(self, config_file: str):        
        self.param = load_config(config_file)

        os.makedirs(self.param.workspace_path, exist_ok=True)
        os.makedirs(self.param.backup_dir, exist_ok=True)

        self.flows : List[BaseFlow] = []
        for flow in self.param.flows:                
            with open(flow.config, 'r') as f:
                flow_config = f.read()
            flow_config = toml.loads(flow_config)
            flow_config.update(flow.model_dump())
            flow_config['workspace_path'] = os.path.join(self.param.workspace_path, flow.flow_id)
            flow_config['llm_config'] = self.param.llm_config
            flow_config['backup_dir'] = self.param.backup_dir
            flow_type = flow_config['flow_type'] 
            self.flows.append(FlowFactory.create_flow(flow_type, flow_config))  
        ## BaseMdeol 日志打印
        logger.info('-----------------Workflows-----------------')
        logger.info(json.dumps(self.param.model_dump(), indent=4, ensure_ascii=False))
        logger.info('-----------------Workflows-----------------')

    def get_previous_flow_nodes(self, flow_nodes: List[str]) -> Dict[str, BaseNode]:

        depend_nodes = {}
        for flow in self.flows:
            for flow_node in flow_nodes:
                flow_id, node_id = flow_node.split('.')
                if flow.id == flow_id:
                    node = flow.get_node(node_id)
                    if node:
                        depend_nodes[flow_node] = node
                    else:
                        logger.error(f"Node {flow_node} not found in flow {flow_id}")
                else:
                    continue
        return depend_nodes
                 
    ## 执行完整流程
    async def run(self, specific_flow: list[str] = [], specific_node: list[str] = []):
        if  isinstance(specific_node, list) and len(specific_node) > 0 and \
            isinstance(specific_flow, list) and len(specific_flow) > 1:
            logger.error("Only one flow can be specified for execution")
            return
        context= Context(project_description=self.param.description)
        for flow in self.flows:            
            if specific_flow and flow.id not in specific_flow:
                logger.info(f"skip {flow.id}")
                context = await flow.run(context, specific_node=specific_node, flow_execute=False)
            else:
                logger.info(f"run {flow.id}")
                context = await flow.run(context, specific_node=specific_node)

