
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_agentchat.base import TaskResult, Response
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console

from ..tools import extract_code_blocks
from ..data_model import LoopFlowParam, Context, TaskItem, get_model_config
from .sequential_flow import SequentialFlow
from .base_flow import BaseFlow
from ..prompt_template import FLOW_DESCRIPTION_TEMPLATE, FORMATE_SYSTEM_PROMPT, FORMATE_MODIFY

import re
import os
import json
import logging
from copy import deepcopy
from typing import List, Dict, Union, Optional

logger = logging.getLogger(__name__)



class LoopFlow(BaseFlow):
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
        self.planner = AssistantAgent(name='planner', model_client=model_client, system_message = FORMATE_SYSTEM_PROMPT)

    async def run(self, context, specific_node = [], flow_execute = True) -> Context:
        tasks = await self._format_tasks(context)

        for i, task in enumerate(tasks):
            config = self._config_tranfer(self._config, f'task_{i}', task.content)
            
            seq_flow = SequentialFlow(config)

            context = await seq_flow.run(context, specific_node, flow_execute)
        
        return context
           
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