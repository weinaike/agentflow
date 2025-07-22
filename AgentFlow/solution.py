from .flows import BaseFlow, FlowFactory
from .nodes import BaseNode
from .data_model import SolutionParam, Context, LanguageEnum, get_model_config, RunParam, RepositoryParam
from .tools.utils import get_json_content
from .tools import AST, register_mcp_tools, mcp_tool_mapping
import os
import toml
import json
import logging
import re
from typing import Callable, Dict, List, Union, Sequence, Optional
from typing import AsyncGenerator
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage, UserMessage
from autogen_core.models import CreateResult
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams
from autogen_core import ComponentBase, Component, CancellationToken
from pydantic import BaseModel
from typing_extensions import Self
import traceback
logger = logging.getLogger(__name__)


def load_config(config_file: str) -> SolutionParam:
    with open(config_file, 'r') as f:
        config = f.read()
    config = toml.loads(config)

    if 'backup_dir' not in config:
        config['backup_dir'] = os.path.join(config['workspace_path'], 'cache')
    codebase = config['codebase'] if 'codebase' in config else {}
    if isinstance(codebase, str):
        config['description'] += f"\n** 项目必要信息**\n"
        config['description'] += f"** 项目代码库路径 ** : {codebase}\n"

    elif isinstance(codebase, dict):
        
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
            
        config['description'] += f"\n** 项目文件备份目录 (backup_dir) ** : {config['backup_dir']}\n"
    return SolutionParam(**config)


# Define the Solution class
class Solution(ComponentBase[BaseModel], Component[SolutionParam]):
    component_type = "solution"

    component_version = 2
    component_config_schema = SolutionParam
    component_provider_override = "AgentFlow.solution.Solution"


    def __init__(self, config_file: Union[str, SolutionParam]):    
        if isinstance(config_file, str):
            self._souluton_param = load_config(config_file)
        elif isinstance(config_file, SolutionParam):
            self._souluton_param = config_file
        else:
            raise ValueError("config_file must be a string path or an instance of SolutionParam")    

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


        llm_config = get_model_config(self._souluton_param.llm_config)
        self._model_client = OpenAIChatCompletionClient(**llm_config.model_dump())
        self._init = False
        
        self.input_func : Optional[Callable] = None

        if isinstance(self._souluton_param.codebase, RepositoryParam):
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
    def set_input_func(self, input_func: Callable):
        """
        Set the input function for the solution.
        This function will be used to get user input during the execution of the solution.
        """
        self.input_func = input_func

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

    async def run_stream(self, task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
                         cancellation_token: Optional[CancellationToken] = None,
                         specific_flow: list[str] = [], specific_node: list[str] = []
                         ) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | TaskResult | Response], None]:
        Template = '''
## 本方案的配置参数如下：
{param}

## 现在用户如下指令:
{task}

## 格式化输出
请以json格式输出需要执行的flow与node, 格式：{{flow_id:[], node_id:[]}}
 
## 请注意以下几点：
1. 如果flow_id与node_id都为空，则表示执行全部工作流与节点;
2. 如果用户没有特别指定，则默认运行全部flow与node; 
2. node_id与flow_id独立输出，不要出现'flow1_node1'这类节点ID。

'''
        if task is not None and ((len(specific_flow) == 0) or (len(specific_node) == 0)) and not self._init:        
            try:
                msg = UserMessage(content=Template.format(param = self._souluton_param, task=task), source="user")
                ret: CreateResult = await self._model_client.create(messages=[msg], json_output=True)
                print(f"根据task信息，需运行的Flow、Node: {ret.content}")
                if 'json' in ret.content:    
                    code_block_pattern = re.compile(rf'```json(.*?)```', re.DOTALL)
                    json_blocks = code_block_pattern.findall(ret.content)
                    ret.content = ''.join(json_blocks).strip()

                output = RunParam(**json.loads(ret.content))

                specific_flow = output.flow_id
                specific_node = output.node_id
                self._init = True
                logger.info(f"_model_client create Specific flows: {specific_flow}, Specific nodes: {specific_node}")
            except Exception as e:
                logger.error(f"Error during model client create: {e}\n{traceback.format_exc()}")
                yield TaskResult(
                    messages=[TextMessage(content="Error during configuring param.", source="solution")],
                    stop_reason="error",
                )
                return

        if  isinstance(specific_node, list) and len(specific_node) > 0 and \
            isinstance(specific_flow, list) and len(specific_flow) > 1:
            logger.error("Only one flow can be specified for execution")
            return
        

        context= Context(project_description=self._souluton_param.description)
        context.cancellation_token = cancellation_token
        if self.input_func:
            context.input_func = self.input_func
        try:
            for flow in self.flows:            
                if cancellation_token and cancellation_token.is_cancelled():
                    break
                if specific_flow and flow.id not in specific_flow:
                    logger.info(f"skip {flow.id}")
                    async for msg in flow.run_stream(context, specific_node=specific_node, flow_execute=False):
                        if cancellation_token and cancellation_token.is_cancelled():
                            break
                        if isinstance(msg, (BaseChatMessage, BaseAgentEvent, Response)):
                            yield msg
                        elif isinstance(msg, Context):
                            context = msg
                else:
                    logger.info(f"run {flow.id}")
                    async for msg in flow.run_stream(context, specific_node=specific_node, flow_execute=True):
                        if cancellation_token and cancellation_token.is_cancelled():
                            break
                        if isinstance(msg, (BaseChatMessage, BaseAgentEvent, Response)):
                            yield msg
                        elif isinstance(msg, Context):
                            context = msg
                    # 如果指定了特定的流程并且当前流程是其中之一，则退出循环
                    if specific_flow and flow.id in specific_flow:
                        break
        finally:
            # 可在此处添加清理逻辑，如需要
            pass
        
        yield TaskResult(
            messages=[TextMessage(content="Solution execution completed.", source="solution")],
            stop_reason= "task completed",
        )

    def _to_config(self) -> SolutionParam:
        """
        Convert the current solution to a configuration object.
        """
        flow_config = []
        for flow in self.flows:
            flow_config.append(flow._flow_param)
        self._souluton_param.flows = flow_config
        return self._souluton_param
    
    @classmethod
    def _from_config(cls, config: SolutionParam) -> Self:
        """
        Create a Solution instance from a configuration object.
        """
        return cls(config)
    
    async def register_tools(self, param: Union[StdioServerParams, StreamableHttpServerParams, SseServerParams]):
        """
        Register MCP tools for the solution.
        """

        await register_mcp_tools(param)