import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import AsyncGenerator, Callable, List, Optional, Sequence, Union

import aiofiles
import yaml
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.base import TaskResult, Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import BaseGroupChat
from autogen_core import EVENT_LOGGER_NAME, CancellationToken, ComponentModel
from autogen_core.logging import LLMCallEvent
from autogen_ext.tools.mcp import StreamableHttpServerParams
from ..datamodel.types import EnvironmentVariable, LLMCallEventMessage, TeamResult
from ..web.managers.run_context import RunContext
from AgentFlow import Solution, solution
logger = logging.getLogger(__name__)


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
                config['config']['description'] += f"\n** 项目必要信息**\n** 项目代码库路径 ** : {config['codebase']}\n"

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
                await solution.register_tools(command_mcp_server)
            else:
                command_mcp_server = StreamableHttpServerParams(
                        url="http://localhost:8080/mcp",
                        headers={"Authorization": "Bearer YOUR_ACCESS_TOKEN"},
                    sse_read_timeout = 3600,  # 设置SSE读取超时时间为1小时
                )
                await solution.register_tools(command_mcp_server)

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

        # Setup logger correctly
        logger = logging.getLogger(EVENT_LOGGER_NAME)
        logger.setLevel(logging.INFO)
        llm_event_logger = RunEventLogger()
        logger.handlers = [llm_event_logger]  # Replace all handlers

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
                # elif isinstance(message, BaseAgentEvent):
                #     yield message
                elif isinstance(message, BaseChatMessage):
                    source = message.source
                    s_flow_id, s_node_id, s_role = source.split('.')   
                    if s_role == 'assistant':
                        yield message
                elif isinstance(message, Response) and isinstance(team, Solution):                    
                    # Ensure Response messages are properly formatted
                    result = TaskResult(messages=[message.chat_message], stop_reason='node completed')
                    source = message.chat_message.source
                    yield TeamResult(task_result=result, usage=source, duration=time.time() - start_time)

                # Check for any LLM events
                while not llm_event_logger.events.empty():
                    event = await llm_event_logger.events.get()
                    # yield event
        finally:
            # Cleanup - remove our handler
            if llm_event_logger in logger.handlers:
                logger.handlers.remove(llm_event_logger)

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
