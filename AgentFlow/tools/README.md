# MCP服务器HTTP API文档

## 概述

MCP Terminal Server 提供了两种访问方式：
1. **标准MCP协议** - 通过 `/mcp` 路径
2. **自定义HTTP API** - 提供RESTful接口

## 服务器配置

```python
# 启动服务器
app = FastMCP('terminal-server', version='1.0.0')
app.settings.host = '0.0.0.0'
app.settings.port = 8080
app.settings.streamable_http_path = "/mcp"  # MCP协议路径
app.run(transport='streamable-http')
```

## HTTP API端点

### 1. 健康检查

- **URL**: `GET /health`
- **描述**: 检查服务器状态
- **响应**:
  ```json
  {
    "status": "healthy",
    "service": "MCP Terminal Server",
    "working_dir": "/workspace",
    "timestamp": "2025-07-07T10:30:00"
  }
  ```

### 2. 获取工具列表

- **URL**: `GET /api/tools`
- **描述**: 获取所有可用的MCP工具
- **响应**:
  ```json
  {
    "tools": [
      {
        "name": "run_command",
        "description": "执行shell命令",
        "parameters": {
          "type": "object",
          "properties": {
            "command": {
              "type": "string",
              "description": "要执行的shell命令"
            },
            "timeout": {
              "type": "integer",
              "description": "超时时间（秒）"
            }
          }
        }
      }
    ]
  }
  ```

## MCP协议端点

### 访问MCP协议

- **URL**: `POST /mcp`
- **描述**: 标准MCP协议接口，支持StreamableHTTP传输
- **使用方式**: 通过MCP客户端库连接

```python
from mcp.client.streamable_http import StreamableHTTPClientTransport
from mcp.client.session import ClientSession

transport = StreamableHTTPClientTransport("http://localhost:8080/mcp")
async with transport.connect() as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        # 使用MCP协议
        tools = await session.list_tools()
        result = await session.call_tool("run_command", {"command": "pwd"})
```

## 使用示例

### 1. 使用curl命令

```bash
# 健康检查
curl http://localhost:8080/health

# 获取工具列表
curl http://localhost:8080/api/tools


## 部署和访问

1. **启动服务器**:
   ```bash
   python mcp_server.py
   ```

2. **访问地址**:
   - 健康检查: http://localhost:8080/health
   - API工具列表: http://localhost:8080/api/tools
   - MCP协议: http://localhost:8080/mcp

3. **在Docker中运行**:
   ```dockerfile
   FROM python:3.10
   COPY mcp_server.py /app/
   WORKDIR /app
   RUN pip install mcp
   EXPOSE 8080
   CMD ["python", "mcp_server.py"]
   ```

## 错误处理

API会返回适当的HTTP状态码和错误信息：

- `200` - 成功
- `400` - 请求参数错误
- `500` - 服务器内部错误

错误响应格式：
```json
{
  "error": "错误描述信息"
}
```
