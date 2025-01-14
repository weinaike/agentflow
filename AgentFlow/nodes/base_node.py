
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import BaseGroupChat
from autogen_core import CancellationToken
from autogen_agentchat.base import TaskResult, Response

from ..data_model import NodeParam, AgentNodeParam, ToolNodeParam, AgentParam, NodeOutput,Context, get_model_config
from ..tools import tool_mapping

from typing import Union, Dict, List
import os
import logging
import json
from abc import ABC, abstractmethod
logger = logging.getLogger(__name__)


from ..prompt_template import BACKGROUND_TEMPLATE, MIDDLE_TEMPLATE, CONTEXT_TEMPLATE, SYSTEM_TEMPLATE, SUMMARY_SYSTEM_PROMPT


class BaseNode(ABC) : 
    def __init__(self, config: Union[Dict, NodeParam]):
        self.param : NodeParam 

    def print_param(self):
        logger.info(f"----------{self.param.id} {self.param.name} param start----------")
        logger.info(json.dumps(self.param.model_dump(), indent=4, ensure_ascii=False))
        logger.info(f"----------{self.param.id} {self.param.name} param over--------")

    @property
    def id(self):
        return self.param.id

   
    @abstractmethod
    async def execute(self, context:Context) -> Response:
        print("BaseNode execute")
        pass

    @abstractmethod
    async def run(self, context:Context) -> None:
        pass

    @abstractmethod
    async def load_state(self) -> None:
        pass

    @abstractmethod
    async def save_state(self) -> Dict:
        pass

    @abstractmethod
    async def get_NodeOutput(self) -> NodeOutput:
        pass

    @abstractmethod
    def gen_context(self, context:Context) -> str:
        pass

    @abstractmethod
    async def set_NodeOutput(self, content:str) -> None:
        pass

class ToolNode(BaseNode) :    
    def __init__(self, config: Union[Dict, ToolNodeParam]):
        self.param : ToolNodeParam
        if isinstance(config, dict):
            self.param = ToolNodeParam(**config)
        else:
            self.param = config    
        self.print_param()

    async def execute(self, context:Context) -> Response:
        print("ToolNode execute")
        

class AgentNode(BaseNode) :  
    def __init__(self, config: Union[Dict, AgentNodeParam]):
        self.param : AgentNodeParam
        if isinstance(config, Dict):
            self.param = AgentNodeParam(**config)
        else:
            self.param = config
        self.print_param()
        self.team: BaseGroupChat
        self.state_file = os.path.join(self.param.backup_dir, f"{self.param.flow_id}_{self.param.id}_chat_state.json")

        self.temrminate_word = 'TERMINATE'
        self.cancellation_token = CancellationToken()
        self.termination_condition = TextMentionTermination(self.temrminate_word) | ExternalTermination()

        param = AgentParam(name = 'summary_agent', system_prompt = SUMMARY_SYSTEM_PROMPT)
        self.summary_agent : AssistantAgent = self.create_agent(param, self.param.llm_config)
    
    async def execute(self, context:Context) -> Response:
        print("AgentNode execute")
        

    def create_agent(self, agent_param: AgentParam, llm_config_file: str) -> AssistantAgent:
        
        name = agent_param.name
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
                            #  model_context=BufferedChatCompletionContext(buffer_size=10),
                               )
        return agent
    
    async def load_state(self) -> None:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                state = json.load(f)                
                await self.team.load_state(state["team"])
                await self.summary_agent.load_state(state["summary"])
            
    async def save_state(self) -> Dict:
        team_state = await self.team.save_state()
        summary_state = await self.summary_agent.save_state()
        state = {"team": team_state, "summary": summary_state}
        with open(self.state_file, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)

    
    def get_NodeOutput(self) -> NodeOutput:
        return self.param.output
    
    def gen_context(self, context:Context) -> str:
        flow_id = self.param.flow_id
        inputs = self.param.inputs

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
        with open(self.param.output.address, "w") as f:
            content = content.replace(self.temrminate_word, '')
            f.write(content)
        self.param.output.content = content
            

    async def run(self, context:Context) -> None:
        try:
            response =  await self.execute(context)
            await self.set_NodeOutput(response.chat_message.content)
        except Exception as e:
            logger.exception(f"Error in node {self.param.id}: {e}")            
            self.cancellation_token.cancel()
        await self.save_state()

