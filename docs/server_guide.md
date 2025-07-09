# AgentFlow 服务器部署指南

## 目录
1. [概述](#概述)
2. [WebSocket 服务开发与部署](#websocket-服务开发与部署)
3. [MCP 工具开发与部署](#mcp-工具开发与部署)
4. [Docker 容器化部署](#docker-容器化部署)

## 概述

AgentFlow 是一个基于 Python 的智能体工作流框架，支持两种主要的服务部署模式：
- **WebSocket 服务**: 提供实时的流式交互能力
- **MCP (Model Context Protocol) 服务**: 提供工具调用和上下文管理能力

## WebSocket 服务开发与部署

### 1. WebSocket 服务架构

AgentFlow 的 WebSocket 服务基于 FastAPI 和 AutoGen Studio 构建，提供实时的任务执行和流式交互能力。服务架构包括：

- **FastAPI 应用**: 主要的 Web 应用框架
- **WebSocket 路由**: 处理 WebSocket 连接和消息路由
- **WebSocket 管理器**: 管理连接状态和消息分发
- **Team 管理器**: 处理任务执行和团队配置
- **数据库管理**: 存储会话、运行状态和配置

```python
# 基本的 WebSocket 服务结构 (studio/autogenstudio/web/serve.py)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import ws

app = FastAPI(
    title="AgentFlow Server API",
    version="1.0.0",
    description="AgentFlow WebSocket API service"
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含 WebSocket 路由
app.include_router(
    ws.router,
    prefix="/ws",
    tags=["websocket"]
)
```

### 2. WebSocket 服务配置

AgentFlow 的 WebSocket 服务配置通过环境变量和配置文件管理：

```python
# 环境变量配置 (studio/autogenstudio/web/config.py)
class Settings(BaseSettings):
    DATABASE_URI: str = "sqlite:///./autogen04202.db"
    API_DOCS: bool = False
    CLEANUP_INTERVAL: int = 300  # 5 minutes
    SESSION_TIMEOUT: int = 3600  # 1 hour
    CONFIG_DIR: str = "configs"
    DEFAULT_USER_ID: str = "guestuser@gmail.com"
    UPGRADE_DATABASE: bool = False

    model_config = {"env_prefix": "AUTOGENSTUDIO_"}

# 环境变量示例
export AUTOGENSTUDIO_DATABASE_URI="sqlite:///./agentflow.db"
export AUTOGENSTUDIO_API_DOCS="true"
export AUTOGENSTUDIO_CONFIG_DIR="./configs"
```

### 3. WebSocket 服务部署步骤

#### 3.1 环境准备

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 2. 安装依赖
cd studio
pip install -r requirements.txt

# 3. 验证安装
python -c "import autogenstudio; print('AutoGen Studio installed successfully')"
```

#### 3.2 使用 CLI 启动服务

AgentFlow 提供了便捷的 CLI 工具来启动 WebSocket 服务：

```bash
# 启动完整的 UI 服务 (包含 WebSocket)
python -m autogenstudio.cli ui --host 0.0.0.0 --port 8081 --docs

# 启动简化的 API 服务 (仅 WebSocket)
python -m autogenstudio.cli serve --host 0.0.0.0 --port 8084 --docs

# 开发模式启动 (自动重载)
python -m autogenstudio.cli serve --host 0.0.0.0 --port 8084 --reload --docs
```

#### 3.3 手动启动服务

```bash
# 使用 uvicorn 直接启动
uvicorn autogenstudio.web.serve:app --host 0.0.0.0 --port 8084 --reload

# 生产环境启动
uvicorn autogenstudio.web.serve:app --host 0.0.0.0 --port 8084 --workers 4
```

#### 3.4 验证服务

```bash
# 检查服务状态
curl http://localhost:8084/health

# 查看版本信息
curl http://localhost:8084/version

# 查看 WebSocket 协议文档
curl http://localhost:8084/ws-docs

# 访问 API 文档
open http://localhost:8084/docs
```


## MCP 工具开发与部署

### 1. MCP 服务架构

MCP (Model Context Protocol) 服务提供了工具调用和上下文管理的标准化接口。

```python
# MCP 服务器基本结构
from mcp.server import FastMCP
from mcp.types import TextContent

app = FastMCP('agentflow-mcp-server', version='1.0.0')

# 注册工具
app.add_tool(generate_cpp_uml)
app.add_tool(extract_class_structure_from_uml)
app.add_tool(file_edit_save_to_file)
app.add_tool(run_command)
```

### 2. MCP 工具开发

#### 2.1 工具定义规范

每个 MCP 工具都应该遵循以下结构：

```python
from mcp.types import Tool, TextContent
from typing import Any, Dict

async def your_tool_function(
    param1: str,
    param2: int = 100
) -> str:
    """
    工具描述
    
    Args:
        param1: 参数1描述
        param2: 参数2描述，默认值100
        
    Returns:
        str: 返回结果描述
    """
    # 工具实现逻辑
    result = f"处理 {param1} 完成"
    return result

# 注册工具
app.add_tool(your_tool_function)
```

#### 2.2 现有工具类别

AgentFlow 提供了以下类别的 MCP 工具：

**代码分析工具**:
- `generate_cpp_uml`: 生成 C++ UML 类图
- `extract_class_structure_from_uml`: 提取类结构
- `fetch_source_code`: 获取源代码
- `query_right_name`: 查询正确函数名

**文件操作工具**:
- `file_edit_save_to_file`: 保存文件
- `read_file`: 读取文件
- `write_file`: 写入文件
- `list_directory`: 列出目录

**系统工具**:
- `run_command`: 执行系统命令
- `run_python_code`: 执行 Python 代码
- `run_shell_code`: 执行 Shell 代码

### 3. MCP 服务部署

#### 3.1 独立部署

```bash
# 1. 进入工具目录
cd AgentFlow/tools

# 2. 启动 MCP 服务器
python mcp_server.py

# 3. 验证服务
curl http://localhost:8080/health
```

#### 3.2 Docker 部署

使用提供的 Docker 配置 [docs/dockerfile]：

```bash
# 配置信息：docker-compose.yml
# 1. 构建镜像
docker-compose build 

# 2. 启动服务
docker-compose up -d 

```

#### 3.3 服务配置

MCP 服务器配置位于 `AgentFlow/tools/mcp_server.py`：

```python
# 健康检查端点
@app.custom_route("/health", methods=["GET"])
async def health_check(request) -> Response:
    return JSONResponse({"status": "healthy", "timestamp": time.time()})

# 工具列表端点
@app.custom_route("/tools", methods=["GET"])
async def list_tools(request) -> Response:
    return JSONResponse({"tools": app.list_tools()})
```

