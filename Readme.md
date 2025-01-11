## 项目说明文档

### 项目简介

AgentFlow是一个基于Python语言开发的智能体工作流构建框架。旨在帮助用户通过配置文件快速构建和管理复杂的智能体工作流，实现任务自动化和高效执行。

### 软件特性

- **动态工作流管理**：支持顺序和循环流程组合，实现复杂的任务控制。
- **多种节点类型**：包括AgentNode和ToolNode，支持多样化的行为和任务处理。
- **高度扩展性**：流程和节点可通过继承扩展，支持自定义功能的集成。
- **信息共享与管理**：采用上下文机制在执行期间共享信息和状态，提高信息流的效率。

### 安装指南

1. **克隆项目**：

   ```bash
   git clone https://github.com/weinaike/agentflow.git
   cd agentflow
   ```
2. **安装依赖项**：

   ```bash
   pip install -r requirements.txt
   #或者可编辑安装，调用pyproject.toml安装
   pip install -e . 
   ```

### 项目结构与开发指引

## 使用说明

1. **配置工作流**

   - 通过YAML或JSON文件定义工作流，包括步骤、节点及其参数配置。
2. **运行工作流**

   ```bash
   python -m AgentFlow.main path/to/your/config.file
   # 或者 pip install -e .后运行
   agentflow path/to/your/config.file
   ```
3. **监控与调试**

   - 利用日志和调试工具监控执行过程，记录异常信息。
4. **扩展功能**

   - 通过继承 `BaseNode`实现自定义执行节点。

- **数据模型（data_model）**：定义参数结构，确保数据一致性。
- **流程管理（flows）**：管理流程顺序和逻辑。
- **节点管理（nodes）**：提供节点的具体功能实现。
- **工具集合（tools）**：辅助模块，提供通用功能。

#### 开发指南

- **设计原则**：遵循SOLID和工厂模式，保证高内聚低耦合。
- **新增流程与节点**：
  - 新流程需继承 `BaseFlow`，在 `FlowFactory`中注册。
  - 新节点需继承 `BaseNode`，在 `NodeFactory`中注册。
- **上下文使用**：统一状态保证信息的共享。
- **配置管理**：利用TOML文件灵活管理流程和节点参数。
- **LLM配置**：详见docs/llm_config_list_template.json

### 项目许可证

本项目遵循MIT许可协议，用户可以自由使用、修改和分发代码，需保留原始许可证和版权声明。详见 `LICENSE`文件。
