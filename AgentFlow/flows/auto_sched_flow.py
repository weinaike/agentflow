
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console

from ..tools import extract_code_blocks
from ..data_model import LoopFlowParam, AutoSchedFlowParam, Context, TaskItem, get_model_config, NodeOutput
from .base_flow import BaseFlow
from ..nodes import BaseNode
from ..prompt_template import FLOW_DESCRIPTION_TEMPLATE, FORMAT_SYSTEM_PROMPT, FORMATE_MODIFY

import re
import os
import json
import logging
from copy import deepcopy
from typing import  Dict, Union, List, Optional, AsyncGenerator, Union

logger = logging.getLogger(__name__)

class AutoSchedFlow(BaseFlow):
    def __init__(self, config: Union[Dict, AutoSchedFlowParam]):
        if isinstance(config, dict):
            self._flow_param = AutoSchedFlowParam(**config)
        else:
            self._flow_param = config

        self._nodes : List[BaseNode] = []  

    async def before_run(self, context: Context, specific_node: list[str] = []):
        self._nodes = await self.create_node(self._flow_param)
        if context.input_func:
            for node in self._nodes:
                node.set_input_func(context.input_func)
        self._start_node_id = self._flow_param.auto_sched.start_node_id
        self._sched_prompt  = self._flow_param.auto_sched.sched_prompt
        self._max_sched_times = self._flow_param.auto_sched.max_sched_times

        _, graph = self._draw_flow_graph()      
        

    async def run(self, context: Context, specific_node=[], flow_execute=True) -> Context:
        await self.before_run(context, specific_node)

        context.flow_description[self._flow_param.flow_id] = self._flow_param.description  
        node_id = self._start_node_id
        node = self.get_node(node_id)
        for i in range(self._max_sched_times):
            self._draw_flow_graph(highlight_node_id=node_id)
            await node.run(context)
            if self.process:
                self.process.terminate()
                self.process = None
            output = node.get_NodeOutput()
            context.node_output[f'{self.id}.{node_id}'] = output

            # select the next running node and its inputs
            node_id, inputs = await self.auto_sched(node_id, output)
            if node_id == 'QUIT':
                break
            node = self.get_node(node_id)
            node._node_param.inputs = inputs
            #static_node = [node for node in self._flow_param.nodes if node.id == node_id][0]
            #static_node.inputs = inputs

        await self.after_run(context)

        return context    

    async def auto_sched(self, node_id, node_output: NodeOutput):
        dialog = node_output.get_content()
        content = f"以下是节点{node_id}的执行情况：\n{dialog}"
        
        llm_config = get_model_config(self._flow_param.llm_config)
        msgs = [TextMessage(content=content, source="user")]   
        next_to_run, inputs = "QUIT", []
        for _ in range(5):
            model_client = OpenAIChatCompletionClient(**llm_config.model_dump())
            assistant = AssistantAgent(name='scheduler', model_client=model_client, system_message = self._sched_prompt) 
            response = await Console(assistant.on_messages_stream(messages=msgs, cancellation_token=CancellationToken()))
            try:
                json_str = extract_code_blocks(response.chat_message.content, "json")
                sched_info = json.loads(json_str)
                next_to_run = sched_info["next_to_run"]
                inputs = sched_info["inputs"]
                break
            except:
                next_to_run, inputs = "QUIT", []

        return next_to_run, inputs
    

    async def run_stream(self, context: Context, specific_node: list[str] = [], flow_execute: bool = True
                          ) -> AsyncGenerator[Union[BaseAgentEvent, BaseChatMessage, Context], None]:
        await self.before_run(context, specific_node)

        context.flow_description[self._flow_param.flow_id] = self._flow_param.description  
        node_id = self._start_node_id
        node = self.get_node(node_id)
        for i in range(self._max_sched_times):
            if context.cancellation_token and context.cancellation_token.is_cancelled():
                logger.info(f"Flow {self.id} cancelled, stop running.")
                break
            self._draw_flow_graph(highlight_node_id=node_id)
            async for msg in node.run_stream(context):
                if isinstance(msg, (BaseChatMessage, BaseAgentEvent)):
                    yield msg
                elif isinstance(msg, Context):
                    context = msg

            if self.process:
                self.process.terminate()
                self.process = None
            output = node.get_NodeOutput()
            context.node_output[f'{self.id}.{node_id}'] = output

            # select the next running node and its inputs
            node_id, inputs = await self.auto_sched(node_id, output)
            if node_id == 'QUIT':
                break
            node = self.get_node(node_id)
            node._node_param.inputs = inputs

        await self.after_run(context)