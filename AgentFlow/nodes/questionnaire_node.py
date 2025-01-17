

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage

from .base_node import AgentNode
from ..data_model import AgentNodeParam, Context

from typing import Union, Dict,List
import logging
import json
import os
logger = logging.getLogger(__name__)

from ..prompt_template import TASK_TEMPLATE

class QuestionnaireNode(AgentNode):
    def __init__(self, config: Union[Dict, AgentNodeParam]):
        super().__init__(config)
        self.questions = self._node_param.manager.questions
        if len(self.questions) == 0:
            raise ValueError("QuestionnaireNode must have at least one question")

        if len(self._node_param.agents) < len(self._node_param.manager.participants):
            raise ValueError(f"AgentNode {self._node_param.id} must have at least {len(self._node_param.manager.participants)} agents")
        
        ## 依据manager中的agents字段顺序，创建多个assistant
        self.agents : List[AssistantAgent] = []
        for name in self._node_param.manager.participants:             
            found = False
            for agent_param in self._node_param.agents:
                if agent_param.name == name:
                    agent = self.create_agent(agent_param, self._node_param.llm_config)
                    self.agents.append(agent)
                    found = True
                    break
            if not found:
                raise ValueError(f"Agent {name} not found in the agent list")

        self.team = RoundRobinGroupChat(participants = self.agents, 
                                        termination_condition = self.termination_condition,
                                        max_turns=self._node_param.manager.max_turns,
                                        ) 
        
        self.response:str = None

    async def execute(self, context:Context) -> Response:
        content = self.gen_context(context)

        print(f"\n************* {self._node_param.flow_id}.{self._node_param.id} : {self._node_param.name} execute *************", flush=True)
        results : List[TaskResult] = []
        for i, question in enumerate(self.questions):
            print(f"\n*************{self._node_param.flow_id}.{self._node_param.id} :question {i}*************\n", flush=True)  
            this_task = ''
            if i == 0:          
                this_task = content + TASK_TEMPLATE.format(task=self._node_param.task, question=question)
            else:
                this_task = TASK_TEMPLATE.format(task=self._node_param.task, question=question)
            result:TaskResult = await Console(self.team.run_stream(
                                                    task=this_task, 
                                                    cancellation_token = self.cancellation_token)
                                                , output_stats=True)
            results.append(result)

        msgs : List[ChatMessage] = []
        for result in results:
            for msg in result.messages:
                if msg.type in ['TextMessage', 'ToolCallSummaryMessage']:
                    msgs.append(msg)

        msgs.append(TextMessage(content=self._node_param.manager.summary_prompt, source="user"))
        summary : Response = await Console(self.summary_agent.on_messages_stream(
                                                messages=msgs, 
                                                cancellation_token=self.cancellation_token)
                                            )
        
        self.response = summary.chat_message.content
        return summary


    async def load_state(self) -> bool:
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    state = json.load(f)                
                    await self.team.load_state(state["team"])
                    await self.summary_agent.load_state(state["summary"])
                    self.response = Response(ChatMessage(content=state["response"], source="assistant"))
                    return True
            else:
                return False
        except Exception as e:
            logger.error(f"load state error: {e}")
            return False    
            
    async def save_state(self) -> Dict:
        team_state = await self.team.save_state()
        summary_state = await self.summary_agent.save_state()
        state = {"team": team_state, "summary": summary_state, "response": self.response}
        with open(self.state_file, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        return state