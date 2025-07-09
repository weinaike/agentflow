
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import BaseGroupChat, RoundRobinGroupChat
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from autogen_core.models import CreateResult,UserMessage
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, ChatMessage, TextMessage
from ..data_model import NodeParam, AgentNodeParam, ToolNodeParam, AgentParam, NodeOutput,Context, \
    get_model_config, ModelEnum, CheckResult, NodeCheckList
from ..tools import tool_mapping, mcp_tool_mapping
from autogen_core import ComponentBase
from pydantic import BaseModel
from ..tools.utils import get_json_content
from typing import  Callable, Dict, Union, List, Optional, AsyncGenerator, Union
import os
import logging
import json
from abc import ABC, abstractmethod
logger = logging.getLogger(__name__)


from ..prompt_template import BACKGROUND_TEMPLATE, MIDDLE_TEMPLATE, CONTEXT_TEMPLATE, \
      SYSTEM_TEMPLATE, SUMMARY_SYSTEM_PROMPT, CHECK_SYSTEM_PROMPT, CHECK_TEMPLATE 


class BaseNode(ABC, ComponentBase[BaseModel]):
    component_type = "node"
    def __init__(self, config: Union[Dict, NodeParam]):
        self._node_param : NodeParam 

    def print_param(self):
        logger.info(f"----------{self._node_param.id} {self._node_param.name} param start----------")
        logger.info(json.dumps(self._node_param.model_dump(), indent=4, ensure_ascii=False))
        logger.info(f"----------{self._node_param.id} {self._node_param.name} param over--------")

    @property
    def id(self):
        return self._node_param.id

    @abstractmethod
    async def run(self, context:Context) -> None:
        pass


    @abstractmethod
    async def run_stream(self, context:Context) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage], None]:
        pass

    @abstractmethod
    async def get_NodeOutput(self) -> NodeOutput:
        pass
         
    @abstractmethod
    async def stop(self) -> None:
        pass

    def set_input_func(self, input_func: Optional[Callable]) -> None:
        """
        Set the input function for the node.
        This function will be used to get user input during the execution of the node.
        """
        self._input_func = input_func
        print("Setting input function for node")

    @staticmethod
    def json_serializer(obj):
        """JSON serializer for objects not serializable by default json code"""
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

class ToolNode(BaseNode) :    
    def __init__(self, config: Union[Dict, ToolNodeParam]):
        self._node_param : ToolNodeParam
        if isinstance(config, dict):
            self._node_param = ToolNodeParam(**config)
        else:
            self._node_param = config    
        self.print_param()

    async def execute(self, context:Context) -> Response:
        NotImplementedError("AgentNode execute method must be implemented")
        

class AgentNode(BaseNode) :  
    def __init__(self, config: Union[Dict, AgentNodeParam]):
        self.first_iteration = True
        self._node_param : AgentNodeParam
        if isinstance(config, Dict):
            self._node_param = AgentNodeParam(**config)
        else:
            self._node_param = config
        self.print_param()
        self.team: BaseGroupChat = None
        self.state_file = os.path.join(self._node_param.backup_dir, f"{self._node_param.flow_id}_{self._node_param.id}_chat_state.json")
        self.use_check = self._node_param.manager.use_check
        self.check_file = os.path.join(self._node_param.backup_dir, f"{self._node_param.flow_id}_{self._node_param.id}_check.json")

        self.temrminate_word = 'TERMINATE'
        self.cancellation_token = CancellationToken()
        self.termination_condition = TextMentionTermination(self.temrminate_word) | ExternalTermination()

        param = AgentParam(name = 'summary_agent', system_prompt = SUMMARY_SYSTEM_PROMPT)
        self.summary_agent : AssistantAgent = self.create_agent(param, self._node_param.llm_config)

        llm_config = get_model_config(config.llm_config, ModelEnum.GPT4O)
        model_client = OpenAIChatCompletionClient(**llm_config.model_dump())
        self._model_client = model_client
        
        if self.use_check:
            self.user_proxy_agent = UserProxyAgent(name='user', description='A human Checker')
            check_param = AgentParam(name = 'checker', system_prompt = CHECK_SYSTEM_PROMPT, model = ModelEnum.DEEPSEEKR1)
            self.check_agent = self.create_agent(check_param, self._node_param.llm_config)
            self.check_team = RoundRobinGroupChat(participants = [self.check_agent], 
                                            termination_condition = self.termination_condition,
                                            max_turns=self._node_param.manager.max_turns,
                                            ) 
        self.response:str = None

    def set_input_func(self, input_func: Optional[Callable]) -> None:
        """
        Set the input function for the user proxy agent.
        This function will be used to get user input during the check process.
        """
        print("Setting input function for user proxy agent")
        if hasattr(self, "user_proxy_agent") and self.user_proxy_agent:
            print("User proxy agent already exists, setting input function")
            self._input_func = input_func
            self.user_proxy_agent.input_func = input_func

    async def gen_check_result(self, history: List[ChatMessage], cancellation_token: Optional[CancellationToken] = None) -> AsyncGenerator[Union[CheckResult| BaseAgentEvent | BaseChatMessage], None]:

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
        check_response = await Console(self.check_agent.on_messages_stream(messages=msgs, 
                                                        cancellation_token=cancellation_token),
                                                        output_stats=True)
        yield check_response.chat_message
        check_result :CheckResult = None

        format_prompt = CHECK_TEMPLATE.format(type=CheckResult.model_json_schema().__str__())   

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

    async def execute(self, context:Context) -> Response:
        NotImplementedError("AgentNode execute method must be implemented")


    async def execute_stream(self, context:Context) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | TaskResult | Response], None]:
        NotImplementedError("AgentNode execute_stream method must be implemented")

    def create_agent(self, agent_param: AgentParam, llm_config_file: str) -> AssistantAgent:
        
        name = agent_param.name
        tools = None
        if len(agent_param.tools) > 0:
            tools = []
        for tool in agent_param.tools:
            if tool in mcp_tool_mapping:
                tools.append(mcp_tool_mapping[tool])
            elif tool in tool_mapping:                
                tools.append(tool_mapping[tool])
            else:
                logger.warning(f"Tool {tool} not found in tool mapping, skipping.")
        system_prompt = agent_param.system_prompt

        # create model client
        model_enum = agent_param.model
        llm_config = get_model_config(llm_config_file, model_enum)
        model_client = OpenAIChatCompletionClient(**llm_config.model_dump())
        agent = AssistantAgent(name=name, 
                               model_client=model_client, 
                               tools=tools, 
                               system_message=SYSTEM_TEMPLATE.format(system_prompt=system_prompt, keyword = self.temrminate_word),
                            #    reflect_on_tool_use = True,
                            #  model_context=BufferedChatCompletionContext(buffer_size=10),
                               )
        return agent

    @abstractmethod
    async def load_state(self) -> bool:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f) 
                    await self.summary_agent.load_state(state["summary"])
                    return True
            except Exception as e:
                logger.exception(f"Error in node {self._node_param.id}: {e}")
                return False
        else:
            return False
    @abstractmethod
    async def save_state(self) -> Dict:        
        summary_state = await self.summary_agent.save_state()
        state = {"team": None, "summary": summary_state}
        with open(self.state_file, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=4, default=self.json_serializer)
        return state
    
    def get_NodeOutput(self) -> NodeOutput:
        return self._node_param.output
    

    def gen_context(self, context:Context) -> str:
        flow_id = self._node_param.flow_id
        inputs = self._node_param.inputs

        content = ""
        if self.first_iteration:
            self.first_iteration = False #只在首次迭代开发时才提供BACKGROUND
            content = BACKGROUND_TEMPLATE.format(project_description = context.project_description, 
                                                flow_description = context.flow_description[flow_id])
        
        has_context = False
        for input in inputs:
            output : NodeOutput = None
            if '.' in input:
                fid, nid = input.split('.')
                output = context.get_node_output(fid, nid)
            else:
                output = context.get_node_output(flow_id, input)
            
            detail = output.get_content()
            if not has_context:
                content += MIDDLE_TEMPLATE
                has_context = True
            content += CONTEXT_TEMPLATE.format( node_description = output.description,
                                                detail_content = detail)

        return content
    

    async def set_NodeOutput(self, content:str) -> None:        
        with open(self._node_param.output.address, "w") as f:
            content = content.replace(self.temrminate_word, '')
            f.write(content)
        self._node_param.output.content = content
            

    async def run(self, context:Context) -> None:
        await Console(self.run_stream(context), output_stats=True)

    async def stop(self) -> None:
        self.cancellation_token.cancel()


    async def run_stream(self, context:Context) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | Response], None]:
        try:
            async for msg in self.execute_stream(context):
                if isinstance(msg, (BaseAgentEvent, BaseChatMessage, Response)):
                    yield msg

                if isinstance(msg, Response):
                    await self.set_NodeOutput(msg.chat_message.content)

        except Exception as e:
            logger.exception(f"Error in node {self._node_param.id}: {e}")
            self.cancellation_token.cancel()
        await self.save_state()