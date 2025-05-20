

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_core.models import CreateResult,UserMessage

from .base_node import AgentNode
from ..data_model import AgentNodeParam, Context, CheckResult, AgentParam, ModelEnum, RoleTypeEnum
from ..tools.utils import get_json_content
import re
from typing import Union, Dict,List
import logging
import json
import os
import copy
logger = logging.getLogger(__name__)

from ..prompt_template import TASK_TEMPLATE,CHECK_SYSTEM_PROMPT,CHECK_TEMPLATE

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
        if self.use_check:
            check_param = AgentParam(name = 'checker', system_prompt = CHECK_SYSTEM_PROMPT, model = ModelEnum.DEEPSEEKR1)
            self.check_agent = self.create_agent(check_param, self._node_param.llm_config)
            self.check_team = RoundRobinGroupChat(participants = [self.check_agent], 
                                            termination_condition = self.termination_condition,
                                            max_turns=self._node_param.manager.max_turns,
                                            ) 
        self.response:str = None
        

    async def _gen_check_result(self, history: List[ChatMessage]) -> CheckResult:

        content = f"### 当前节点工作目标：\n{self._node_param.task}\n-----\n"
        content += f"### 当前节点的预交付物内容：\n{history[-1].content}\n-----\n"
        content += f"现在需要完成以下任务：首先总结当前节点工作过程的重要内容，形成过程摘要。"
        content += f"\n然后需要根据检查清单，逐项检测当前节点工作是否符合要求。当前节点的检查清单如下：\n"
        for item in self._node_param.manager.check_items:    
            content += f"检测项{item.item_id}: {item.item_content}\n"
        content += f"最后，总结检查结果，对于不符合要求的地方，给出改进方案（代办事项）。并决定由谁完成改进方案。（对于预交付物的修改，由SummaryAgent完成，若需要更多上下文信息由ExecutionTeam完成）\n [注意：重要说明：检查与总结都围绕检查清单开展，对于不再清单内的内容不作为检查项。不需要优化]\n"
        msgs: List[ChatMessage] = []
        msgs.extend(history)
        msgs.append(TextMessage(content=content, source="user"))
        print(f"\n*************{self._node_param.flow_id}.{self._node_param.id} :check*************\n", flush=True)
        res = await Console(self.check_agent.on_messages_stream(messages=msgs, 
                                                        cancellation_token=self.cancellation_token),
                                                        output_stats=True)
        
        check_result :CheckResult = None

        content = CHECK_TEMPLATE.format(type=CheckResult.model_json_schema().__str__())        
        msgs = [UserMessage(content=res.chat_message.content,source='user'), UserMessage(content=content, source="user")]    

        while True:
            ret:CreateResult = await self._model_client.create(messages= msgs)   
            try: 
                check_result = CheckResult(**get_json_content(ret.content))  
                check_result.reason += res.chat_message.content
                break
            except Exception as e:
                logger.error(f"Error in parsing json: {e}")
                msgs.append(UserMessage(content=f"Error in parsing json: {e}, 请根据格式要求重新输出", source="user"))
        await self.check_agent.on_reset(self.cancellation_token)
        return check_result


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
                                                    cancellation_token = self.cancellation_token), 
                                                output_stats=True)
            results.append(copy.deepcopy(result)) 
            
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
            res : Response = await self.summary_agent.on_messages(messages=msgs, cancellation_token=self.cancellation_token)
            
            summary = copy.deepcopy(res)
            with open(self.state_file + f"_summary_{uuid}.md", "a") as f:
                f.write(f"# {i}\n" + summary.chat_message.content + "\n")
            print(f"\n*************{self._node_param.flow_id}.{self._node_param.id} : {i} summary *************\n{summary.chat_message.content}", flush=True)
            await self.summary_agent.on_reset(self.cancellation_token)
            msgs.append(summary.chat_message)            
            if self.use_check:
                check_result : CheckResult = await self._gen_check_result(msgs)
                
                with open(self.check_file, "a") as f:
                    f.write(check_result.model_dump_json()+"\n")

                if (check_result.result == "PASS") or i == max_iter - 1 :
                    break
                else:
                    # await self.team.reset()
                    REVISE_TEMPLATE = '''
## 当前节点工作目标：\n{task}\n
-----------------------------------------------
## 期望输出的交付物满足以下条件：\n{requirement}\n
-----------------------------------------------
## 执行团队已完成的工作摘要（详情见历史）：\n{abstract}\n
-----------------------------------------------
## 并形成当前节点的预交付物。内容如下：\n{pre_deliverables}\n
-----------------------------------------------
## 依据检查清单，检查员对预交付物逐项检查，检查结果如下：\n{check_detail}\n
-----------------------------------------------
## 接下来要完成以下工作：
根据检查反馈内容与交付物输出条件，修改预交付物内容，形成最终交付物。
'''                 
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
                        
                        result:TaskResult = await Console(self.team.run_stream(
                                                            task=this_task, 
                                                            cancellation_token = self.cancellation_token),
                                                        output_stats=True)
                        results.append(copy.deepcopy(result))
            else:
                break
            

                
        self.response = summary.chat_message.content
        return summary


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
            json.dump(state, f, ensure_ascii=False, indent=4)
        return state