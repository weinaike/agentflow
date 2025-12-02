import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import AsyncGenerator, Callable, List, Optional, Sequence, Union
import uuid

import aiofiles
import aiohttp
import yaml
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, ToolCallSummaryMessage,TextMessage, ToolCallRequestEvent
from autogen_agentchat.teams import BaseGroupChat
from autogen_core import EVENT_LOGGER_NAME, CancellationToken, ComponentModel
from autogen_core.logging import LLMCallEvent
from autogen_ext.tools.mcp import StreamableHttpServerParams
from loguru import logger
from ..datamodel.types import EnvironmentVariable, LLMCallEventMessage, TeamResult
from ..web.managers.run_context import RunContext
from AgentFlow import Solution, solution


# 全局变量用于保存 WebSocket 管理器实例（用于 MCP 隧道）
_websocket_manager = None


def set_websocket_manager(manager):
    """设置 WebSocket 管理器实例（用于 MCP 隧道功能）"""
    global _websocket_manager
    _websocket_manager = manager


def get_websocket_manager():
    """获取 WebSocket 管理器实例"""
    return _websocket_manager


class RunEventLogger(logging.Handler):
    """Event logger that queues LLMCallEvents for streaming"""

    def __init__(self):
        super().__init__()
        self.events = asyncio.Queue()

    def emit(self, record: logging.LogRecord):
        if isinstance(record.msg, LLMCallEvent):
            self.events.put_nowait(LLMCallEventMessage(content=str(record.msg)))


class TeamManager:
    """Manages team operations including loading configs and running teams"""

    def __init__(self):
        self._team: Optional[Union[BaseGroupChat, Solution]] = None
        self._run_context = RunContext()

    @staticmethod
    async def check_health(url: str, timeout: float = 5.0) -> bool:
        """Check if a service is healthy by calling its health endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Health check failed for {url}: {e}")
            return False

    @staticmethod
    async def load_from_file(path: Union[str, Path]) -> dict:
        """Load team configuration from JSON/YAML file"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        async with aiofiles.open(path) as f:
            content = await f.read()
            if path.suffix == ".json":
                return json.loads(content)
            elif path.suffix in (".yml", ".yaml"):
                return yaml.safe_load(content)
            raise ValueError(f"Unsupported file format: {path.suffix}")

    @staticmethod
    async def load_from_directory(directory: Union[str, Path]) -> List[dict]:
        """Load all team configurations from a directory"""
        directory = Path(directory)
        configs = []
        valid_extensions = {".json", ".yaml", ".yml"}

        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() in valid_extensions:
                try:
                    config = await TeamManager.load_from_file(path)
                    configs.append(config)
                except Exception as e:
                    logger.error(f"Failed to load {path}: {e}")

        return configs

    async def _create_team(
        self,
        team_config: Union[str, Path, dict, ComponentModel],
        input_func: Optional[Callable] = None,
        env_vars: Optional[List[EnvironmentVariable]] = None,
    ) -> Union[BaseGroupChat, Solution]:
        """Create team instance from config"""
        if isinstance(team_config, (str, Path)):
            config = await self.load_from_file(team_config)
        elif isinstance(team_config, dict):
            config = team_config
        else:
            config = team_config.model_dump()

        # Load env vars into environment if provided
        if env_vars:
            logger.info("Loading environment variables")
            for var in env_vars:
                os.environ[var.name] = var.value
        if config.get("component_type") == "team":
            self._team = BaseGroupChat.load_component(config)
            for agent in self._team._participants:
                if hasattr(agent, "input_func") and isinstance(agent, UserProxyAgent) and input_func:
                    agent.input_func = input_func
        elif config.get("component_type") == "solution":

            if 'codebase' in config:
                config['config']['codebase'] = config['codebase']
                config['config']['description'] = f"\n** 项目必要信息**\n** 项目代码库路径 ** : {config['codebase']}\n"

            if 'run_id' in config:
                os.makedirs('workspace', exist_ok=True)
                config['config']['workspace_path'] = f'workspace/{config["run_id"]}'
                config['config']['backup_dir'] = f'workspace/{config["run_id"]}/cache'
                config['config']['project_id'] = f'{config["run_id"]}'

            solution:Solution = Solution.load_component(config)
            if input_func:
                logger.info("Setting input function for solution")
                solution.set_input_func(input_func)

            if 'mcp_server' in config:
                mcp_server = config['mcp_server']
                mcp_port = config.get('mcp_port', 8080)
                mcp_token = config.get('mcp_token', 'your_token')
                command_mcp_server = StreamableHttpServerParams(
                    url=f"http://{mcp_server}:{mcp_port}/mcp",
                    headers={"Authorization": f"Bearer {mcp_token}"},
                    sse_read_timeout=3600,  # Set SSE read timeout to 1 hour
                )
                ret = await solution.register_tools(command_mcp_server)
                if ret == False:
                    logger.warning(f"{mcp_server}:{mcp_port} MCP服务器工具注册失败,请检查MCP服务是否正常运行,将继续执行")
                else:
                    logger.info(f"成功注册 MCP 服务: {mcp_server}:{mcp_port}")
                    
            elif config.get('use_local_mcp', False):
                command_mcp_server = StreamableHttpServerParams(
                        url="http://localhost:8080/mcp",
                        headers={"Authorization": "Bearer YOUR_ACCESS_TOKEN"},
                    sse_read_timeout = 3600,  # 设置SSE读取超时时间为1小时
                )
                ret = await solution.register_tools(command_mcp_server)
                if ret == False:
                    logger.warning("本地 localhost:8080 MCP服务器工具注册失败,请检查MCP服务是否正常运行,将继续执行")
                else:
                    logger.info("成功注册 本地 localhost:8080 MCP 服务")
            # 检查是否有 MCP 隧道连接（VSCode 端通过同一个 WebSocket 连接）
            run_id = config.get('run_id')
            ws_manager = get_websocket_manager()
            
            if run_id and ws_manager:
                # 等待隧道连接初始化完成（最多等待 5 秒）
                max_wait_time = 5.0
                wait_interval = 0.2
                waited = 0.0
                
                while waited < max_wait_time:
                    if ws_manager.has_mcp_tunnel(run_id):
                        break
                    logger.debug(f"等待 MCP 隧道连接初始化... (run_id: {run_id}, waited: {waited:.1f}s)")
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                
                if ws_manager.has_mcp_tunnel(run_id):
                    logger.info(f"检测到 MCP 隧道连接 (run_id: {run_id})，正在创建隧道工具映射...")
                    try:
                        from ..web.managers.mcp_tunnel import register_mcp_tunnel_tools_from_ws
                        tunnel_tool_mapping = await register_mcp_tunnel_tools_from_ws(ws_manager, run_id)
                        # 注册到 solution 实例的内部工具映射
                        await solution.register_tools(tunnel_tool_mapping)
                        logger.info(f"成功注册 {len(tunnel_tool_mapping)} 个 MCP 隧道工具到 Solution")
                    except Exception as e:
                        logger.warning(f"创建 MCP 隧道工具映射失败: {e}，将继续执行")
                else:
                    logger.info(f"未检测到 run_id {run_id} 的 MCP 隧道连接（等待超时），跳过隧道工具注册")
            elif run_id:
                logger.info(f"WebSocket 管理器未初始化，跳过隧道工具注册")

            # Check if localhost:4444 health endpoint is available and register MCP service
            if await self.check_health("http://localhost:4444/api/health"):
                logger.info("Health check passed for localhost:4444, registering MCP service")
                project_id = Path(config['codebase']).name
                session_id = str(uuid.uuid4())
                logger.info(f"project_id: {project_id}, Generated session ID: {session_id}")
                command_mcp_server = StreamableHttpServerParams(
                        url="http://localhost:4444/mcp",
                        headers={"Authorization": "Bearer YOUR_ACCESS_TOKEN", 
                                 "X-Project-ID": project_id,
                                 "X-Session-ID": session_id},
                    sse_read_timeout=600,
                    timeout=30,
                )
                ret = await solution.register_tools(command_mcp_server)
                if ret == False:
                    logger.warning("任务管理 MCP 服务注册失败,请检查本地4444端口的MCP服务是否正常运行,将继续执行")
                else:
                    logger.info("成功注册 任务管理 MCP 服务")
            else:
                logger.info("Health check failed for localhost:4444, skipping MCP service registration")

            self._team = solution
        return self._team

    async def run_stream(
        self,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None,
        team_config: Union[str, Path, dict, ComponentModel],
        input_func: Optional[Callable] = None,
        cancellation_token: Optional[CancellationToken] = None,
        env_vars: Optional[List[EnvironmentVariable]] = None,
        flow_id: Optional[str] = None,
        node_ids: Optional[Sequence[str]] = None,
    ) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | LLMCallEvent, BaseChatMessage, TeamResult], None]:
        """Stream team execution results"""
        start_time = time.time()
        team = None

        # Setup event logger correctly (use different name to avoid shadowing global loguru logger)
        event_logger = logging.getLogger(EVENT_LOGGER_NAME)
        event_logger.setLevel(logging.INFO)
        llm_event_logger = RunEventLogger()
        event_logger.handlers = [llm_event_logger]  # Replace all handlers

        try:
            team = await self._create_team(team_config, input_func, env_vars)

            # Get the appropriate stream based on team type
            if isinstance(team, BaseGroupChat):
                stream = team.run_stream(task=task, cancellation_token=cancellation_token)
            elif isinstance(team, Solution):

                stream = team.run_stream(
                    task=task,
                    cancellation_token=cancellation_token,
                    specific_flow=[flow_id] if flow_id else [],
                    specific_node=node_ids if node_ids else [],
                )
            else:
                return

            # Process messages from the stream
            async for message in stream:
                if cancellation_token and cancellation_token.is_cancelled():
                    break

                if isinstance(message, TaskResult):
                    yield TeamResult(task_result=message, usage="solution", duration=time.time() - start_time)
                elif isinstance(message, BaseAgentEvent):
                    print(type(message), flush=True)
                    if isinstance(message, ToolCallRequestEvent):                        
                        names = []
                        for result in message.content:
                            names.append(result.name)
                        text = "".join([f"调用工具：{name}  \n" for name in names])
                        message = TextMessage(content=text, source=message.source)
                        yield message

                elif isinstance(message, BaseChatMessage):
                    print(type(message), flush=True)
                    if isinstance(message, ToolCallSummaryMessage):
                        names = []
                        for result in message.results:
                            names.append(result.name)
                        text = "".join([f"调用工具：{name}  \n" for name in names])
                        message = TextMessage(content=text, source=message.source)  

                    if isinstance(message, TextMessage):
                        content = message.content.replace('TERMINATE', '')
                        content = content.replace('_I_HAVE_COMPLETED_', '')
                        message = TextMessage(content=content, source=message.source)
                    source = message.source
                    if '.' in source:
                        s_flow_id, s_node_id, s_role = source.split('.')   
                        if s_role == 'assistant':
                            yield message
                elif isinstance(message, Response) and isinstance(team, Solution):
                    print(type(message), flush=True)
                    # Ensure Response messages are properly formatted
                    msg = message.chat_message
                    if isinstance(msg, TextMessage):
                        content = msg.content.replace('TERMINATE', '')
                        content = content.replace('_I_HAVE_COMPLETED_', '')
                        msg.content = content

                    result = TaskResult(messages=[msg], stop_reason='node completed')
                    source = message.chat_message.source
                    yield TeamResult(task_result=result, usage=source, duration=time.time() - start_time)

                # Check for any LLM events
                while not llm_event_logger.events.empty():
                    event = await llm_event_logger.events.get()
                    # yield event
        finally:
            # Cleanup - remove our handler
            if llm_event_logger in event_logger.handlers:
                event_logger.handlers.remove(llm_event_logger)

            # Ensure cleanup happens
            if team and hasattr(team, "_participants"):
                for agent in team._participants:
                    if hasattr(agent, "close"):
                        await agent.close()

    async def run(
        self,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None,
        team_config: Union[str, Path, dict, ComponentModel],
        input_func: Optional[Callable] = None,
        cancellation_token: Optional[CancellationToken] = None,
        env_vars: Optional[List[EnvironmentVariable]] = None,
    ) -> TeamResult:
        """Run team synchronously"""
        start_time = time.time()
        team = None

        try:
            team = await self._create_team(team_config, input_func, env_vars)
            result = await team.run(task=task, cancellation_token=cancellation_token)

            return TeamResult(task_result=result, usage="", duration=time.time() - start_time)

        finally:
            if team and hasattr(team, "_participants"):
                for agent in team._participants:
                    if hasattr(agent, "close"):
                        await agent.close()
