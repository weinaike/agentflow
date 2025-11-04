# AgentFlow 容器构建与运行指南

本目录包含了 AgentFlow 项目的容器化相关文件，支持使用 Docker 或 Podman 构建和运行完整的 AgentFlow 服务栈。

## 📁 文件说明

- `Dockerfile` - 容器镜像构建文件
- `build.sh` - 镜像构建脚本
- `run-podman.sh` - Podman 容器运行脚本(测试用)
- `supervisord.conf` - Supervisor 进程管理配置
- `entrypoint.sh` - 容器入口脚本（废弃，由 Supervisor 替代）

## 🗄️ MongoDB 数据库准备

AgentFlow 服务依赖 MongoDB 数据库，需要先启动 MongoDB 容器才能正常运行。

### 启动 MongoDB 容器

#### 使用 Podman 启动 MongoDB

```bash
# 拉取 MongoDB 镜像
podman pull mongo:latest

# 启动 MongoDB 容器
podman run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  -e MONGO_INITDB_DATABASE=shrimp_db \
  -v mongodb_data:/data/db \
  mongo:latest
```

### MongoDB 连接配置

**当前 run-podman.sh 脚本连接的mongodb启用账号、密码**
AgentFlow 容器通过以下连接字符串访问 MongoDB：

```text
mongodb://admin:password@host.containers.internal:27017/shrimp_db
```

**说明**：

- `admin:password` 是 MongoDB 的管理员账号和密码
- `host.containers.internal` 是容器访问宿主机服务的特殊地址，需要根据实际情况调整
- `27017` 是 MongoDB 的默认端口
- `shrimp_db` 是应用使用的数据库名称


### 验证 MongoDB 连接

```bash
# 检查 MongoDB 容器状态
podman ps | grep mongodb

# 连接到 MongoDB 容器测试（使用管理员账号）
podman exec -it mongodb mongosh -u admin -p password

# 在 mongosh 中执行（可选）
> show dbs
> use shrimp_db
> show collections
```

## 🏗️ 镜像构建

### 环境要求

- Docker 或 Podman
- Linux/macOS/Windows 系统
- 网络连接（用于下载依赖）
- **MongoDB 数据库**（必须先启动）

### 构建选项

镜像构建支持以下环境变量配置：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `IMAGE` | `agentflow-shrimp:1.0.1` | 构建的镜像名称和标签 |
| `PYTHON_BASE_IMAGE` | `python:3.11.4-slim-bullseye` | Python 基础镜像 |
| `PYPI_REPOSITORY` | `https://pypi.tuna.tsinghua.edu.cn/simple` | PyPI 镜像源 |
| `PYPI_TIMEOUT` | `15` | PyPI 超时时间（秒） |
| `BUILD_ENGINE` | `podman` | 构建引擎（podman/docker） |

### 快速构建

```bash
# 使用默认配置构建
cd container
./build.sh

```

### 镜像组件

构建的镜像包含以下组件：

1. **AgentFlow 主服务** - 基于 AutoGen Studio 的智能代理服务
2. **Shrimp 后端服务** - 任务管理 MCP 和 API 服务
3. **Supervisor** - 多进程配置项

## 🚀 容器运行

### 使用 Podman 运行（本地）

```bash
cd container
./run-podman.sh
```

**注意**：

- 确保 MongoDB 容器已经启动并运行正常
- `run-podman.sh` 脚本中的 MONGO_URI 已配置为 `mongodb://host.containers.internal:27017/shrimp_db`， 需要根据实际情况调整

### 运行配置

容器运行支持以下环境变量配置：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `IMAGE` | `localhost/agentflow-shrimp:1.0.1` | 要运行的镜像 |
| `CONTAINER_NAME` | `agentflow-shrimp` | 容器名称 |
| `API_PORT` | `4444` | Shrimp API 服务端口 （脚本中使用9444 是因为4444端口被占用）|
| `AGENT_PORT` | `8084` | AgentFlow 服务端口 （脚本中使用9084 是因为8084端口被占用）|

### 端口映射

- **4444** → **4444** (Shrimp API 服务)
- **8084** → **8084** (AgentFlow 服务)

### 数据卷挂载 （**必须挂载以下数据卷，对于数据持久化至关重要**）

- `workspace/` → `/app/workspace` (工作区数据持久化)
- `logs/` → `/var/log` (日志文件持久化)
- `mongodb_data` → `/data/db` (MongoDB 数据持久化)
- `~/.autogenstudio` → `/root/.autogenstudio` (AutoGen Studio 配置持久化)

## 🔧 服务访问

容器启动后，可以通过以下地址访问服务：

### AgentFlow 服务

- **Web 界面**: <http://localhost:9084>
- **测试页面**: <http://localhost:9084/static/ws-test.html>

### Shrimp API 服务

- **健康检查**: <http://localhost:9444/api/health>
- **API 文档**: <http://localhost:9444/docs>

## 📊 监控与管理

### 查看容器状态

```bash
podman ps
```

### 查看服务日志

```bash
# 查看所有日志
podman logs agentflow-shrimp

# 实时查看日志
podman logs -f agentflow-shrimp
```

### 进入容器调试

```bash
podman exec -it agentflow-shrimp bash
```

### 停止容器

```bash
podman stop agentflow-shrimp
```

## 🔍 健康检查

运行脚本会自动执行健康检查：

- ✅ Shrimp API 服务状态检查
- ✅ AgentFlow 服务状态检查

## 📋 环境变量完整列表

### 构建时环境变量

- `MONGO_URI` - MongoDB 连接字符串（例如：`mongodb://admin:password@host.containers.internal:27017/shrimp_db`）
- `DATABASE_NAME` - 数据库名称（默认：`shrimp_db`）
- `HOST` - Shrimp 任务管理服务绑定主机
- `PORT` - Shrimp 任务管理服务端口
- `DEBUG` - Shrimp 任务管理服务调试模式开关

### 运行时环境变量

- `PYTHONUNBUFFERED=1` - Python 输出不缓冲
- `TZ=Asia/Shanghai` - 时区设置
- `MONGO_URI` - MongoDB 连接配置（需包含认证信息）
- `DATABASE_NAME` - 数据库名称

---

📝 **说明**: 本容器化方案基于 Supervisor 管理多个服务进程，确保 AgentFlow 和 Shrimp 服务的稳定运行。如有问题，请查看日志文件。
