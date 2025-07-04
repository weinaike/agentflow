# from dataclasses import Field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Sequence

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_core import ComponentModel
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from pydantic import BaseModel, ConfigDict, SecretStr


class MessageConfig(BaseModel):
    source: str
    content: str | ChatMessage | Sequence[ChatMessage] | None
    message_type: Optional[str] = "text"


class TeamResult(BaseModel):
    task_result: TaskResult
    usage: str
    duration: float


class LLMCallEventMessage(TextMessage):
    source: str = "llm_call_event"

    def to_text(self) -> str:
        return self.content

    def to_model_text(self) -> str:
        return self.content

    def to_model_message(self) -> UserMessage:
        raise NotImplementedError("This message type is not supported.")


class MessageMeta(BaseModel):
    task: Optional[str] = None
    task_result: Optional[TaskResult] = None
    summary_method: Optional[str] = "last"
    files: Optional[List[dict]] = None
    time: Optional[datetime] = None
    log: Optional[List[dict]] = None
    usage: Optional[List[dict]] = None


class GalleryMetadata(BaseModel):
    author: str
    # created_at: datetime = Field(default_factory=datetime.now)
    # updated_at: datetime = Field(default_factory=datetime.now)
    version: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    license: Optional[str] = None
    homepage: Optional[str] = None
    category: Optional[str] = None
    last_synced: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class GalleryComponents(BaseModel):
    agents: List[ComponentModel]
    models: List[ComponentModel]
    tools: List[ComponentModel]
    terminations: List[ComponentModel]
    teams: List[ComponentModel]


class GalleryConfig(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    metadata: GalleryMetadata
    components: GalleryComponents

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat(), SecretStr: lambda v: v.get_secret_value()}
    )


class EnvironmentVariable(BaseModel):
    name: str
    value: str
    type: Literal["string", "number", "boolean", "secret"] = "string"
    description: Optional[str] = None
    required: bool = False


class UISettings(BaseModel):
    show_llm_call_events: bool = False
    expanded_messages_by_default: bool = True
    show_agent_flow_by_default: bool = True


class SettingsConfig(BaseModel):
    environment: List[EnvironmentVariable] = []
    default_model_client: Optional[ComponentModel] = OpenAIChatCompletionClient(
        model="gpt-4o-mini", api_key="your-api-key"
    ).dump_component()
    ui: UISettings = UISettings()


# web request/response data models


class Response(BaseModel):
    message: str
    status: bool
    data: Optional[Any] = None


class SocketMessage(BaseModel):
    connection_id: str
    data: Dict[str, Any]
    type: str

class TeamConfig(BaseModel):
    id: int  # 唯一标识符，与数据库的Team id对应

    oss_endpoint:str # OSS存储地址
    bucket_name: str # OSS存储桶名称
    # oss_access_key_id: str # OSS访问密钥ID, 这个如何管理
    # oss_access_key_secret: str # OSS访问密钥Secret
    
    llm_config: Optional[dict] = None # 先内置， 是否需要外部配置，再讨论。

    # codebase RepositoryParam: str = None # 代码库路径 通过MCP接口获取，RepositoryParam， 
    mcp_server: Optional[str] = None  # MCP服务器地址， MCP工具与待处理数据放在一个容器中
    mcp_port: Optional[int] = None  # MCP服务器端口
    mcp_token: Optional[str] = None  # MCP访问令牌
    