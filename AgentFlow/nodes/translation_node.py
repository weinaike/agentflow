

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult, Response, ChatAgent, Team
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage,ToolCallSummaryMessage
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_core.models import SystemMessage, CreateResult, UserMessage
from autogen_core import CancellationToken
from .base_node import AgentNode
from .interactive_node import InteractiveNode
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


QUESTION_TEMPLATE = '''
# 当前目标是完成是完成以下任务，任务完成时，输出结束关键字。
{question}

'''

class TranslationNode(InteractiveNode):
    def __init__(self, config: Union[Dict, AgentNodeParam], context: Optional[Context] = None):
        super().__init__(config, context)
        if len(self._node_param.manager.participants) != 1:
            raise ValueError(f"TranslationNode {self._node_param.id} must have exactly one participant")

        self.agents : List[ChatAgent | Team] = []
        for name in self._node_param.manager.participants:
            found = False
            for agent_param in self._node_param.agents:
                if agent_param.name == name and agent_param.type == 'TranslationAgent':
                    self.team = self.create_agent(agent_param, self._node_param.llm_config) ## 仅单个TranslationAgent
                    found = True
                    break
            if not found:
                raise ValueError(f"Agent {name} not found in the agent list")
            

    async def execute_stream(self, context:Context) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage  | Response, None]:
        if self.team is None:
            raise ValueError("Team is not initialized")
        content = self.gen_context(context)

        cancellation_token =  context.cancellation_token if context.cancellation_token else self.cancellation_token

        print(f"\n************* {self._node_param.flow_id}.{self._node_param.id} : {self._node_param.name} execute *************", flush=True)
        result: Optional[TaskResult] = None
        for i, question in enumerate(self.questions):
            print(f"\n*************{self._node_param.flow_id}.{self._node_param.id}:question {i}*************\n", flush=True)  

            if i == 0:          
                this_task = content + QUESTION_TEMPLATE.format(question=question)
            else:
                this_task = QUESTION_TEMPLATE.format(question=question)

            async for msg in self.team.run_stream(task=this_task, cancellation_token = cancellation_token):
                if isinstance(msg, (BaseAgentEvent, BaseChatMessage)):
                    yield msg
                if isinstance(msg, TaskResult):
                    result = msg


        if self._node_param.interactive and self._input_func:
            prompt = "请输入你的问题，输入 `TERMINATE` 结束交互："
            while True:
                response = await self._input_func(prompt)
                if response.strip().upper() == "TERMINATE":
                    print("Terminating interactive session.")
                    break
                async for msg in self.team.run_stream(task=response, cancellation_token = cancellation_token):
                    if isinstance(msg, (BaseAgentEvent, BaseChatMessage)):
                        yield msg

                    if isinstance(msg, TaskResult):
                        last_msg = msg.messages[-1]
                        if isinstance(last_msg, ToolCallSummaryMessage):
                            prompt = "已经持续分析一段时间， 要继续吗？ 输入 `TERMINATE` 终止"
                        else:
                            prompt = "请输入你的下一个问题，输入 `TERMINATE` 结束交互："

            # 总结
            model_context = self.team.model_context

            summary_agent = AssistantAgent(name="summary_agent", 
                    model_client=self._model_client,             
                    system_message=SUMMARY_SYSTEM_PROMPT,
                    model_context=model_context,
                    )            

            msg = TextMessage(content=self._node_param.manager.summary_prompt, source="user")
            summary = await summary_agent.on_messages(messages=[msg], cancellation_token=cancellation_token)
            yield summary
            self.response = summary.chat_message.content
            return
        else:
            last_msg = result.messages[-1] if result else None
            last_2nd_msg = result.messages[-2] if result and len(result.messages) >=2 else None
            
            content = last_msg.content if isinstance(last_msg, TextMessage) else ""

            if len(content.strip()) < len('_I_HAVE_COMPLETED_') * 2:
                content = last_2nd_msg.content if isinstance(last_2nd_msg, TextMessage) else "" +'\n'+ content
                
                if len(content.strip()) == 0 and result and result.stop_reason:
                    # 出现异常，没有TextMessage输出， 仅有工具调用时， 则输出停止原因
                    content = result.stop_reason
            summary = Response(
                chat_message=TextMessage(
                    content=content,
                    source="assistant",
                )
            )
            yield summary
            self.response = content
            return


            