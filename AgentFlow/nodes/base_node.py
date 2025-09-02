
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import BaseGroupChat
from autogen_core import CancellationToken
from autogen_agentchat.base import TaskResult, Response

from ..data_model import NodeParam, AgentNodeParam, ToolNodeParam, AgentParam, NodeOutput,Context, get_model_config, ModelEnum
from ..tools import tool_mapping
from ..tools.utils import JsonHandler

from typing import Union, Dict, List
import os
import logging
import json
from abc import ABC, abstractmethod
logger = logging.getLogger(__name__)


from ..prompt_template import BACKGROUND_TEMPLATE, MIDDLE_TEMPLATE, CONTEXT_TEMPLATE, SYSTEM_TEMPLATE, SUMMARY_SYSTEM_PROMPT


class BaseNode(ABC) : 
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
    async def get_NodeOutput(self) -> NodeOutput:
        pass
         
    @abstractmethod
    async def stop(self) -> None:
        pass
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
    

    async def execute(self, context:Context) -> Response:
        NotImplementedError("AgentNode execute method must be implemented")
        

    def create_agent(self, agent_param: AgentParam, llm_config_file: str) -> AssistantAgent:
        
        name = agent_param.name
        tools = None
        if len(agent_param.tools) > 0:
            tools = []
        for tool in agent_param.tools:
            tools.append(tool_mapping[tool])
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
            json.dump(state, f, ensure_ascii=False, indent=4, cls=JsonHandler)
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
        try:
            response =  await self.execute(context)
            await self.set_NodeOutput(response.chat_message.content)
        except Exception as e:
            logger.exception(f"Error in node {self._node_param.id}: {e}")            
            self.cancellation_token.cancel()
        await self.save_state()

    async def stop(self) -> None:
        self.cancellation_token.cancel()
