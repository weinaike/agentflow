

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage

from ..tools import extract_code_blocks
from .questionnaire_node import QuestionnaireNode
from .base_node import AgentNode
from ..data_model import AgentNodeParam, Context, AgentParam, TaskItem, LoopModeEnum

from typing import Union, Dict,List, Tuple
import logging
import json
import os
import copy
import asyncio
logger = logging.getLogger(__name__)

from ..prompt_template import FORMATE_SYSTEM_PROMPT, FORMATE_MODIFY


async def execute_task(i:int, task:TaskItem, context:Context, node_param:AgentNodeParam) -> Tuple[Dict[str, str], Response]:
    new_param = copy.deepcopy(node_param)
    new_param.task = task.content
    new_param.id += f'task{i}'
    seq_node = QuestionnaireNode(new_param)

    try:
        response = await seq_node.execute(context)
    except Exception as e:
        logger.error(f"Error in node {node_param.id}: {e}")
        seq_node.stop()
        return None, None

    team_state = await seq_node.save_state()
    
    return team_state, response



class LoopQuestionnaireNode(AgentNode):
    def __init__(self, config: Union[Dict, AgentNodeParam]):
        super().__init__(config)
        self._node_param : AgentNodeParam
        if isinstance(config, Dict):
            self._node_param = AgentNodeParam(**config)
        else:
            self._node_param = config

        self._loop_param = self._node_param.manager.loop
        
        param = AgentParam(name = 'planner', system_prompt = FORMATE_SYSTEM_PROMPT)
        self.planner : AssistantAgent = self.create_agent(param, self._node_param.llm_config)
        self.tasks_file = os.path.join(self._node_param.backup_dir, f"{self._node_param.flow_id}_{self._node_param.id}_tasks.json")
        

    async def run(self, context:Context) -> None:
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'r') as f:
                tasks = [TaskItem(**obj) for obj in json.load(f)]
        else:
            tasks = await self._format_tasks(context)
            self._update_task(tasks)

        states = dict()
        summaries = dict()
        results : List[Tuple[Dict[str, str], Response]] = []

        if self._loop_param.mode == LoopModeEnum.LOOP_ITERATION:
            for i, task in enumerate(tasks):
                results.append(await execute_task(i, task, context, self._node_param))
        else:
            tasks_to_run = []
            for i, task in enumerate(tasks):
                tasks_to_run.append(asyncio.create_task(execute_task(i, task, context, self._node_param)))

            results = await asyncio.gather(*tasks_to_run)

        for result, task in zip(results, tasks):
            if result[0] is None :
                task.status = 'error'
                states[f'task{i}'] = 'error'
                summaries[f'task{i}'] = {"task": task.content, "output": 'error'}
                continue
            states[f'task{i}'] = result[0]
            if isinstance(result[1],Response):
                summaries[f'task{i}'] = {"task": task.content, "output": result[1].chat_message.content}
                task.status = 'done'
            else:
                task.status = 'todo'
        self._update_task(tasks)
        
        await self._set_LoopNodeOutput(summaries)
        #await self._set_state(states)

    def _update_task(self, tasks: List[TaskItem]) -> None:
        with open(self.tasks_file, 'w') as f:
            json.dump([task.model_dump() for task in tasks], f, indent=4, ensure_ascii=False)
        
    async def _format_tasks(self, context: Context) -> List[TaskItem]:

        dependencies_content = self._node_param.task

        for flow_node_id in self._loop_param.dependencies:
            if '.' not in flow_node_id:
                flow_id = self._node_param.flow_id
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
                                        cancellation_token=self.cancellation_token)
                                    )
            try:
                json_str = extract_code_blocks(respond.chat_message.content, "json")
                parsed_json = json.loads(json_str)
                tasks.extend([TaskItem(**obj) for obj in parsed_json])
                break
            except Exception as e:
                logger.exception(f"Error in parsing json: {e}")
                msgs = [TextMessage(content = FORMATE_MODIFY.format(error_log = f'{e}'), source= 'user')]
        
        if len(tasks) == 0:
            raise ValueError("No task generated")

        return tasks


    async def _set_LoopNodeOutput(self, summaries:Dict[str, Dict[str, str]]) -> None:        
        CONTENT_TEMPLATE = '''#### {task}\n{output}\n'''

        content = ''
        for key, val in summaries.items():
            content += CONTENT_TEMPLATE.format(task = val['task'], output = val['output'])

        with open(self._node_param.output.address, "w") as f:
            f.write(content)
        self._node_param.output.content = content

