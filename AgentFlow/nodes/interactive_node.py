

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult, Response, ChatAgent, Team
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage,ToolCallSummaryMessage
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_core.models import SystemMessage, CreateResult, UserMessage
from autogen_core import CancellationToken
from .base_node import AgentNode
from .questionnaire_node import QuestionnaireNode
from ..data_model import AgentNodeParam, Context, CheckResult, AgentParam, ModelEnum, RoleTypeEnum
from ..tools.utils import get_json_content
import re
from typing import  Callable, Dict, Union, List, Optional, AsyncGenerator, Union
import logging
import json
import os
import copy
logger = logging.getLogger(__name__)

from ..prompt_template import *

class InteractiveNode(AgentNode):
    def __init__(self, config: Union[Dict, AgentNodeParam], context: Optional[Context] = None):
        super().__init__(config, context)
        self.questions = self._node_param.manager.questions

        if len(self._node_param.agents) < len(self._node_param.manager.participants):
            raise ValueError(f"AgentNode {self._node_param.id} must have at least {len(self._node_param.manager.participants)} agents")
        
        ## 依据manager中的agents字段顺序，创建多个assistant
        self.agents : List[ChatAgent | Team] = []
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
        # self.summary_agent._system_messages = [SystemMessage(content=SUMMARY_HISTORY_SYSTEM_TEMPLATE)]

    async def execute_stream(self, context:Context) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage  | Response, None]:
        if self.team is None:
            raise ValueError("Team is not initialized")
        content = self.gen_context(context)

        cancellation_token =  context.cancellation_token if context.cancellation_token else self.cancellation_token

        print(f"\n************* {self._node_param.flow_id}.{self._node_param.id} : {self._node_param.name} execute *************", flush=True)
        results : List[TaskResult] = []
        for i, question in enumerate(self.questions):
            print(f"\n*************{self._node_param.flow_id}.{self._node_param.id}:question {i}*************\n", flush=True)  

            if i == 0:          
                this_task = content + TASK_TEMPLATE.format(task=self._node_param.task, question=question)
            else:
                this_task = TASK_TEMPLATE.format(task=self._node_param.task, question=question)

            async for msg in self.team.run_stream(task=this_task, cancellation_token = cancellation_token):
                if isinstance(msg, (BaseAgentEvent, BaseChatMessage)):
                    yield msg

                if isinstance(msg, TaskResult):
                    results.append(msg) 

        prompt = "请输入你的问题，输入 `TERMINATE` 结束交互："
        while self._node_param.interactive and self._input_func:
            response = await self._input_func(prompt)
            if response.strip().upper() == "TERMINATE":
                print("Terminating interactive session.")
                break
            async for msg in self.team.run_stream(task=response, cancellation_token = cancellation_token):
                if isinstance(msg, (BaseAgentEvent, BaseChatMessage)):
                    yield msg

                if isinstance(msg, TaskResult):
                    results.append(msg)
                    last_msg = msg.messages[-1]
                    if isinstance(last_msg, ToolCallSummaryMessage):
                        prompt = "已经持续分析一段时间， 要继续吗？ 输入 `TERMINATE` 终止"
                    else:
                        prompt = "请输入你的下一个问题，输入 `TERMINATE` 结束交互："
                 
        # 总结
        msgs = []
        for result in results:
            msg = result.messages[-1]
            if isinstance(msg, (TextMessage, ToolCallSummaryMessage)):
                msgs.append(msg)

        msgs.append(TextMessage(content=self._node_param.manager.summary_prompt, source="user"))
        summary = await self.summary_agent.on_messages(messages=msgs, cancellation_token=cancellation_token)
        yield summary
        self.response = summary.chat_message.content
        return

    async def execute(self, context:Context) -> Response:
        response = await Console(self.execute_stream(context), output_stats=True)
        return response

    async def save_state(self) -> Dict:
        if self.team is None:
            return {}
        team_state = await self.team.save_state()
        summary_state = await self.summary_agent.save_state()
        state = {"team": team_state, "summary": summary_state, "response": self.response}
                
        with open(self.state_file, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=4, default=self.json_serializer)
        return state
    

    async def load_state(self) -> bool:
        if self.team is None:
            return False
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    state = json.load(f)                          
                    await self.team.load_state(state["team"])
                    await self.summary_agent.load_state(state["summary"])
                    self.response = state["response"]
                    return True
            else:
                return False
        except Exception as e:
            logger.error(f"load state error: {e}")           
            return False        