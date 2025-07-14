

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage, UserMessage
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_core.models import SystemMessage, CreateResult
from autogen_core import CancellationToken
from .base_node import AgentNode
from .questionnaire_node import QuestionnaireNode
from ..data_model import AgentNodeParam, Context, CheckResult, AgentParam, ModelEnum, RoleTypeEnum
from ..tools.utils import get_json_content
import re
from typing import  Dict, Union, List, Optional, AsyncGenerator, Union
import logging
import json
import os
import copy
logger = logging.getLogger(__name__)

from ..prompt_template import *
      
class ReflectiveNode(QuestionnaireNode):
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
        self.summary_agent._system_messages = [SystemMessage(content=SUMMARY_HISTORY_SYSTEM_TEMPLATE)]



    async def _format_summary(self, check_response: Response, cancellation_token: Optional[CancellationToken] = None) -> AsyncGenerator[Union[CheckResult| BaseAgentEvent | BaseChatMessage], None]:
 
        ## 检查结果格式化
        check_result :CheckResult = None
        format_prompt = CHECK_TEMPLATE.format(type=CheckResult.model_json_schema().__str__())   
        msgs = []
        if hasattr(self, "_input_func") and self._input_func:
            print("Setting input function for user proxy agent")
            msg = TextMessage(content=f"## 内置checker检查结果:\n{check_response.chat_message.content}\n请提供你的建议......\n", source='user')
            yield msg
            human_response:Response = await self.user_proxy_agent.on_messages(messages=[msg], cancellation_token=cancellation_token)
       
            msgs = [UserMessage(content=check_response.chat_message.content,source='user'), 
                    UserMessage(content=human_response.chat_message.content, source="user"),
                    UserMessage(content=format_prompt, source="user")]    
        else:
            print("No input function set for user proxy agent, using default format prompt")
            yield check_response.chat_message
            msgs = [UserMessage(content=check_response.chat_message.content,source='user'), 
                    UserMessage(content=format_prompt, source="user")]
        
        while True:
            ret:CreateResult = await self._model_client.create(messages= msgs)   
            try: 
                check_result = CheckResult(**get_json_content(ret.content))  
                check_result.reason += check_response.chat_message.content
                break
            except Exception as e:
                logger.error(f"Error in parsing json: {e}")
                msgs.append(UserMessage(content=f"Error in parsing json: {e}, 请根据格式要求重新输出", source="user"))
        await self.check_agent.on_reset(self.cancellation_token)
        yield check_result
        return


    async def execute_stream(self, context:Context) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage  | Response], None]:
        content = self.gen_context(context)

        cancellation_token =  context.cancellation_token if context.cancellation_token else self.cancellation_token

        print(f"\n************* {self._node_param.flow_id}.{self._node_param.id} : {self._node_param.name} execute *************", flush=True)
        results : List[TaskResult] = []
        max_iter = 3
        questions = self.questions
        summary : Response = None
        for iter in range(max_iter):
            for i, question in enumerate(questions):
                print(f"\n*************{self._node_param.flow_id}.{self._node_param.id} iter:{iter}/{max_iter} :question {i}*************\n", flush=True)  

                if i == 0:          
                    this_task = content + TASK_TEMPLATE.format(task=self._node_param.task, question=question)
                    if iter > 0:
                        this_task = f"历史执行记录：\n{summary.chat_message.content}\n\n" + this_task
                else:
                    this_task = TASK_TEMPLATE.format(task=self._node_param.task, question=question)

                async for msg in self.team.run_stream(task=this_task, cancellation_token = cancellation_token):
                    if isinstance(msg, (BaseAgentEvent, BaseChatMessage)):
                        yield msg

                    if isinstance(msg, TaskResult):
                        results.append(msg) 
            
            msgs : List[ChatMessage] = []
            for result in results:                
                for msg in result.messages:
                    if msg.type in ['TextMessage', 'ToolCallSummaryMessage']:
                        msgs.append(msg)
            msgs.append(TextMessage(content=SUMMARY_USER_PROMPT, source="user"))
            summary = await self.summary_agent.on_messages(messages=msgs, cancellation_token=cancellation_token)


            await self.team.reset()
            results.clear()
            questions = []

            if self.use_check and iter < max_iter - 1:
                async for out in self._format_summary(summary, cancellation_token=cancellation_token):
                    if isinstance(out, CheckResult):
                        if out.result == 'PASS':
                            logger.info(f"Check result: {out.result}, no need to revise")
                            break
                        questions = ['\n'.join(out.todo)]
                    else:
                        yield out
            else:
                break
        self.response = summary.chat_message.content
        yield summary
        return
