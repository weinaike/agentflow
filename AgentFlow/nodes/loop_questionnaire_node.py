

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage

from ..tools import extract_code_blocks
from .questionnaire_node import QuestionnaireNode
from ..data_model import AgentNodeParam, Context, AgentParam, TaskItem

from typing import Union, Dict,List
import logging
import json
logger = logging.getLogger(__name__)

from ..prompt_template import FORMATE_SYSTEM_PROMPT, FORMATE_MODIFY

class LoopQuestionnaireNode(QuestionnaireNode):
    def __init__(self, config: Union[Dict, AgentNodeParam]):
        super().__init__(config)
        self.loop_param = self.param.manager.loop
        
        param = AgentParam(name = 'planner', system_prompt = FORMATE_SYSTEM_PROMPT)
        self.planner : AssistantAgent = self.create_agent(param, self.param.llm_config)


    async def run(self, context:Context) -> None:
        tasks = await self.format_tasks(context)

        states = dict()
        summaries = dict()
        for i, task in enumerate(tasks):     
            self.param.task = task.content       
            try:                                
                response = await self.execute(context)
            except Exception as e:
                logger.error(f"Error in node {self.param.id}: {e}")            
                self.cancellation_token.cancel()

            team_state = await self.team.save_state()
            summary_state = await self.summary_agent.save_state()

            states[f'task{i}'] = {"team": team_state, "summary": summary_state}
            summaries[f'task{i}'] = {"task": task.content, "output": response.chat_message.content}

            await self.team.reset()
            await self.summary_agent.on_reset(self.cancellation_token)
        
        await self.set_LoopNodeOutput(summaries)
        
        
    async def format_tasks(self, context: Context) -> List[TaskItem]:

        dependencies_content = self.param.task

        for flow_node_id in self.loop_param.dependencies:
            if '.' not in flow_node_id:
                flow_id = self.param.flow_id
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


    async def set_LoopNodeOutput(self, summaries:Dict[str, Dict[str, str]]) -> None:        
        CONTENT_TEMPLATE = '''#### {task}\n{output}\n'''

        content = ''
        for key, val in summaries.items():
            content += CONTENT_TEMPLATE.format(task = val['task'], output = val['output'])

        with open(self.param.output.address, "w") as f:
            f.write(content)
        self.param.output.content = content
