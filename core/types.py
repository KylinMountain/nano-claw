"""
核心类型定义 - 模仿Gemini CLI的核心类型系统
"""
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json


class LoopState(Enum):
    """Agent Loop 状态机"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_TOOL = "waiting_tool"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    ERROR = "error"


class ToolKind(Enum):
    """工具类型枚举"""
    READ = "read"
    EDIT = "edit"
    DELETE = "delete"
    MOVE = "move"
    SEARCH = "search"
    EXECUTE = "execute"
    THINK = "think"
    FETCH = "fetch"
    COMMUNICATE = "communicate"
    SKILL = "skill"
    OTHER = "other"


# 有副作用的工具类型
MUTATOR_KINDS = {ToolKind.EDIT, ToolKind.DELETE, ToolKind.MOVE, ToolKind.EXECUTE}


class PolicyDecision(Enum):
    """策略引擎决策结果"""
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"


class ToolConfirmationOutcome(Enum):
    """工具确认结果"""
    PROCEED_ONCE = "proceed_once"
    PROCEED_ALWAYS = "proceed_always"
    PROCEED_ALWAYS_TOOL = "proceed_always_tool"
    CANCEL = "cancel"
    MODIFY_WITH_EDITOR = "modify_with_editor"


@dataclass
class Message:
    """对话消息"""
    role: str  # "user", "assistant", "system", "tool"
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        data = {"role": self.role}
        if self.content:
            data["content"] = self.content
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.name:
            data["name"] = self.name
        return data


@dataclass
class ToolCallRequest:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ToolCallRequest":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            arguments=data.get("arguments", {})
        )


@dataclass
class ToolResult:
    """工具执行结果"""
    call_id: str
    success: bool
    content: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": self.call_id,
            "content": self.content if self.success else f"Error: {self.error}"
        }


@dataclass
class ToolSchema:
    """工具JSON Schema定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


@dataclass
class ConfirmationDetails:
    """确认详情"""
    title: str
    prompt: str
    tool_name: str
    arguments: Dict[str, Any]
    

@dataclass
class SkillDefinition:
    """Skill定义"""
    name: str
    description: str
    location: str
    body: str
    disabled: bool = False
    is_builtin: bool = False
    active: bool = False


@dataclass
class AgentEvent:
    """Agent事件"""
    type: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)


# 事件处理器类型
EventHandler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class EventType:
    """事件类型常量"""
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_CONFIRMATION_REQUEST = "tool_confirmation_request"
    TOOL_CONFIRMATION_RESPONSE = "tool_confirmation_response"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    COMPLETION = "completion"
    THINKING = "thinking"