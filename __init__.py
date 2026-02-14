"""
Nano Claw - Python仿写Gemini CLI最小Agent系统

包含功能:
- Agent Loop核心循环
- 工具调用系统
- MCP (Model Context Protocol)
- Skills系统（渐进式披露）
- 三层记忆系统
- HumanInTheLoop确认机制
"""

__version__ = "0.1.0"
__author__ = "Mountain Gu"

from core.types import (
    LoopState, ToolKind, PolicyDecision,
    Message, ToolCallRequest, ToolResult,
    SkillDefinition, AgentEvent
)
from core.llm_client import LLMClient, ConversationCompressor
from core.agent_loop import AgentLoop, AgentConfig, EventBus
from core.policy import PolicyEngine, ApprovalMode
from tools.base import ToolRegistry, ToolScheduler, ToolBuilder, ToolInvocation
from tools.builtin import register_builtin_tools
from skills.manager import SkillManager, SkillLoader, ActivateSkillTool
from memory.manager import MemoryManager, ProjectContextExtractor

__all__ = [
    # Core types
    "LoopState", "ToolKind", "PolicyDecision",
    "Message", "ToolCallRequest", "ToolResult",
    "SkillDefinition", "AgentEvent",
    # Core components
    "LLMClient", "ConversationCompressor",
    "AgentLoop", "AgentConfig", "EventBus",
    "PolicyEngine", "ApprovalMode",
    # Tools
    "ToolRegistry", "ToolScheduler", "ToolBuilder", "ToolInvocation",
    "register_builtin_tools",
    # Skills
    "SkillManager", "SkillLoader", "ActivateSkillTool",
    # Memory
    "MemoryManager", "ProjectContextExtractor",
]