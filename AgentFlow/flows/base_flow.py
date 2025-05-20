from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import Response
from autogen_agentchat.ui import Console

from ..data_model import flowDetailParam, Context, get_model_config, ModelEnum, NodeCheckList
from ..nodes import NodeFactory, BaseNode
from ..tools.utils import get_json_content

import os
from graphviz import Digraph
import subprocess
import toml
import logging
from abc import ABC, abstractmethod
from typing import  Dict, Union, List, Optional
import json  # Add this import for using json.dumps
logger = logging.getLogger(__name__)

class BaseFlow(ABC):
    def __init__(self, config: Union[Dict, flowDetailParam]):
        self._flow_param: flowDetailParam 
        self._nodes: List[BaseNode] 

    async def before_run(self, context: Context, specific_node: list[str] = []):
        pass

    async def after_run(self, context: Context):
        pass 
       
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

    async def create_node(self, flow_param: flowDetailParam) -> List[BaseNode]:

        prompt = f'## 工作流 {flow_param.flow_id} : {flow_param.flow_name} \n本工作流的职责:{flow_param.description}\n'
        nodes : List[BaseNode] = []

        if not os.path.exists(flow_param.workspace_path):
            os.makedirs(flow_param.workspace_path)


        node_configs : List[Dict] = []
        prompt += f'## 工作流节点\n本工作流包含以下{len(flow_param.nodes)}个节点:\n'
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
                node_config.update(node.model_dump())
                node_config['output'] = {"address": os.path.join(node.workspace_path, node.config.replace('toml', 'md')),
                                          "description": node.name}  
                prompt += f"### {node.id} {node.name}\n- 节点职责:{node_config['task']}\n- 节点执行结果的总结提示词：'''{node_config['manager']['summary_prompt']}'''\n\n"
                node_configs.append(node_config)

            except Exception as e:
                print(f"Error in reading config file: {config_file}, {e}")
                raise e
        
        
        nodechecklist:NodeCheckList = None

        checklist_file_path = os.path.join(flow_param.backup_dir, f'{flow_param.flow_id}_checklist.json')
        if os.path.exists(checklist_file_path):
            with open(checklist_file_path, 'r') as f:
                nodechecklist = NodeCheckList(**json.loads(f.read()))
        else:
            prompt += f"问题1：若要对每个节点设置检查清单。具体的检查项内容是什么？\n问题2：参考各节点的检查项内容，改进各节点的总结提示词\n"
            format_prompt = f"将以上结果以json格式输出。```json\ncontent\n```,具体各内容字段要求：{NodeCheckList.model_json_schema().__str__()}\n请特别注意字段规则，特别是引号规则，避免json解析出错的情况"

            
            llm_config = get_model_config(flow_param.llm_config, ModelEnum.GPT4O)
            model_client = OpenAIChatCompletionClient(**llm_config.model_dump())
            agent = AssistantAgent(name='Designer', model_client=model_client)
            await Console(agent.on_messages_stream([TextMessage(content=prompt, source = 'user')],CancellationToken()) )

            
            msg = TextMessage(content=format_prompt, source = 'user')
            for i in range(3):            
                response:Response = await Console(agent.on_messages_stream([msg], CancellationToken()))
                try:        
                    data = get_json_content(response.chat_message.content)
                    nodechecklist = NodeCheckList(**data)
                    break
                except Exception as e:
                    print(f"Error in parsing json: {e}")
                    msg = TextMessage(content = f"Error in parsing json: {e} ,follow format requrirement,retry again ", source= 'user')
            with open(checklist_file_path, 'w') as f:
                f.write(json.dumps(nodechecklist.model_dump(), indent=4, ensure_ascii=False))  # Use json.dumps instead of nodechecklist.json()
            
        
        for node_config in node_configs:
            for node_check in nodechecklist.nodes:
                if node_check.node_id == node_config['id']:
                    node_config['manager']['summary_prompt'] = node_check.summary_prompt
                    node_config['manager']['check_items'] = node_check.check_items
                    break
            
            nodes.append(NodeFactory.create_node(node_config['type'], node_config))


            with open(os.path.join(flow_param.backup_dir,node_config['config']), 'w') as f:
                f.write(toml.dumps(node_config))

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