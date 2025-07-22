from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Dict, List, Callable
from enum import Enum
from .prompt_template import CONTEXT_TEMPLATE
import json
from autogen_agentchat.base import TaskResult
from autogen_core import CancellationToken


############### llm_config  ################

class ModelEnum(str, Enum):
    DEFAULT = "gpt-4o"
    GPT4O = "gpt-4o"
    O1MINI = "o1-mini"
    CLAUDE = "claude"
    DOUBAO = "doubao"
    MINIMAX = "minimax"
    DEEPSEEKV3 = "deepseek-v3"
    DEEPSEEKR1 = "deepseek-r1"


class ModelCapabilities(BaseModel):
    vision : bool
    function_calling : bool
    json_output : bool
    structured_output : bool


class ModelConfig(BaseModel):
    model : str
    api_key : str
    base_url : str
    model_capabilities : ModelCapabilities


def get_model_config(model_config_file: str, type:ModelEnum = ModelEnum.DEFAULT) -> ModelConfig:
    with open(model_config_file, 'r') as f:
        config = f.read()
    
    model_dict : dict = json.loads(config)

    for key, value in model_dict.items():
        if key == type:
            return ModelConfig(**value)

    assert False, f"Model {type} not found in the config file {model_config_file}"


###################### 循环并发或迭代任务 ######################
class LoopModeEnum(str, Enum):
    LOOP_ITERATION = "Iteration"   # 串行执行, 有依赖关系
    LOOP_CONCURRENT = "Concurrent" # 并发执行, 无依赖关系


class LoopDependParam(BaseModel):
    dependencies: List[str]
    mode: LoopModeEnum = Field(LoopModeEnum.LOOP_ITERATION, description="Loop mode: Concurrent or Iteration")
    prompt: str = Field('', description="Prompt for the loop")

# TaskItem 用于描述 并发或迭代任务的数据格式
class TaskItem(BaseModel):
    id: int
    content: str
    status: Literal["todo", "done", "doing"] = "todo"
    result: Optional[TaskResult] = None


############### node  ################
### Define the parameters for the nodes

# define the node types
class NodeTypeEnum(str, Enum):
    TOOL = "Tool"           # 工具节点, 无代理
    AGENT = "Agent"         # 代理节点

# define the agent parameters
class AgentParam(BaseModel):
    name: str = Field(..., description="Agent ID")
    system_prompt: str  = Field(..., description="Agent System prompt")
    description: str = Field(None, description="Agent description")
    tools: list[str] = Field([], description="fucntion call for agent")
    model : ModelEnum = Field(ModelEnum.DEFAULT, description="LLM for agent")

# NodeOutput 用于描述节点的输出
class NodeOutput(BaseModel):
    description: str
    address: str 
    content: str = None
    def get_content(self) -> str:
        content = ''
        try:
            with open(self.address, 'r') as f:
                content = f.read()
                # 去掉content中包含的字符串 TERMINATE
                content = content.replace('TERMINATE', '')
        except Exception as e:
            print(f"Error in reading content file: {self.address},\n   {e}")            
        self.content = content
        return content


class NodeParam(BaseModel):   
    name: str
    id: str =  Field('node_0', pattern=r'^[A-Za-z0-9_]+$', description="Must consist of letters, numbers, and underscores only, and cannot contain '.'")
    inputs: list[str] = list()   # 节点ID
    config: str
    # 以下内容无需主动配置   
    llm_config: Optional[str] = None # 不配置则使用工作流配置
    workspace_path: Optional[str] = None # 可以不配置，默认使用工作流路径
    backup_dir: Optional[str] = None # 数据备份/缓存目录
    flow_id: Optional[str] = None
    output: Optional[NodeOutput] = None




class ToolNodeParam(NodeParam):
    type: Literal[NodeTypeEnum.TOOL]
    tools: list[str]

# 节点输出检查项
class CheckItem(BaseModel):
    item_id: int = Field(..., description="the id of the check item")
    item_content: str = Field(..., description="the content of the check item")

class CheckList(BaseModel):
    node_id: str = Field(..., description="the node id")
    check_items: List[CheckItem] = Field([], description="the check items for the node")
    summary_prompt: str = Field(..., description="该节点输出结果的总结模板提示词，要求覆盖所有的检查项，引导LLM节点输出，便于后续检查")

class NodeCheckList(BaseModel):
    nodes: List[CheckList] = Field([], description="all node check lists")

# AgentNodeParam 与 ToolNodeParam 的区别在于 AgentNodeParam 需要配置 manager 和 agents
class AgentModeEnum(str, Enum):
    Questionnaire = "Questionnaire"
    LoopQuestionnaire = "LoopQuestionnaire" # 单节点循环（迭代）问答， 即针对不同的任务， 重复执行同一个节点
    SelectorGroupChat = "SelectorGroupChat"
    SwarmGroupChat = "SwarmGroupChat"
    MagenticOne = "MagenticOne"
    ReflectiveTeam = "ReflectiveTeam"  # 反思团队模式, 需要多轮问答和总结

# ManagerParam 用于描述 AgentNodeParam 的 manager 参数
class ManagerParam(BaseModel):
    mode: AgentModeEnum
    summary_prompt: str 
    max_turns: int
    questions: list[str]
    participants: list[str]   # 代理名称, 顺序即为轮询顺序
    loop: Optional[LoopDependParam] = Field(None, description="Loop flow only")
    use_check: Optional[bool] = Field(False, description="Whether to use the check agent")
    check_items: Optional[List[CheckItem]] = Field(None, description="Check items for the node")

    # 以下仅SelectorGroupChat
    selector_prompt: Optional[str] = Field(None, description="Selector prompt for SelectorGroupChat mode")

# AgentNodeParam 用于描述 Agent工作节点的完整参数
class AgentNodeParam(NodeParam):
    task: str   
    # 以下内容对 Tool 节点无需配置
    type: Literal[NodeTypeEnum.AGENT]
    manager : ManagerParam
    agents : List[AgentParam] = list()   


class RunParam(BaseModel):
    flow_id: List[str] = Field([], description="工作流ID列表, 需要执行的工作流ID, 如果为空则执行所有工作流")
    node_id: List[str] = Field([], description="节点ID列表, 需要执行的节点ID, 如果为空则执行所有节点")


############# 上下文传递 ################

# Context 用于描述工作流的上下文
class Context(BaseModel):
    project_description: str
    flow_description: Dict[str,str] = dict()
    node_output: Dict[str, NodeOutput] = dict()
    input_func: Optional[Callable] = None  # 输入函数，用于获取用户输入
    cancellation_token: Optional[CancellationToken] = None
    
    def get_node_output(self, flow_id : str, node_id: str) -> NodeOutput:
        key = f'{flow_id}.{node_id}'
        return self.node_output.get(key, None)
    
    def get_node_content(self, flow_id : str, node_id: str) -> str:
        key = f'{flow_id}.{node_id}'
        output = self.node_output.get(key, None)
        if output:
            content = output.get_content()
            return CONTEXT_TEMPLATE.format(node_description = output.description,
                                           detail_content = content)
        return None

    class Config:
        arbitrary_types_allowed = True


############### flow  ################

## Define the flow types
class FlowTypeEnum(str, Enum):
    SEQUENTIAL = "SEQUENTIAL"
    AUTOSCHED  = "AUTOSCHED"
    CONDITIONAL = "CONDITIONAL"
    SEQUENTIALLOOP = "SEQUENTIALLOOP"
    AUTOSCHEDLOOP = "AUTOSCHEDLOOP"


## Define the parameters for the flow node
class flowNodeParam(BaseModel):
    flow_name: str
    flow_id: str
    config: str
    previous_flows: List[str] = list()
    workspace_path: str = None 
    backup_dir: str = None # 数据备份/缓存目录
    llm_config: str = None # 模型配置文件路径  
    

## Define the parameters for the flow
class flowDetailParam(flowNodeParam):
    flow_type: FlowTypeEnum
    description: str
    nodes: List[NodeParam]        
  
class SequentialFlowParam(flowDetailParam):
    pass

## Define the parameters for the loop flow
class LoopFlowParam(flowDetailParam):
    loop: LoopDependParam  # Add attributes specific to loop flows

class AutoSchedParam(BaseModel):
    max_sched_times: int
    start_node_id: str
    sched_prompt: str

class AutoSchedFlowParam(SequentialFlowParam):
    auto_sched: AutoSchedParam

## Define the parameters for the condition flow
class ConditionFlowParam(flowDetailParam):
    condition: str  # Add attributes specific to condition flows

############### workflow  ################

class LanguageEnum(str, Enum):
    C = "C"
    CPP = "C++"
    PYTHON = "Python"
    JAVA = "Java"
    GO = "Go"
    RUST = "Rust"
    SWIFT = "Swift"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    KOTLIN = "Kotlin"
    SCALA = "Scala"
    RUBY = "Ruby"
    PHP = "PHP"
    CSHARP = "C#"
    OBJECTIVEC = "Objective-C"
    SHELL = "Shell"
    OTHER = "Other"

class RepositoryParam(BaseModel):
    language: LanguageEnum = LanguageEnum.PYTHON
    project_path: str                               # 代码仓库路径
    source_path: str                                # 源码路径
    header_path: Optional[Union[str,List[str]]] = None     # 头文件路径
    build_path: str = None                          # 编译路径
    namespace: Optional[Union[str,List[str]]] = None      # 命名空间

class SolutionParam(BaseModel):
    project_name: str
    project_id: str
    description: str    # 项目描述，针对整个项目的描述，具体的需求在requirement中描述
    workspace_path: str
    llm_config: str
    codebase: Union[RepositoryParam, str]
    flows: List[Union[flowDetailParam, flowNodeParam]] = []
    backup_dir: str = None # 数据备份/缓存目录
    requirement: Optional[str] = None   # 项目需求描述，用于替换工作流描述中的{requirement}
    requirement_flow: Optional[List[str]] = None # 需求对应的工作流ID
    def get_flow_param(self, flow_id: str) -> flowNodeParam:
        for flow in self.flows:
            if flow.flow_id == flow_id:
                return flow
        return None
    

class CheckTypeEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"

class RoleTypeEnum(str, Enum):
    ExecustionTeam = "ExecustionTeam"
    SummaryAgent = "SummaryAgent"
class CheckResult(BaseModel):
    result: CheckTypeEnum = Field(..., description="任务完成情况的总体结论")
    reason: str  = Field(..., description="the reason for the result, if failed, give the reason and the suggestion")
    abstract: str = Field(..., description="总结任务处理过程的重要信息形成过程摘要")
    todo: List[str] = Field([], description="改进代办事项")
    next_role: RoleTypeEnum = Field(RoleTypeEnum.SummaryAgent, description="下一步角色, 用于指示下一步的处理角色。角色选择依据。 SummaryAgent无法使用工具，仅能输出结果，ExecustionTeam可以使用工具获取环境的反馈")


