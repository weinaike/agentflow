from .flows import BaseFlow, FlowFactory
from .nodes import BaseNode
from .data_model import SolutionParam, Context, LanguageEnum
from .tools import AST
import os
import toml
import json
import logging
from typing import Dict, List


logger = logging.getLogger(__name__)


def load_config(config_file: str) -> SolutionParam:
    with open(config_file, 'r') as f:
        config = f.read()
    config = toml.loads(config)

    codebase = config['codebase']
    config['description'] += f"\n\n** 项目必要信息**"
    if 'language' in codebase:
        config['description'] += f"** language ** : {codebase['language']}\n"
    if 'project_path' in codebase:
        config['description'] += f"** 项目路径 ** : {codebase['project_path']}\n"
    if 'source_path' in codebase:
        config['description'] += f"** 源码目录 ** : {codebase['source_path']}\n"
    if 'header_path' in codebase:
        config['description'] += f"** 头文件目录 ** : {codebase['header_path']}\n"
    if 'build_path' in codebase:
        config['description'] += f"** 编译与构建目录 ** : {codebase['build_path']}\n"
    if 'namespace' in codebase:
        config['description'] += f"** 命名空间 ** : {codebase['namespace']}\n"

    if 'backup_dir' not in config:
        config['backup_dir'] = os.path.join(config['workspace_path'], 'cache')
    config['description'] += f"\n** 项目文件备份目录 (backup_dir) ** : {config['backup_dir']}\n"
    return SolutionParam(**config)


# Define the Solution class
class Solution:
    def __init__(self, config_file: str):        
        self._souluton_param = load_config(config_file)

        os.makedirs(self._souluton_param.workspace_path, exist_ok=True)
        os.makedirs(self._souluton_param.backup_dir, exist_ok=True)

        self.flows : List[BaseFlow] = []
        for flow in self._souluton_param.flows:                
            with open(flow.config, 'r') as f:
                flow_config = f.read()
            flow_config = toml.loads(flow_config)
            flow_config.update(flow.model_dump())
            flow_config['workspace_path'] = os.path.join(self._souluton_param.workspace_path, flow.flow_id)
            flow_config['llm_config'] = self._souluton_param.llm_config
            flow_config['backup_dir'] = self._souluton_param.backup_dir
            if self._souluton_param.requirement_flow is not None and len(self._souluton_param.requirement_flow) > 0:
                if flow.flow_id in self._souluton_param.requirement_flow:
                    flow_config['description'] =  flow_config['description'].format(requirement = self._souluton_param.requirement) 
            flow_type = flow_config['flow_type'] 
            self.flows.append(FlowFactory.create_flow(flow_type, flow_config))  
        ## BaseModel 日志打印
        logger.info('-----------------Workflows-----------------')
        logger.info(json.dumps(self._souluton_param.model_dump(), indent=4, ensure_ascii=False))
        logger.info('-----------------Workflows-----------------')

        if self._souluton_param.codebase:
            if self._souluton_param.codebase.language == LanguageEnum.CPP:

                src = self._souluton_param.codebase.source_path
                
                include = []
                if isinstance(self._souluton_param.codebase.header_path, list):
                    include = self._souluton_param.codebase.header_path
                elif isinstance(self._souluton_param.codebase.header_path, str):
                    include = [self._souluton_param.codebase.header_path]
                else:
                    include = []
                namespaces = []
                if isinstance(self._souluton_param.codebase.namespace, list):
                    namespaces = self._souluton_param.codebase.namespace
                elif isinstance(self._souluton_param.codebase.namespace, str):
                    if self._souluton_param.codebase.namespace == '':
                        namespaces = []
                    else:
                        namespaces = [self._souluton_param.codebase.namespace]
                else:
                    namespaces=[]
                cache_file = f'{self._souluton_param.backup_dir}/{self._souluton_param.project_id}'
                ast = AST()
                dir_list = [src]
                if include:
                    dir_list.extend(include)
                output_filters =  [
                    lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
                ]
                ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=output_filters, cache_file=cache_file, load=True)

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
        context= Context(project_description=self._souluton_param.description)
        for flow in self.flows:            
            if specific_flow and flow.id not in specific_flow:
                logger.info(f"skip {flow.id}")
                context = await flow.run(context, specific_node=specific_node, flow_execute=False)
            else:
                logger.info(f"run {flow.id}")
                context = await flow.run(context, specific_node=specific_node)
                if specific_flow and flow.id in specific_flow:
                    break

