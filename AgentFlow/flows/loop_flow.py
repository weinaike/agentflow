
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_agentchat.base import TaskResult, Response
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

from ..tools import extract_code_blocks
from ..data_model import LoopFlowParam, Context, TaskItem, get_model_config
from .sequential_flow import SequentialFlow
from .auto_sched_flow import AutoSchedFlow
from .base_flow import BaseFlow
from ..prompt_template import FLOW_DESCRIPTION_TEMPLATE, FORMAT_SYSTEM_PROMPT, FORMATE_MODIFY

import re
import os
import json
import logging
from copy import deepcopy
from typing import  Dict, Union, List, Optional, AsyncGenerator, Union

logger = logging.getLogger(__name__)

class LoopFlow(BaseFlow):

    component_config_schema = LoopFlowParam
    component_provider_override = "AgentFlow.flows.LoopFlow"

    def __init__(self, config : Union[Dict, LoopFlowParam]):
        if isinstance(config, dict):
            self._flow_param = LoopFlowParam(**config)
            self._config = config
        else:
            self._flow_param = config
            self._config = self._flow_param.model_dump()
        self.loop_param = self._flow_param.loop
       
        llm_config = get_model_config(self._flow_param.llm_config)
        model_client = OpenAIChatCompletionClient(**llm_config.model_dump())
        #self.tasks_file = os.path.join(self._node_param.backup_dir, f"{self._node_param.flow_id}_{self._node_param.id}_tasks.json")
        self.tasks_file = os.path.join(self._config["backup_dir"], f"{self._flow_param.flow_id}_loop_tasks.json")
        self.planner = AssistantAgent(name='planner', model_client=model_client, system_message = FORMAT_SYSTEM_PROMPT)

    def create_internal_flow(config) -> BaseFlow:
        raise NotImplementedError("override this method in the subclass please!")

    async def run(self, context, specific_node = [], flow_execute = True) -> Context:
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file) as f:
                tasks = [TaskItem(**obj) for obj in json.load(f)]
        else:        
            tasks = await self._format_tasks(context)
            self._update_tasks(tasks)

        for i, task in enumerate(tasks):
            if task.status == 'done':
                continue
            config = self._config_tranfer(self._config, f'task_{i}', task.content)
            
            flow:BaseFlow = self.create_internal_flow(config)

            context = await flow.run(context, specific_node, flow_execute)
        
        return context 
     
    def _update_tasks(self, tasks) -> None:
        with open(self.tasks_file, 'w') as f:
            json.dump([task.model_dump() for task in tasks], f, indent=4, ensure_ascii=False)
           
    def _config_tranfer(self, flow_config: Dict, loop_key:str, loop_val:str) -> Dict:
        config = deepcopy(flow_config)
        # 由上层传入的参数覆盖配置文件中的参数
        config['workspace_path'] = str(os.path.join(flow_config['workspace_path'], loop_key))
        config['flow_id'] = flow_config['flow_id'] + '_' + loop_key
        config['description'] = FLOW_DESCRIPTION_TEMPLATE.format(
                                    flow_description = flow_config['description'],
                                    goals = loop_val
                                    )

        return config

        
    async def _format_tasks(self, context: Context) -> List[TaskItem]:

        dependencies_content = self.loop_param.prompt

        for flow_node_id in self.loop_param.dependencies:
            if '.' not in flow_node_id:
                flow_id = self._flow_param.flow_id
                node_id = flow_node_id
            else:
                flow_id, node_id = flow_node_id.split('.')
            dependencies_content += context.get_node_content(flow_id, node_id)

        msgs = [TextMessage(content = dependencies_content, source= 'user') ,
                ]
        
        tasks : List[TaskItem] = []
        i = 0
        while i < 5:
            i += 1
            respond : Response = await Console(self.planner.on_messages_stream(
                                        messages=msgs, 
                                        cancellation_token=CancellationToken())
                                    )
            try:
                json_str = extract_code_blocks(respond.chat_message.content, "json")
                parsed_json = json.loads(json_str)
                tasks.extend([TaskItem(**obj) for obj in parsed_json])
                break
            except Exception as e:
                logger.error(f"Error in parsing json: {e}")
                msgs = [TextMessage(content = FORMATE_MODIFY.format(error_log = f'{e}'), source= 'user')]
        
        if len(tasks) == 0:
            raise ValueError("No task generated")

        return tasks    
    
    async def run_stream(self, context, specific_node = [], flow_execute = True
                         ) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | Context], None]:
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file) as f:
                tasks = [TaskItem(**obj) for obj in json.load(f)]
        else:
            tasks = await self._format_tasks(context)
            self._update_tasks(tasks)
        for i, task in enumerate(tasks):
            if context.cancellation_token and context.cancellation_token.is_cancelled():
                logger.info(f"Flow {self.id} cancelled, stop running.")
                break
            if task.status == 'done':
                continue
            config = self._config_tranfer(self._config, f'task_{i}', task.content)
            
            flow:BaseFlow = self.create_internal_flow(config)

            async for msg in flow.run_stream(context, specific_node, flow_execute):
                if isinstance(msg, (BaseChatMessage, BaseAgentEvent)):
                    yield msg
                elif isinstance(msg, Context):
                    context = msg


class SequentialLoopFlow(LoopFlow):
    def create_internal_flow(self, config):
        return SequentialFlow(config)

class AutoSchedLoopFlow(LoopFlow):
    def create_internal_flow(self, config):
        return AutoSchedFlow(config)