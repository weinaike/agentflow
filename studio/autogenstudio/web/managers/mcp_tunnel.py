"""
MCP Tunnel Manager - 管理与 VSCode 端的 MCP 隧道连接

该模块实现了服务端的 MCP 隧道功能，允许后端通过 WebSocket 连接
调用 VSCode 端暴露的 MCP 工具，解决局域网 MCP 服务无法被公网访问的问题。
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Type, TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from autogen_core.utils import schema_to_pydantic_model

logger = logging.getLogger(__name__)


class McpTunnelConnection:
    """单个 MCP 隧道连接的封装"""
    
    def __init__(self, websocket: WebSocket, run_id: int):
        self.websocket = websocket
        self.run_id = run_id
        self.server_info: Optional[Dict[str, Any]] = None
        self.capabilities: Optional[Dict[str, Any]] = None
        self.tools: List[Dict[str, Any]] = []
        self.initialized: bool = False
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_counter = 0
        self.created_at = datetime.now(timezone.utc)
    
    def _generate_request_id(self) -> str:
        """生成唯一的请求 ID"""
        self._request_counter += 1
        return f"req_{self.run_id}_{self._request_counter}_{uuid.uuid4().hex[:8]}"
    
    async def send_mcp_request(
        self, 
        method: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0
    ) -> Any:
        """
        发送 MCP 请求到 VSCode 端并等待响应
        
        Args:
            method: MCP 方法名 (如 'tools/list', 'tools/call')
            params: 请求参数
            timeout: 超时时间(秒)
        
        Returns:
            MCP 响应结果
        """
        request_id = self._generate_request_id()
        
        # 构造 JSON-RPC 请求
        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        # 包装成隧道消息格式
        tunnel_message = {
            "type": "mcp_request",
            "id": request_id,
            "request": json_rpc_request
        }
        
        # 创建 Future 用于等待响应
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            # 发送请求
            await self.websocket.send_json(tunnel_message)
            logger.debug(f"发送 MCP 请求: {method} (id: {request_id})")
            
            # 等待响应
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"MCP 请求超时: {method} (id: {request_id})")
            raise TimeoutError(f"MCP request timeout: {method}")
        finally:
            self._pending_requests.pop(request_id, None)
    
    def handle_response(self, request_id: str, response: Dict[str, Any]) -> bool:
        """
        处理从 VSCode 端收到的响应
        
        Args:
            request_id: 请求 ID
            response: JSON-RPC 响应
        
        Returns:
            是否成功处理
        """
        if request_id not in self._pending_requests:
            logger.warning(f"收到未知请求的响应: {request_id}")
            return False
        
        future = self._pending_requests[request_id]
        
        if "error" in response:
            # 设置异常
            error = response["error"]
            future.set_exception(
                McpToolError(
                    code=error.get("code", -1),
                    message=error.get("message", "Unknown error")
                )
            )
        else:
            # 设置结果
            future.set_result(response.get("result"))
        
        return True
    
    async def initialize(self) -> bool:
        """
        初始化 MCP 连接，获取工具列表
        
        Returns:
            是否初始化成功
        """
        try:
            # 发送 initialize 请求
            init_result = await self.send_mcp_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "agentflow-server",
                        "version": "1.0.0"
                    }
                }
            )
            
            self.server_info = init_result.get("serverInfo")
            self.capabilities = init_result.get("capabilities")
            
            # 发送 initialized 通知
            await self.send_mcp_request("initialized", {})
            
            # 获取工具列表
            tools_result = await self.send_mcp_request("tools/list")
            self.tools = tools_result.get("tools", [])
            
            self.initialized = True
            logger.info(f"MCP 隧道初始化成功 (run_id: {self.run_id}), 工具数量: {len(self.tools)}")
            return True
            
        except Exception as e:
            logger.error(f"MCP 隧道初始化失败 (run_id: {self.run_id}): {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具执行结果
        """
        if not self.initialized:
            raise RuntimeError("MCP 隧道未初始化")
        
        result = await self.send_mcp_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            },
            timeout=300.0  # 工具调用可能需要更长时间
        )
        
        return result
    
    async def close(self):
        """关闭连接并清理资源"""
        # 取消所有待处理的请求
        for request_id, future in self._pending_requests.items():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()


class McpToolError(Exception):
    """MCP 工具调用错误"""
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"MCP Error {code}: {message}")


class McpTunnelToolAdapter(BaseTool[BaseModel, Any]):
    """
    MCP 隧道工具适配器
    
    将 MCP 隧道中的工具包装为 autogen 兼容的工具格式，
    可以直接添加到 mcp_tool_mapping 中供 Agent 使用。
    
    此适配器继承自 autogen_core.tools.BaseTool，
    使其可以无缝集成到现有的工具系统中。
    """
    
    component_type = "tool"
    
    def __init__(self, connection: McpTunnelConnection, tool_def: Dict[str, Any]):
        """
        初始化工具适配器
        
        Args:
            connection: MCP 隧道连接
            tool_def: MCP 工具定义
        """
        self._connection = connection
        self._tool_def = tool_def
        
        # 提取工具信息
        name = tool_def.get("name", "unknown_tool")
        description = tool_def.get("description", "")
        input_schema = tool_def.get("inputSchema", {"type": "object", "properties": {}})
        
        # 使用 schema_to_pydantic_model 将 JSON schema 转换为 Pydantic 模型
        input_model = schema_to_pydantic_model(input_schema)
        
        # 使用 Any 作为返回类型，因为 MCP 工具返回类型可能不同
        return_type: Type[Any] = object
        
        # 调用父类构造函数
        super().__init__(input_model, return_type, name, description)
    
    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        """
        执行工具调用
        
        Args:
            args: Pydantic 模型参数
            cancellation_token: 取消令牌
        
        Returns:
            工具执行结果
        """
        try:
            # 检查是否已取消
            if cancellation_token.is_cancelled():
                raise asyncio.CancelledError("Operation cancelled")
            
            # 将 Pydantic 模型转换为字典，排除未设置的值
            kwargs = args.model_dump(exclude_unset=True)
            
            result = await self._connection.call_tool(self._name, kwargs)
            
            # 处理 MCP 工具结果格式
            if isinstance(result, dict):
                content = result.get("content", [])
                is_error = result.get("isError", False)
                
                if is_error:
                    error_msg = self._extract_text_content(content)
                    raise Exception(error_msg or "Tool execution failed")
                
                return content
            
            return result
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"MCP 隧道工具调用失败 [{self._name}]: {e}")
            raise
    
    def _extract_text_content(self, content: List[Any]) -> str:
        """从 content 列表中提取文本内容"""
        if not content:
            return ""
        
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)
    
    def return_value_as_string(self, value: Any) -> str:
        """
        将返回值转换为字符串格式
        
        Args:
            value: 工具返回值
        
        Returns:
            字符串格式的返回值
        """
        if isinstance(value, str):
            return value
        
        if isinstance(value, list):
            # 处理 content 列表格式
            texts = []
            for item in value:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        texts.append(item.get("text", ""))
                    else:
                        texts.append(json.dumps(item, ensure_ascii=False))
                else:
                    texts.append(str(item))
            return "\n".join(texts) if texts else "[]"
        
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False, indent=2)
        
        return str(value)
    
    def __repr__(self) -> str:
        return f"McpTunnelToolAdapter(name={self._name})"


async def register_mcp_tunnel_tools_from_ws(
    ws_manager: "WebSocketManager",
    run_id: int
) -> Dict[str, McpTunnelToolAdapter]:
    """
    从 WebSocketManager 的 MCP 隧道创建工具映射
    
    Args:
        ws_manager: WebSocket 管理器（包含集成的 MCP 隧道）
        run_id: 运行 ID
    
    Returns:
        工具映射字典 { tool_name: McpTunnelToolAdapter }
    """
    try:
        # 获取 MCP 隧道连接
        connection = ws_manager.get_mcp_tunnel(run_id)
        if not connection:
            logger.warning(f"未找到 run_id {run_id} 的 MCP 隧道连接")
            return {}
        
        if not connection.initialized:
            logger.warning(f"run_id {run_id} 的 MCP 隧道未初始化")
            return {}
        
        # 创建工具映射（不再使用全局变量）
        tool_mapping = {}
        for tool_def in connection.tools:
            adapter = McpTunnelToolAdapter(
                connection=connection,
                tool_def=tool_def
            )
            tool_mapping[adapter.name] = adapter
            logger.info(f"创建 MCP 隧道工具适配器: {adapter.name}")
        
        logger.info(f"成功创建 {len(tool_mapping)} 个 MCP 隧道工具适配器 (run_id: {run_id})")
        return tool_mapping
        
    except Exception as e:
        logger.error(f"创建 MCP 隧道工具映射失败: {e}")
        return {}


# 添加类型提示导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .connection import WebSocketManager
