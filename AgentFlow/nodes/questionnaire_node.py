

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from .base_node import AgentNode
from ..data_model import AgentNodeParam, Context, CheckResult, AgentParam, ModelEnum, RoleTypeEnum

import re
from typing import  Dict, Union, List, Optional, AsyncGenerator, Union
import logging
import json
import os
import copy
logger = logging.getLogger(__name__)

from ..prompt_template import TASK_TEMPLATE,REVISE_TEMPLATE
      
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

    async def execute(self, context:Context) -> Response:
        response = await Console(self.execute_stream(context), output_stats=True)
        return response

    async def load_state(self) -> bool:
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
            
    async def save_state(self) -> Dict:
        team_state = await self.team.save_state()
        summary_state = await self.summary_agent.save_state()
        state = {"team": team_state, "summary": summary_state, "response": self.response}
                
        with open(self.state_file, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=4, default=self.json_serializer)
        return state
    

    
    async def execute_stream(self, context:Context) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | TaskResult | Response], None]:
        content = self.gen_context(context)

        cancellation_token =  context.cancellation_token if context.cancellation_token else self.cancellation_token

        print(f"\n************* {self._node_param.flow_id}.{self._node_param.id} : {self._node_param.name} execute *************", flush=True)
        results : List[TaskResult] = []
        for i, question in enumerate(self.questions):
            print(f"\n*************{self._node_param.flow_id}.{self._node_param.id} :question {i}*************\n", flush=True)  
            this_task = ''
            if i == 0:          
                this_task = content + TASK_TEMPLATE.format(task=self._node_param.task, question=question)
            else:
                this_task = TASK_TEMPLATE.format(task=self._node_param.task, question=question)
            async for msg in self.team.run_stream(task=this_task, cancellation_token = cancellation_token):
                if isinstance(msg, (BaseAgentEvent, BaseChatMessage)):
                    yield msg

                if isinstance(msg, TaskResult):
                   results.append(copy.deepcopy(msg)) 

        summary : Response = None

        # 生成随机的uuid字符串
        uuid = re.sub(r'[^a-zA-Z0-9]', '', str(os.urandom(16)))
        max_iter = 3
        revise_msg = ''
        for i in range(max_iter):
            msgs : List[ChatMessage] = []
            for result in results:
                for msg in result.messages:
                    if msg.type in ['TextMessage', 'ToolCallSummaryMessage']:
                        msgs.append(msg)

            if i == 0:
                msgs.append(TextMessage(content=self._node_param.manager.summary_prompt, source="user"))
            else:
                if revise_msg == '':
                    msgs.append(TextMessage(content=self._node_param.manager.summary_prompt, source="user"))
                else:
                    msgs.append(TextMessage(content=revise_msg, source="user"))
            res : Response = await self.summary_agent.on_messages(messages=msgs, cancellation_token=cancellation_token)
            
            summary = copy.deepcopy(res)
            yield summary.chat_message
            with open(self.state_file + f"_summary_{uuid}.md", "a") as f:
                f.write(f"# {i}\n" + summary.chat_message.content + "\n")
            print(f"\n*************{self._node_param.flow_id}.{self._node_param.id} : {i} summary *************\n{summary.chat_message.content}", flush=True)
            await self.summary_agent.on_reset(cancellation_token)
            msgs.append(summary.chat_message)            
            if self.use_check:                
                check_result : CheckResult = None
                async for out in self.gen_check_result(msgs, cancellation_token=cancellation_token):
                    if isinstance(out, (BaseAgentEvent, BaseChatMessage)):
                        yield out
                    if isinstance(out, CheckResult):
                        check_result = out
                
                with open(self.check_file, "a") as f:
                    f.write(check_result.model_dump_json()+"\n")

                if (check_result.result == "PASS") or i == max_iter - 1 :
                    break
                else:
                    # await self.team.reset()
                    
                    revise_msg = REVISE_TEMPLATE.format(task = self._node_param.task,
                                                        requirement = self._node_param.manager.summary_prompt,
                                                        abstract = check_result.abstract,
                                                        pre_deliverables = summary.chat_message.content,
                                                        check_detail = check_result.reason)
                    if check_result.next_role == RoleTypeEnum.SummaryAgent:
                        continue

                    for j, todo in enumerate(check_result.todo):
                        this_task = ''
                        if j == 0:
                            this_task += f"## 当前节点工作目标：\n{self._node_param.task}\n------\n"
                            this_task += f"## 已执行的过程摘要：\n{check_result.abstract}\n------\n"
                            this_task += f"## 期望输出的交付物满足以下条件：\n{self._node_param.manager.summary_prompt}\n------\n"
                            this_task += f"## 已取得结果：\n{summary.chat_message.content}\n------\n"
                            this_task += f"## 检查项验证结果：\n{check_result.result}\n------\n"
                            this_task += f"## 检查详情：\n{check_result.reason}\n------\n"
                            this_task += f"为达成任务目标，执行了以下代办事项：\n{todo}\n"
                        else:
                            this_task += f"## 检查详情：\n{check_result.reason}\n------\n"
                            this_task += f"为达成任务目标，还需执行了以下代办事项：\n{todo}\n"

                        async for msg in self.team.run_stream(task=this_task,cancellation_token=cancellation_token):
                            if isinstance(msg, (BaseAgentEvent, BaseChatMessage)):
                                yield msg
                            
                            if isinstance(msg, TaskResult):
                                results.append(copy.deepcopy(msg))
            else:
                break

        self.response = summary.chat_message.content
        yield summary
        return