# AgentFlow智能体工作流配置指南

## 1. 引言

### 1.1 目的与概述

    AgentFlow 是一个创新且高效的 Python 框架，专为用户提供精细化的智能体工作流解决方案。其设计目的是通过配置文件的形式，帮助用户快速构建和管理复杂的工作流体系，实现任务的自动化和高效执行。AgentFlow 支持灵活多变的工作流控制，包括顺序、循环等复杂流程组合，且通过提供多样化且可扩展的节点类型，使用户能够灵活应对不同的应用场景。框架的高度扩展性允许用户自定义工作流组件以满足特定需求，从而提升智能体任务执行的效率和稳定性，为项目开发带来显著的增益。

### 1.2 适用对象

    本项目适用于以下几类用户：

1. **开发者与工程师**：希望将智能体（Agent）工作流用于产品开发的技术人员。无论是初学者还是有经验的开发者，AgentFlow框架提供的详细文档和示例项目有助于快速掌握如何通过配置文件构建高效的智能体工作流。
2. **技术架构师**：负责设计系统架构的专业人员，他们需要构建灵活且可扩展的工作流系统以满足特定业务需求。通过AgentFlow，架构师可以直观地管理流（Flow）和节点（Node），定制复杂的流程逻辑。
3. **研究人员与学生**：对人工智能和自动化感兴趣的学术群体，他们能够通过该框架探索智能体执行自动化任务的最新技术和方案。

## 2. 基础概念

### 2.1 AgentFlow 概括介绍

  AgentFlow是一种用于定义、组织和管理复杂任务的结构化系统，系统将复杂任务进行分解拆分，具体到每个节点，仅负责特定的、简单的任务。这使得节点中的智能体(Agent)能够稳定得开展工作。这种组织模式主要是基于以下因素：

- **LLM快思考模式**：导致其推理能力有限， 难以处理复杂任务
- **有限得上下文窗口**：复杂任务往往需要大量的上下文、容易超过LLM的输入窗口
- **提高上下文质量**：简单任务，工具使用更加精准，更加容易获取高质量上下文

#### 2.2 AgentFlow 源码目录结构

1. **data_model.py** - 定义项目中用到的数据模型，是数据结构与其操作的定义中心。
2. **flows/** - 包含实现各类工作流逻辑的模块。

   -**base_flow.py** - 提供工作流的基础结构和功能，是所有特定工作流的基类，提供基本功能和接口。

   - **loop_flow.py** - 实现需要重复执行的循环工作流，是复杂任务重复执行的关键模块。
   - **sequential_flow.py** - 顺序执行的工作流实现，用于线性任务流程。
3. **main.py** - 主程序入口，负责项目的初始化和启动流程。
4. **nodes/** - 定义和实现工作流中的不同节点逻辑。

   -**base_node.py** - 基础节点类型，是节点的基础抽象类，定义所有节点的模板和接口。

   - **loop_questionnaire_node.py** - 循环问卷节点，实现循环问卷逻辑的节点，用于动态任务调整。
   - **questionnaire_node.py** - 问卷节点，定义标准问卷逻辑节点。
5. **prompt_template.py** - 提供用于构建和管理命令提示框架的模板，支持交互界面功能。
6. **tools/** - 包含辅助工具集，用于支持项目的开发及运行时管理。

    -**abstract_syntax_tree.py** - 操作和分析代码语法树的工具。
    - **code_tool.py, file_edit.py, file_tool.py** - 提供文件和代码操作的细化功能，文件操作相关的功能。
    - **shell_tool.py, uml_tool.py** - 提供脚本执行和UML相关的工具。
    - **utils.py** - 通用工具方法。
  7. **work_flow.py** - 负责整体工作流的调度和执行。

### 2.3 工作流的基本组件

#### 2.3.1 工作流（`WorkFlow`）

`WorkFlow` 复杂组织与调度 `Flow` 完成服务工作, 其定义在 **work_flow.py** 文件中

#### 2.3.1 流（`Flow`）

`Flow`定义了任务之间的逻辑关系，是工作流的骨架，决定任务执行的顺序、并发与条件转移等机制。

- **实现位置**：集中在 `flows`目录下供用户定义。
- **流的相关设计**
  - **BaseFlow**是流的基础抽象类，提供通用的流操作，如节点的创建、流的执行、和节点的选择逻辑。
    - **属性**：
      - `param`: 包含流的配置参数。
      - `nodes`: 包含流中的节点集合。
    - **关键方法**：
      - `run`: 异步执行流，用于启动流的执行。
      - `create_node`: 根据配置创建节点集合，初始化流所需的节点。
  - **子类实现**：不同类型的流可以继承BaseFlow，实现各自的逻辑，如顺序、循环或条件流等。

#### 2.3.2 节点（`Node`）

Node是工作流的基本构成部分，每个节点通常承担单一功能实现，如数据处理或任务决策。

- **实现位置**：具体实现位于 `nodes`目录中，适应新的功能需求。
- 节点的设计
  - **BaseNode**是节点的基础抽象类，定义了节点的核心接口，所有具体节点类型都需实现这些接口。
    - **属性**：
      - `param`: 包含节点的配置参数。
    - **关键方法**：
      - `execute`: 执行节点的主要逻辑，实现节点内的具体任务。
      - `run`: 负责节点的实际运行和处理。
      - `load_state` 和 `save_state`: 处理节点状态载入与存储，支持中断恢复及状态持久化（待实现）。
  - **典型子类**：
    - **ToolNode**：用于封装和执行工具操作的节点（待实现）。
    - **AgentNode**：专注于智能体交互及复杂操作，支持状态管理和上下文生成。

## 3. 配置详解

### 3.1 配置文件格式

#### 3.1.1 文件格式

TOML (Tom's Obvious, Minimal Language) 是一种专门用于编写配置文件的格式，选择TOML的最重要的原因是：**支持长文本与跨行文本有利于prompt描述**。当然它同时也支持丰富的数据类型与易于解析等特点

#### 3.1.2 配置文件的组织和结构

配置文件被组织为模块化和可理解的结构，以路径 `agentflow/workflows/cuda_migration`为例进行说明。工作流包括以下几个部分：

- **总的配置文件**：**根目录下放置**：`workflows.toml`， 用于定义整个工作流的基本信息和流程顺序。它协调不同的流，以实现完整的工作流执行。
- **工作流配置**：**每个子目录**（如 `flow1_architect_understand`, `flow2_solution` 等）对应一个工作流阶段（Flow），
- **节点配置**：（如 `node1_business_analysis.toml`）描述在具体工作流过程中每个节点的详细任务，其与流配置文件处于同一目录
- **高级选项配置**：调试选项、日志等级等（待开发）。

示例项目目录结构说明

```
/cuda_migration
├── flow1_architect_understand			# 主要处理架构理解的流程，
│   ├── flow_architect_understand.toml		# 定义总体流程配置
│   ├── node1_business_analysis.toml		# 各种节点配置文件，如 `node1_business_analysis.toml`, `node2_CoreModule.toml`，这些节点配置具体的任务和目标。
│   ├── node2_CoreModule.toml
│   ├── node3_SingleClassUML.toml
│   ├── node4_MultiClassUML.toml
│   └── node5_SystemArchitect.toml
├── flow2_solution				# 负责迁移方案设计
│   ├── flow_solution.toml
│   └── node1_Solution.toml
├── flow3_task_decomposition			# 负责任务分解
│   ├── flow_task_decomposition.toml
│   └── node8_config_taskPlan.toml
├── flow4_task_execution			# 负责执行具体任务
│   ├── flow_task_execution.toml
│   ├── node1_config_QueryCode.toml
│   ├── node2_config_genCode.toml
│   ├── node3_config_editCode.toml
│   └── node4_config_debugCode.toml
└── workflows.toml				# 为项目提供整体的工作流配置，并链接其他细化的配置文件。
```

### 3.2 各配置文件说明

#### **3.2.1 总配置文件**

总配置文件的数据结构

```python
class RepositoryParam(BaseModel):
    language: LanguageEnum = LanguageEnum.PYTHON
    project_path: str                               # 代码仓库路径
    source_path: str                                # 源码路径
    header_path: Optional[Union[str,List[str]]] = None     # 头文件路径
    build_path: str = None                          # 编译路径
    namespace: Optional[Union[str,List[str]]] = None      # 命名空间

class WorkflowsParam(BaseModel):
    project_name: str
    project_id: str
    description: str
    workspace_path: str
    llm_config: str
    codebase: RepositoryParam
    flows: List[flowNodeParam]
    backup_dir: str = None # 数据备份/缓存目录
```

**`workflows.toml`**：总配置文件，包含字段如下

- `project_name`、`project_id`、`description`、`workspace_path`、`llm_config`: 定义项目的基本信息
- `codebase`：定义工作流项目所要分析处理的的目标代码库信息，
  - `language`、`project_path`、`source_path` 必填
- `flows`：定义具体的工作流信息， 可以定义多个工作流
  - `flow_name`、`flow_id`、`config`、`previous_flows`必填

```toml
project_name = "GalSim光子射击算法CUDA加速" 	# "项目名称"
project_id = "project_1"                  	# "项目标识符"
description = """
Galsim是一个用于模拟天体光学成像的项目。它的亮度模型SBprofie通过光学仿真构建ImageView图像。亮度模型仿真渲染的方法主要包括三种：1. 离散傅里叶变换渲染 2. 实空间直接渲染 3. 光子射击
"""

workspace_path = "workspace/test"         #"工作空间的文件路径" 
llm_config = "docs/OAI_CONFIG_LIST.json"  #"大语言模型相关的配置文件路径"

[codebase]
language = "C++"                          		#"使用的编程语言（如：Python, C++等）" 
project_path = "/home/wnk/code/GalSim/"      		#"项目的根目录路径" 
source_path = "/home/wnk/code/GalSim/src/"      	#"源代码存放路径"
header_path = "/home/wnk/code/GalSim/include/galsim/"   #"C/C++项目的头文件路径"
build_path = "/home/wnk/code/GalSim/build/"        	#"构建工程输出的路径"
namespace = "galsim"          				# "命名空间（通常用于组织代码）"

[[flows]]
flow_name = "结构理解"    				# "流程名称（例如：架构分析）"
flow_id = "flow1"         				# "唯一标识的流程ID"
config = "workflows/cuda_migration/flow1_architect_understand/flow_architect_understand.toml"    #"流程的配置文件路径"
previous_flows = []    										 #"依赖的前置流程ID"
```

#### **3.2.2 Flow配置文件**

Flow的配置数据结构

```python
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
  
```

在流配置文件中，需要详细定义每个节点以及它们之间的关系。主要字段如下：

- `flow_name` 、 `description` 、 `flow_type`字段必填
- **工作流类型(flow_type)：** 当前支持两种，`SEQUENTIAL`与 `LOOP`
  - 对于 `LOOP`类型的工作流，需要额外配置 loop 字段， 包含三个 键值对， dependencies,  mode, prompt
- `nodes` ：定义该工作所包含的节点，即节点之间的上下游关系
  - `id`、`name`、`inputs`、`config` 必填
  - `config`：指定具体节点配置文件，其与流文件同目录

以下是 `flow1_architect_understand.toml`的详细结构：

```toml
flow_name = "结构理解"
flow_type = "SEQUENTIAL" #  "SEQUENTIAL" or "LOOP"
description = """
### 结构理解流程
该流程的目的是帮助架构师
1. 分析业务，理解项目的主要功能；
2. 提炼实现核心功能的主要类或者模块，分析类或模块之间的关系；
3. 提炼实现核心业务的主要流程，及其涉及的相关内容。
"""
# LOOP 类型工作流，需要配置以下 loop 字段
# [loop]
# dependencies = ['flow3.node8']	# 需要遍历循环的内容所在的节点
# mode = "Iteration"	# 当前仅支持"Iteration", 即循环迭代， 后续考虑支持 "Concurrent"，即并发模式
# prompt = "将需要迁移的模块，根据要求格式化输出，形成任务列表， 便于后续遍历执行。每个子任务请详细描述任务内容"  # 用于将上游节点的任务， 转化为格式化列表的提示词，便于循环执行

[[nodes]]
id = "node1"
name = "业务分析"
inputs = []
config = "node1_business_analysis.toml"

[[nodes]]
id = "node2"
name = "核心模块"
inputs = []
config = "node2_CoreModule.toml"

[[nodes]]
id = "node3"
name = "单核心类UML"
inputs = ["node2"]
config = "node3_SingleClassUML.toml"

[[nodes]]
id = "node4"
name = "多核心类UML"
inputs = ["node2"]
config = "node4_MultiClassUML.toml"

[[nodes]]
id = "node5"
name = "系统架构"
inputs = ["node1", "node3", "node4"]
config = "node5_SystemArchitect.toml"
```

#### **3.2.3 Node节点配置说明**

节点的配置数据结构

```python
# define the node types
class NodeTypeEnum(str, Enum):
    TOOL = "Tool"           # 工具节点, 无代理
    AGENT = "Agent"         # 代理节点

# define the agent parameters
class AgentParam(BaseModel):
    name: str  
    system_prompt: str
    description: str = None
    tools: list[str] = []   
    model : ModelEnum = ModelEnum.DEFAULT

class NodeParam(BaseModel):   
    name: str
    id: str =  Field('node_0', pattern=r'^[A-Za-z0-9_]+$', description="Must consist of letters, numbers, and underscores only, and cannot contain '.'")
    inputs: list[str] = list()   # 节点ID
    config: str
    # 以下内容无需主动配置   
    llm_config: str = None # 不配置则使用工作流配置
    workspace_path: str = None # 可以不配置，默认使用工作流路径   
    backup_dir: str = None # 数据备份/缓存目录  
    flow_id: str = None   
    output: Optional[NodeOutput] = None

```

节点文件（如 `node1_business_analysis.toml`）则详细罗列了执行该节点时所需的信息，字段包含如下

* **`type`**：当前仅支持Agent模式， 后续扩展Tool模式
* **`task`** :  描述当前节点的任务目标
* **`manager`**：管理节点内Agent的对话进程。
  * `max_turns`： 每个话题最长对话次数
  * `participants`： 表示参与话题的智能体
    * 单个智能体，将持续发言，直到问题解答完毕或者对话次数达到上限
    * 多个智能体：对于单个话题，将依次发言， 直到问题解答或者对话次数达到上限。（该处对话次数表示轮次，所有智能体发言一次算一轮）
  * `mode`： 当前支持 `Questionnaire` 与 `LoopQuestionnaire` 两种模式
    * `Questionnaire`： 围绕着task， 依次向智能体询问questions中所列的内容
    * `LoopQuestionnaire`：一般用于需要处理多个上游事项的场景，比如上游输出多个业务分析需求，本节点需依次独立分析，
      * 该模式下，将生效 `manager.loop`字段， `manager.loop.dependencies`字段 必须提供
      * 内置的智能体，将结合 `manager.loop.prompt`， `manager.loop.dependencies` 与 `task`，三种的信息， 形成待处理任务列表
      * 任务的执行与Questionnaire模式相同，也是依次向 `participants`所定义的参与的智能体询问 `questions`中所列的内容
      * 最后会将任务列表与每个任务的处理结果汇总输出
  * `questions` : 即需要智能体提交的话题
  * `summary_prompt` : 对 `questions`中的话题进行对话的所有内容进行总结。
* **`agents`**：定义节点参与的智能体， 可以是一个或者多个。
  * `name`、`system_prompt`字段必要的，定义智能体特性
  * `tools`：根据需要选填内容, 可以配置一个多种多个工具函数
  * `model`：该字段默认为 `gpt-4o` 若需指定，可选范围参考 `ModelEnum`， 具体参数由 `llm_config`配置提供的配置文件配置

```toml

type = "Agent"			# 当前仅支持Agent模式， 后续扩展Tool模式
task = "总体了解项目，熟悉项目的核心业务， 归纳实现业务的主要方法与流程"

# 最好能够有文档支撑
[manager]
max_turns = 5
mode = 'Questionnaire'		# 当前支持 'Questionnaire' 与 'LoopQuestionnaire' 两种模式
participants = ["assistant"]
questions = [
    "该算法库的总体介绍",
    "该算法库的主要功能介绍，其输入是什么？ 输出是什么? 中间包含哪些过程",
    "主要业务流程介绍",
]
summary_prompt = '整理以上内容，形成详细且丰富的业务分析文档'

# 仅在LoopQuestionnaire模式下有效
#[manager.loop]
#dependencies = ["node2"]
#mode = "Iteration"
#prompt = ''


[[agents]]
name = "assistant"
tools = [ "read_file_content", ] # 需要用到的工具
system_prompt = '''
你是一个资深的软件开发文档专家，擅长分析和总结复杂的软件系统，能够以简洁而清晰的语言为用户介绍软件仓库相关的内容。
你的回答应该适合初学者和有经验的开发者，帮助他们快速了解项目的背景、业务逻辑和主要功能。
'''

```

节点配置重点需要关注以下几点：

* `agents.system_prompt`: 其体现Agent的能力偏向
* `manager.questions`: 引导问题解决，使得工作更为稳定
* `manager.summary_prompt`: 决定了节点的输出质量，其输出最终会成为上下文影响其他节点的工作

#### 3.2.4 Tools工具配置说明

Tools就是能够提供给智能体调用的函数，其函数可以根据需要进行新增， 新增方法如下

* 输入参数：需要定义具体的类型， 并用利用Annotated描述
* 输出参数：明确具体类型
* 函数功能描述：需要 `__doc__`,框架会提取用于提示LLM调用。即在函数开始下方添加 `''' ''' `内容

```python
from typing_extensions import Annotated
from typing import Union, List

def run_shell_code(code:Annotated[str, "The shell code to run"], 
                   path:Annotated[str, "the directory to run the shell code"] = None) -> str:
    '''
    run_shell_code: Run the shell code in the given path

    Args:
        code (Annotated[str, "The shell code to run"]): The shell code to run

        path (Annotated[str, "the directory to run the shell code"]): The directory to run the shell code

    Returns:
        str: The output of the shell code

    Example:  
        code = """
        ls
        """
        print(run_shell_code(code))
        # Output: file1 file2 file3
  
    '''
    if path is None:
        result = subprocess.run(code, shell=True, text=True, capture_output=True)
    else:
        result = subprocess.run(code, shell=True, text=True, capture_output=True, cwd=path)

    if result.stderr:
        return result.stderr
    return result.stdout

```

当前支持的工具集如下：

```python
# Define a mapping of tool names to functions
tool_mapping = {
    "generate_uml": generate_uml,
    "read_file_content": read_file_content,
    "read_clang_uml_readme_file": read_clang_uml_readme_file,
    "find_definition": find_definition,
    "find_declaration": find_declaration,
    "read_plantuml_file": read_plantuml_file,
    "run_shell_code": run_shell_code,
    "run_python_code": run_python_code,
    "get_dir_structure": get_dir_structure,
    "get_dir_structure_with_tree_cmd": get_dir_structure_with_tree_cmd,
    "get_derived_class_of_class": get_derived_class_of_class,
    "get_derived_class_of_function": get_derived_class_of_function,
    "read_function_from_file": read_function_from_file,
    "read_code_from_file": read_code_from_file,
    "file_edit_insert_include_header": file_edit_insert_include_header,
    "file_edit_insert_code_block": file_edit_insert_code_block,
    "file_edit_delete_one_line": file_edit_delete_one_line,
    "file_edit_delete_code_block": file_edit_delete_code_block,
    "file_edit_replace_code_block": file_edit_replace_code_block,
    "file_edit_update_function_defination": file_edit_update_function_defination,
    "file_edit_rollback": file_edit_rollback,
    "file_edit_save": file_edit_save,
    "save_code_to_new_file": save_code_to_new_file,
    "run_cmake_and_make": run_cmake_and_make,
    "run_make": run_make,
    "function_dependency_query": function_dependency_query,
    "file_backup" : file_backup,
    "generate_python_uml": generate_python_uml,
}

```
