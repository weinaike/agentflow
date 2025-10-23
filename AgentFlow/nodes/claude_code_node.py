from .base_node import BaseNode
from ..data_model import ClaudeCodeParam, Context, NodeOutput,RepositoryParam
from typing import Callable, Dict, Union, AsyncGenerator, Optional, Any, TYPE_CHECKING, List
from autogen_agentchat.messages import (
    BaseAgentEvent, 
    BaseChatMessage, 
    TextMessage,
    ThoughtEvent,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    ModelClientStreamingChunkEvent
)
from autogen_agentchat.base import Response
from autogen_agentchat.agents import UserProxyAgent
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import FunctionExecutionResult
from autogen_agentchat.ui import Console
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams
import logging
import json
import os




from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    ClaudeAgentOptions, 
    SystemPromptPreset,
    UserMessage as ClaudeUserMessage,
    AssistantMessage,
    SystemMessage as ClaudeSystemMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    ContentBlock,
    McpServerConfig,
    McpStdioServerConfig,
    McpSSEServerConfig,
    McpHttpServerConfig,
    McpSdkServerConfig
)

logger = logging.getLogger(__name__)
## 只能处理本地代码库
class ClaudeCodeNode(BaseNode):
    def __init__(self, config: Union[Dict, ClaudeCodeParam]):

        if isinstance(config, dict):
            self._param = ClaudeCodeParam(**config)
            self._node_param = self._param
        else:
            self._param = config
            self._node_param = config

        self.print_param()
        
        if self._param.backup_dir is None:
            raise ValueError("backup_dir must be set for ClaudeCodeNode")
        
        self.state_file = os.path.join(
                self._param.backup_dir, 
                f"{self._param.flow_id}_{self._param.id}_chat_state.json"
            )
        self.response: str = ''
        self._input_func: Optional[Callable] = None  # User input function
        self.user_proxy_agent = None
        self.cancellation_token = CancellationToken()
        self._interactive = self._param.interactive if hasattr(self._param, 'interactive') else False

    def set_input_func(self, input_func: Optional[Callable]) -> None:
        self._input_func = input_func
        self.user_proxy_agent = UserProxyAgent(name='user', input_func=input_func)

    def _create_claude_options(self, param: ClaudeCodeParam, context: Context) -> ClaudeAgentOptions:
        """创建 Claude Agent 的配置选项
        
        直接使用 claude_agent_sdk.types.ClaudeAgentOptions，
        从配置文件或默认值构建完整的选项对象。
        """
        options = param.claude_options

        options_dict = options.model_dump()
        
        # 使用 SDK 的 ClaudeAgentOptions 数据类
        claude_options = ClaudeAgentOptions(**options_dict)
        if param.workspace_path:
            claude_options.add_dirs.append(param.workspace_path)
        if param.backup_dir:
            claude_options.add_dirs.append(param.backup_dir)
        if context.codebase:
            if isinstance(context.codebase, str):
                claude_options.add_dirs.append(context.codebase)
                claude_options.cwd = context.codebase
            elif isinstance(context.codebase, RepositoryParam):
                claude_options.add_dirs.append(context.codebase.project_path)
                claude_options.cwd = context.codebase.project_path
                if context.codebase.build_path:
                    claude_options.add_dirs.append(context.codebase.build_path)
                if context.codebase.source_path:
                    claude_options.add_dirs.append(context.codebase.source_path)
                if context.codebase.header_path:
                    claude_options.add_dirs.extend(context.codebase.header_path)


        if len(context.mcps) > 0:
            # 转换 MCP 配置
            claude_mcp_configs = self._autogen_mcp_2_claude_mcp(context.mcps)
            claude_options.mcp_servers = claude_mcp_configs



        return claude_options

    def _convert_claude_to_autogen_message(
        self, 
        claude_msg: Union[ClaudeUserMessage, AssistantMessage, ClaudeSystemMessage, ResultMessage, StreamEvent]
    ) -> Union[List[Union[BaseChatMessage, BaseAgentEvent]], Response]:
        """将 Claude SDK 消息转换为 Autogen 消息格式
        
        转换对应关系：
        1. ClaudeUserMessage -> TextMessage (source="user")
        2. AssistantMessage 根据 ContentBlock 类型：
           - TextBlock -> TextMessage
           - ThinkingBlock -> ThoughtEvent
           - ToolUseBlock -> ToolCallRequestEvent
           - ToolResultBlock -> ToolCallExecutionEvent
        3. ResultMessage -> Response (包含结果统计信息和使用量)
        4. StreamEvent -> ModelClientStreamingChunkEvent
        5. SystemMessage -> TextMessage (source="system")
        
        Returns:
            消息列表，因为一个 AssistantMessage 可能包含多个 ContentBlock
            或者 Response 对象（针对 ResultMessage）
        """
        messages: List[Union[BaseChatMessage, BaseAgentEvent]] = []
        source_prefix = f"{self._param.flow_id}.{self._param.id}"
        
        # 1. 处理 UserMessage
        if isinstance(claude_msg, ClaudeUserMessage):
            if isinstance(claude_msg.content, str):
                # 简单字符串情况
                messages.append(TextMessage(
                    content=claude_msg.content,
                    source=f"{source_prefix}.user"
                ))
            elif isinstance(claude_msg.content, list):
                # content 是 ContentBlock 列表，需要处理多种类型
                text_parts = []
                tool_use_map = {}  # 用于 ToolResultBlock
                
                for block in claude_msg.content:
                    # 1.1 TextBlock - 累积文本
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)                    
                     
                    # 1.4 ToolResultBlock - 用户提供的工具执行结果
                    elif isinstance(block, ToolResultBlock):
                        content_str = ""
                        if isinstance(block.content, str):
                            content_str = block.content
                        elif isinstance(block.content, list):
                            content_str = json.dumps(block.content)
                        elif block.content is None:
                            content_str = ""
                        
                        tool_name = tool_use_map.get(block.tool_use_id, "unknown_tool")
                        result = FunctionExecutionResult(
                            content=content_str,
                            call_id=block.tool_use_id,
                            name=tool_name
                        )
                        messages.append(ToolCallExecutionEvent(
                            content=[result],
                            source=f"{source_prefix}.user_tool_result"
                        ))
                
                # 如果有文本内容，创建 TextMessage
                if text_parts:
                    messages.append(TextMessage(
                        content="\n".join(text_parts).strip(),
                        source=f"{source_prefix}.user"
                    ))
        
        # 2. 处理 AssistantMessage - 最复杂的情况
        elif isinstance(claude_msg, AssistantMessage):
            text_parts = []  # 收集文本块
            tool_use_map = {}  # 存储 tool_use_id -> tool_name 的映射
            
            for block in claude_msg.content:
                # 2.1 TextBlock -> TextMessage (累积)
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
                
                # 2.2 ThinkingBlock -> ThoughtEvent
                elif isinstance(block, ThinkingBlock):
                    messages.append(ThoughtEvent(
                        content=block.thinking,
                        source=f"{source_prefix}.assistant"
                    ))
                
                # 2.3 ToolUseBlock -> ToolCallRequestEvent
                elif isinstance(block, ToolUseBlock):
                    # 记录工具调用映射
                    tool_use_map[block.id] = block.name
                    
                    function_call = FunctionCall(
                        id=block.id,
                        name=block.name,
                        arguments=json.dumps(block.input)
                    )
                    messages.append(ToolCallRequestEvent(
                        content=[function_call],
                        source=f"{source_prefix}.assistant"
                    ))
                
                # 2.4 ToolResultBlock -> ToolCallExecutionEvent
                elif isinstance(block, ToolResultBlock):
                    # 构造 FunctionExecutionResult
                    content_str = ""
                    if isinstance(block.content, str):
                        content_str = block.content
                    elif isinstance(block.content, list):
                        content_str = json.dumps(block.content)
                    elif block.content is None:
                        content_str = ""
                    
                    # 尝试从映射中获取工具名称，如果没有则使用默认值
                    tool_name = tool_use_map.get(block.tool_use_id, "unknown_tool")
                    
                    result = FunctionExecutionResult(
                        content=content_str,
                        call_id=block.tool_use_id,
                        name=tool_name
                    )
                    messages.append(ToolCallExecutionEvent(
                        content=[result],
                        source=f"{source_prefix}.assistant"
                    ))
            
            # 如果有文本内容，创建一个 TextMessage
            if text_parts:
                messages.append(TextMessage(
                    content="\n".join(text_parts),
                    source=f"{source_prefix}.assistant"
                ))
        
        # 3. 处理 ResultMessage -> 转换为 Response
        elif isinstance(claude_msg, ResultMessage):
            # 构建结果摘要内容
            summary = f"""## Claude 执行结果

- 状态: {"❌ 错误" if claude_msg.is_error else "✅ 成功"}
- 轮次: {claude_msg.num_turns}
- 耗时: {claude_msg.duration_ms}ms (API: {claude_msg.duration_api_ms}ms)
- 会话ID: {claude_msg.session_id}
"""
            
            
            if claude_msg.total_cost_usd is not None:
                summary += f"- 成本: ${claude_msg.total_cost_usd:.4f}\n"
            
            if claude_msg.usage:
                summary += f"- 使用量: {json.dumps(claude_msg.usage, ensure_ascii=False, indent=2)}\n"


            print(f"Claude ResultMessage summary: {summary}", flush=True)
            main_message = TextMessage(
                content='',
                source=f"{source_prefix}.assistant"
            )
              
            if claude_msg.result:
                main_message.content = claude_msg.result
            
            # 如果有使用量信息，添加到 models_usage
            if claude_msg.usage:
                from autogen_core.models import RequestUsage
                main_message.models_usage = RequestUsage(
                    prompt_tokens=claude_msg.usage.get("input_tokens", 0),
                    completion_tokens=claude_msg.usage.get("output_tokens", 0)
                )
            
            # 返回 Response 对象
            return Response(chat_message=main_message)
        
        # 4. 处理 StreamEvent
        elif isinstance(claude_msg, StreamEvent):
            # 从事件中提取文本内容
            event_data = claude_msg.event
            content_str = ""
            
            # 根据 Anthropic API 的事件类型提取内容
            if event_data.get("type") == "content_block_delta":
                delta = event_data.get("delta", {})
                if delta.get("type") == "text_delta":
                    content_str = delta.get("text", "")
            
            if content_str:
                messages.append(ModelClientStreamingChunkEvent(
                    content=content_str,
                    source=f"{source_prefix}.assistant"
                ))
        
        # 5. 处理 SystemMessage
        elif isinstance(claude_msg, ClaudeSystemMessage):
            print(claude_msg, flush=True)
            # messages.append(TextMessage(
            #     content=f"[系统消息 - {claude_msg.subtype}] {json.dumps(claude_msg.data, ensure_ascii=False)}",
            #     source=f"{source_prefix}.system"
            # ))
        
        return messages

    async def run(self, context: Context) -> None:
        """运行节点（非流式）"""
        await Console(self.run_stream(context), output_stats=True)

    def _autogen_mcp_2_claude_mcp(self, mcps: list[StdioServerParams | StreamableHttpServerParams | SseServerParams]) -> dict[str, McpServerConfig]:
        """将 Autogen MCP 配置转换为 Claude MCP 配置
        
        转换规则：
        1. StdioServerParams -> McpStdioServerConfig
        2. StreamableHttpServerParams -> McpHttpServerConfig  
        3. SseServerParams -> McpSSEServerConfig
        
        Args:
            mcps: Autogen MCP 服务器参数列表
            
        Returns:
            Claude MCP 服务器配置字典，key为服务器名称，value为配置
        """
        mcp_configs: dict[str, McpServerConfig] = {}
        
        for i, mcp in enumerate(mcps):
            # 生成服务器名称
            server_name = f"{i}"
            
            if isinstance(mcp, StdioServerParams):
                # 转换 StdioServerParams -> McpStdioServerConfig
                config = McpStdioServerConfig(
                    type="stdio",
                    command=mcp.command,
                )
                
                # 添加可选参数
                if hasattr(mcp, 'args') and mcp.args:
                    config["args"] = mcp.args
                    
                if hasattr(mcp, 'env') and mcp.env:
                    config["env"] = mcp.env
                
                mcp_configs[server_name] = config
                
            elif isinstance(mcp, StreamableHttpServerParams):
                # 转换 StreamableHttpServerParams -> McpHttpServerConfig
                config = McpHttpServerConfig(
                    type="http",
                    url=mcp.url,
                )
                
                # 添加可选的headers
                if hasattr(mcp, 'headers') and mcp.headers:
                    config["headers"] = mcp.headers
                
                mcp_configs[server_name] = config
                
            elif isinstance(mcp, SseServerParams):
                # 转换 SseServerParams -> McpSSEServerConfig  
                config = McpSSEServerConfig(
                    type="sse",
                    url=mcp.url,
                )
                
                # 添加可选的headers
                if hasattr(mcp, 'headers') and mcp.headers:
                    config["headers"] = mcp.headers
                
                mcp_configs[server_name] = config
                
            else:
                logger.warning(f"Unsupported MCP server type: {type(mcp)}")
                continue
        
        logger.info(f"Converted {len(mcp_configs)} MCP server configurations")
        return mcp_configs

    async def run_stream(self, context: Context) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """运行节点（流式）"""
        try:
            print(f"\n************* {self._param.flow_id}.{self._param.id} : {self._param.name} execute *************", flush=True)
            
            # 生成上下文内容
            context_content = self._gen_context(context)
            param = self._param
            task = getattr(param, 'task', '')  # type: ignore
            task_content = f"{context_content}\n\n## 任务目标：\n{task}"
            
            # 创建 Claude 客户端选项
            options:ClaudeAgentOptions = self._create_claude_options(self._param, context)

            cancellation_token =  context.cancellation_token if context.cancellation_token else self.cancellation_token



            # 使用 Claude SDK Client
            async with ClaudeSDKClient(options=options) as client:
                
                await client.query(prompt=task_content)
                # 接收并处理响应
                async for message in client.receive_response():
                    # print(message, flush=True)
                    if cancellation_token.is_cancelled():
                        logger.info(f"ClaudeCodeNode {self._param.id} cancelled during execution.")
                        await client.interrupt()
                        break

                    # 转换 Claude 消息为 Autogen 消息
                    autogen_result = self._convert_claude_to_autogen_message(message)
                    
                    # 判断返回的是 Response 还是消息列表
                    if isinstance(autogen_result, Response):
                        # ResultMessage 转换为 Response，直接 yield
                        # 累积响应内容
                        chat_msg = autogen_result.chat_message
                        if isinstance(chat_msg, TextMessage):
                            self.response += chat_msg.content + "\n"
                        yield autogen_result
                    else:
                        # 其他消息类型，返回的是列表
                        for autogen_msg in autogen_result:                           
                            # 生成输出消息（保留原有 source）
                            # print(type(autogen_msg), flush=True)
                            yield autogen_msg

                while self.user_proxy_agent and self._interactive:

                    if cancellation_token.is_cancelled():
                        logger.info(f"ClaudeCodeNode {self._param.id} cancelled during execution.")
                        break
                    msg = TextMessage(content=f"请提供你的建议(如无建议,回复 PASS )......\n", source=f"{self._param.flow_id}.{self._param.id}.assistant")
                    yield msg
                    human_response:Response = await self.user_proxy_agent.on_messages(messages=[msg], cancellation_token=cancellation_token)

                    if not isinstance(human_response.chat_message, TextMessage):
                        break
                
                    content = human_response.chat_message.content
                    if "PASS" in content.strip().upper():
                        break
                    else:
                        await client.query(prompt=content)
                        # 接收并处理响应
                        async for message in client.receive_response():

                            if cancellation_token.is_cancelled():
                                logger.info(f"ClaudeCodeNode {self._param.id} cancelled during execution.")
                                await client.interrupt()
                                break

                            # 转换 Claude 消息为 Autogen 消息
                            autogen_result = self._convert_claude_to_autogen_message(message)
                            
                            # 判断返回的是 Response 还是消息列表
                            if isinstance(autogen_result, Response):
                                # ResultMessage 转换为 Response，直接 yield
                                # 累积响应内容
                                chat_msg = autogen_result.chat_message
                                if isinstance(chat_msg, TextMessage):
                                    self.response += chat_msg.content + "\n"
                                yield autogen_result
                            else:
                                # 其他消息类型，返回的是列表
                                for autogen_msg in autogen_result:                           
                                    # 生成输出消息（保留原有 source）
                                    yield autogen_msg

            # 保存输出
            await self._set_node_output(self.response)
            
        except Exception as e:
            logger.exception(f"Error in ClaudeCodeNode {self._param.id}: {e}")
            error_msg = TextMessage(
                content=f"执行出错: {str(e)}",
                source=f"{self._param.flow_id}.{self._param.id}.system"
            )
            yield error_msg
        finally:
            await self.save_state()

    def _gen_context(self, context: Context) -> str:
        """生成上下文内容"""
        if self._param.flow_id is None:
            raise ValueError(f"flow_id is not set for node {self._param.id}")
        flow_id = self._param.flow_id
        inputs = self._param.inputs
        
        content = f"## 项目背景：\n{context.project_description}\n\n"
        
        if flow_id in context.flow_description:
            content += f"## 工作流描述：\n{context.flow_description[flow_id]}\n\n"
        
        # 添加前置节点的输出
        if inputs:
            content += "## 前置节点输出：\n"
            for input_id in inputs:
                output: Optional[NodeOutput] = None
                if '.' in input_id:
                    fid, nid = input_id.split('.')
                    output = context.get_node_output(fid, nid)
                else:
                    output = context.get_node_output(flow_id, input_id)
                
                if output:
                    detail = output.get_content()
                    content += f"### {output.description}\n{detail}\n\n"
        
        return content

    async def _set_node_output(self, content: str) -> None:
        """设置节点输出"""
        if self._param.output is None:
            raise ValueError(f"Output must be defined for ClaudeCodeNode {self._param.id}")
        with open(self._param.output.address, "w") as f:
            f.write(content)
        self._param.output.content = content

    async def get_NodeOutput(self) -> NodeOutput:
        """获取节点输出"""
        if self._param.output:
            return self._param.output
        else:
            raise ValueError(f"No output defined for node {self._param.id}")

    async def stop(self) -> None:
        """停止节点执行"""
        logger.info(f"Stopping ClaudeCodeNode {self._param.id}")
        # Claude SDK 的清理会在 async with 上下文中自动处理

    async def load_state(self) -> bool:
        """加载节点状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    self.response = state.get("response", "")
                    logger.info(f"Loaded state for ClaudeCodeNode {self._param.id}")
                    return True
            except Exception as e:
                logger.exception(f"Error loading state for node {self._param.id}: {e}")
                return False
        return False

    async def save_state(self) -> Dict:
        """保存节点状态"""
        state = {
            "response": self.response,
            "node_id": self._param.id,
            "flow_id": self._param.flow_id
        }
        
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved state for ClaudeCodeNode {self._param.id}")
        except Exception as e:
            logger.exception(f"Error saving state for node {self._param.id}: {e}")
        
        return state


