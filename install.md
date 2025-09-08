# AgentFlow 项目安装配置文档

## 项目简介

AgentFlow 是一个基于Python开发的智能体工作流构建框架，旨在帮助用户通过配置文件快速构建和管理复杂的智能体工作流，实现任务自动化和高效执行。

## 系统要求

### 基础环境
- **Python**: 3.10 或更高版本
- **操作系统**: Linux, macOS, Windows
- **内存**: 最小 4GB RAM，推荐 8GB+
- **存储**: 最小 1GB 可用空间

### 开发环境要求
- **Git**: 用于版本控制
- **Git LFS**: 用于管理大文件（如图片）
- **Node.js**: 14.15.0 或更高版本（用于前端开发）
- **npm**: 用于包管理

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/weinaike/agentflow.git
cd agentflow
```

### 2. 安装 Git LFS（如需要）

```bash
# Debian/Ubuntu
apt-get install git-lfs

# macOS (Homebrew)
brew install git-lfs

# Windows (Chocolatey)
choco install git-lfs

# 初始化 Git LFS
git lfs install
```

### 3. 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv agentflow_env

# 激活虚拟环境
# Linux/macOS:
source agentflow_env/bin/activate
# Windows:
agentflow_env\Scripts\activate
```

### 4. 安装 Python 依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 或者使用开发模式安装
pip install -e .
```

### 5. 安装 UML 分析工具（可选）

```bash
# 安装 clang-uml
sudo add-apt-repository ppa:bkryza/clang-uml
sudo apt update
sudo apt install clang-uml
```

### 6. 安装前端依赖（如需要修改前端）

```bash
# 进入前端目录
cd studio/frontend

# 安装依赖
npm install -g gatsby-cli
npm install --global yarn
yarn install

# 构建前端
yarn build
```

## 配置说明

### 1. 环境变量配置

创建 `.env` 文件：

```bash
# 复制默认配置文件
cp .env.default .env.development

# 编辑配置文件
nano .env.development
```

主要配置项：
```bash
# API 配置
GATSBY_API_URL=http://localhost:8081/api

# 数据库配置
DATABASE_URL=sqlite:///database.sqlite

# 应用目录
APP_DIR=/home/<USER>/.autogenstudio

# MCP 服务器配置
MCP_HOST=0.0.0.0
MCP_PORT=8080
```

### 2. 数据库配置

支持多种数据库后端：

#### SQLite（默认）
```bash
autogenstudio ui --database-uri sqlite:///database.sqlite
```

#### PostgreSQL
```bash
autogenstudio ui --database-uri postgresql+psycopg://user:password@localhost/dbname
```

#### MySQL
```bash
autogenstudio ui --database-uri mysql://user:password@localhost/dbname
```

### 3. 工作流配置

工作流通过 TOML 配置文件定义，示例配置：

```toml
# 工作流配置
[flow]
name = "example_flow"
type = "sequential"

# 节点配置
[[flow.nodes]]
name = "agent_node"
type = "AgentNode"
parameters = { model = "gpt-3.5-turbo", temperature = 0.7 }

[[flow.nodes]]
name = "tool_node"
type = "ToolNode"
parameters = { tool_name = "run_command", timeout = 30 }
```

## 运行方法

### 1. 运行 MCP 服务器

```bash
# 启动 MCP 服务器
python mcp_server.py

# 或使用 Python 模块
python -m AgentFlow.main path/to/your/config.file
```

### 2. 运行 AutoGen Studio

```bash
# 启动 Web UI
autogenstudio ui --port 8081

# 或使用开发模式（自动重载）
autogenstudio ui --port 8081 --reload
```

### 3. 访问服务

- **MCP 服务器**: http://localhost:8080
  - 健康检查: http://localhost:8080/health
  - API 工具列表: http://localhost:8080/api/tools
  - MCP 协议: http://localhost:8080/mcp

- **AutoGen Studio**: http://localhost:8081

## 开发指南

### 1. 项目结构

```
/workspace/
├── AgentFlow/          # 核心框架代码
│   ├── tools/         # 工具集合
│   ├── main.py        # 主入口
│   └── data_model.py  # 数据模型定义
├── studio/            # Studio相关代码
│   ├── frontend/      # 前端代码
│   └── README.md
├── script/            # 脚本文件
└── mcp_server.py      # MCP服务器实现
```

### 2. 新增工作流

```python
# 继承 BaseFlow
from AgentFlow.flow import BaseFlow

class MyCustomFlow(BaseFlow):
    def execute(self, context):
        # 实现自定义逻辑
        pass

# 在 FlowFactory 中注册
from AgentFlow.flow_factory import FlowFactory
FlowFactory.register('my_flow', MyCustomFlow)
```

### 3. 新增节点

```python
# 继承 BaseNode
from AgentFlow.node import BaseNode

class MyCustomNode(BaseNode):
    def process(self, input_data, context):
        # 实现自定义处理逻辑
        pass

# 在 NodeFactory 中注册
from AgentFlow.node_factory import NodeFactory
NodeFactory.register('my_node', MyCustomNode)
```

### 4. 添加 LLM 支持

更新 `data_model.py` 中的 `ModelEnum` 枚举，添加新的模型类型，同时参考 `docs/llm_config_list_template.json` 格式添加相应配置。

## 故障排除

### 1. 常见问题

#### Python 依赖安装失败
```bash
# 更新 pip
pip install --upgrade pip

# 清理缓存
pip cache purge

# 重新安装
pip install -r requirements.txt
```

#### 前端构建失败
```bash
# 清理构建缓存
cd studio/frontend
yarn clean
gatsby clean

# 重新安装依赖
yarn install
yarn build
```

#### 数据库连接失败
```bash
# 检查数据库文件权限
chmod 644 database.sqlite

# 检查数据库连接字符串格式
autogenstudio ui --database-uri sqlite:///database.sqlite
```

### 2. 调试工具

#### 启用详细日志
```bash
# 设置环境变量
export PYTHONPATH=${PYTHONPATH}:${PWD}
export LOG_LEVEL=DEBUG

# 运行服务
python mcp_server.py
```

#### 使用 MCP 客户端测试
```python
from mcp.client.streamable_http import StreamableHTTPClientTransport
from mcp.client.session import ClientSession

transport = StreamableHTTPClientTransport("http://localhost:8080/mcp")
async with transport.connect() as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        # 使用 MCP 协议
        tools = await session.list_tools()
        result = await session.call_tool("run_command", {"command": "pwd"})
```

## 部署指南

### 1. Docker 部署

#### 创建 Dockerfile
```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app/

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 暴露端口
EXPOSE 8080 8081

# 启动服务
CMD ["python", "mcp_server.py"]
```

#### 构建 Docker 镜像
```bash
docker build -t agentflow .
```

#### 运行 Docker 容器
```bash
docker run -d -p 8080:8080 -p 8081:8081 agentflow
```

### 2. 生产环境配置

#### 使用 systemd 服务
```ini
# /etc/systemd/system/agentflow.service
[Unit]
Description=AgentFlow MCP Server
After=network.target

[Service]
Type=simple
User=agentflow
WorkingDirectory=/opt/agentflow
ExecStart=/opt/agentflow/venv/bin/python mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 使用 Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /mcp {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 性能优化

### 1. 数据库优化

- 使用 PostgreSQL 替代 SQLite 获得更好的性能
- 定期清理过期的工作流和会话数据
- 添加适当的索引以提高查询性能

### 2. 缓存配置

```python
# 配置 Redis 缓存
import redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

redis_client = redis.Redis(host='localhost', port=6379, db=0)
FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
```

### 3. 负载均衡

使用 Gunicorn 或 Uvicorn 运行多个实例：

```bash
# 使用 Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker mcp_server:app

# 使用 Uvicorn
uvicorn mcp_server:app --host 0.0.0.0 --port 8080 --workers 4
```

## 安全配置

### 1. 环境变量安全

```bash
# 使用 .env 文件存储敏感信息
echo "DATABASE_URL=your_database_url" >> .env
echo "API_KEY=your_api_key" >> .env

# 设置文件权限
chmod 600 .env
```

### 2. API 认证

```python
# 添加认证中间件
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # 验证 token
    if credentials.credentials != "your-secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": "user123"}
```

### 3. 网络安全

- 使用 HTTPS 加密传输
- 配置防火墙规则
- 定期更新依赖包

## 监控和日志

### 1. 日志配置

```python
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('agentflow.log', maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
```

### 2. 健康检查

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AgentFlow",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

## 贡献指南

### 1. 代码规范

- 遵循 PEP 8 Python 代码风格指南
- 使用类型注解提高代码可读性
- 编写清晰的文档字符串

### 2. 提交规范

```bash
# 分支命名
feature/new-feature
bugfix/bug-description
hotfix/critical-fix

# 提交信息格式
type(scope): description

# 示例
feat(flow): add sequential flow support
fix(node): resolve timeout issue
docs(readme): update installation guide
```

### 3. 测试要求

```python
# 单元测试示例
import pytest
from AgentFlow.flow import BaseFlow

class TestMyFlow(BaseFlow):
    def test_execute(self):
        context = {}
        result = self.execute(context)
        assert result is not None
```

## 许可证

本项目遵循 MIT 许可证，详见 `LICENSE` 文件。

## 技术支持

- **GitHub Issues**: [项目 Issues 页面](https://github.com/weinaike/agentflow/issues)
- **文档**: [项目文档](https://github.com/weinaike/agentflow/docs)
- **社区**: [开发者社区](https://github.com/weinaike/agentflow/discussions)

---

*本文档最后更新时间：2025-07-07*