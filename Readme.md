## 项目说明文档

### 项目简介

AgentFlow是一个基于Python语言开发的智能体工作流构建框架。旨在帮助用户通过配置文件快速构建和管理复杂的智能体工作流，实现任务自动化和高效执行。

### 软件特性

- **动态工作流管理**：支持顺序和循环流程组合，实现复杂的任务控制。
- **多种节点类型**：包括AgentNode和ToolNode，支持多样化的行为和任务处理。
- **高度扩展性**：流程和节点可通过继承扩展，支持自定义功能的集成。
- **信息共享与管理**：采用上下文机制在执行期间共享信息和状态，提高信息流的效率。

## 项目内容
该项目下包含3个主要部分：
- **AgentFlow**：核心框架代码，包含工作流和节点的定义与管理。（./AgentFlow/）
- **MCP工具容器**：提供多种预置工具的Docker容器 （./docker-compose.yml）
- **Websocket**：智能体服务端与后端交互的WebSocket服务（./studio/）
   - studio中包含多个内容: autogenstudio智能体服务端，frontend前端界面，和一些预置的工具文档
   - Websocket放置在 ./studio/autogenstudio/cli.py




### 安装指南

1. **克隆项目**：

```bash
git clone https://github.com/weinaike/agentflow.git
cd agentflow
```

2. **安装AgentFlow**： 
```bash
pip install -r requirements.txt
#或者可编辑安装，调用pyproject.toml安装
pip install -e . 
```

3.  **WebSocket服务**：    
```bash
cd studio 
pip install -e . 
```
   - 启动服务
```bash
cd ..
autogenstudio serve --host 0.0.0.0 --port 8084
```

注意： WebSocket服务 内部会调用Agentflow，因而两者的python包依赖需要保持一致。
而且启动WebSocket服务，要求在该项目根目录启动

WebSocket服务启动后，智能体要正常工作，需要配置模型与API_KEY等环境变量，
- DEFAULT_MODEL=glm-4.5(默认模型)
- OPENAI_API_KEY=your_api_key
- OPENAI_BASE_URL=https://api.openai.com/v1 (需要提供模型服务地址)

4. **MCP工具容器**：

   - MCP工具容器：参考 docker-compose.yml
   - 该工具容器要求独立部署，与AgentFlow和WebSocket服务可以分开部署

### 项目结构与开发指引

## 使用说明

1. **配置工作流**

   - 通过TOML文件定义工作流，包括流、节点及其参数配置。
   - 具体配置说明，请参考 [docs/configuration_guide.md](./docs/configuration_guide.md)
2. **运行工作流**

   ```bash
   python -m AgentFlow.main path/to/your/config.file
   # 或者 pip install -e .后运行
   agentflow path/to/your/config.file
   ```

### 开发指南

- **设计原则**：遵循SOLID和工厂模式，保证高内聚低耦合。
- **配置管理**：利用TOML文件灵活管理流程和节点参数。
- **上下文使用**：统一对象存储，保证信息的共享。
- **新增流程与节点**：
  - 新流程需继承 `BaseFlow`，在 `FlowFactory`中注册。
  - 新节点需继承 `BaseNode`，在 `NodeFactory`中注册。
  - 新增LLM支持，格式详见docs/llm_config_list_template.json, 同时保证 data_model.py 中的 ModelEnum 包含对应模型枚举
- **数据模型（data_model）**：定义参数结构，确保数据一致性。
- **工具集合（tools）**：辅助模块，提供通用功能。

### 项目许可证

本项目遵循MIT许可协议，用户可以自由使用、修改和分发代码，需保留原始许可证和版权声明。详见 `LICENSE`文件。
