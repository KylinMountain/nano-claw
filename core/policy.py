"""
策略引擎 - HumanInTheLoop的核心
模仿Gemini CLI的PolicyEngine
"""
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .types import PolicyDecision, ConfirmationDetails
from tools.base import ToolKind, MUTATOR_KINDS


class ApprovalMode(Enum):
    """批准模式"""
    PLAN = "plan"           # Plan模式：只允许读操作
    DEFAULT = "default"     # 默认模式
    YOLO = "yolo"          # YOLO模式：自动允许
    READ_ONLY = "read_only" # 只读模式


@dataclass
class PolicyRule:
    """策略规则"""
    tool_pattern: str       # 工具名匹配模式
    decision: PolicyDecision
    condition: Optional[str] = None  # 额外条件


class PolicyEngine:
    """策略引擎"""
    
    def __init__(self, mode: ApprovalMode = ApprovalMode.DEFAULT):
        self.mode = mode
        self._always_allow: Set[str] = set()
        self._always_deny: Set[str] = set()
        self._rules: List[PolicyRule] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """设置默认规则"""
        # 读操作工具默认允许
        self._always_allow.update([
            "read_file", "glob", "grep"
        ])
        
        # 设置基于模式的规则
        self._rules = [
            PolicyRule("read_*", PolicyDecision.ALLOW),
            PolicyRule("write_*", PolicyDecision.ASK_USER),
            PolicyRule("delete_*", PolicyDecision.ASK_USER),
            PolicyRule("shell", PolicyDecision.ASK_USER),
            PolicyRule("execute_*", PolicyDecision.ASK_USER),
        ]
    
    def set_mode(self, mode: ApprovalMode) -> None:
        """设置批准模式"""
        self.mode = mode
    
    def add_always_allow(self, tool_name: str) -> None:
        """添加总是允许的工具"""
        self._always_allow.add(tool_name)
    
    def add_always_deny(self, tool_name: str) -> None:
        """添加总是拒绝的工具"""
        self._always_deny.add(tool_name)
    
    def check(
        self,
        tool_name: str,
        tool_kind: ToolKind,
        arguments: Dict,
        is_mutator: bool = False
    ) -> PolicyDecision:
        """
        检查工具调用是否符合策略
        
        Returns:
            PolicyDecision: ALLOW, DENY, 或 ASK_USER
        """
        # YOLO模式 - 全部允许
        if self.mode == ApprovalMode.YOLO:
            return PolicyDecision.ALLOW
        
        # 只读模式 - 只允许读操作
        if self.mode == ApprovalMode.READ_ONLY:
            if tool_kind != ToolKind.READ and is_mutator:
                return PolicyDecision.DENY
            return PolicyDecision.ALLOW
        
        # Plan模式 - 只允许读操作和搜索
        if self.mode == ApprovalMode.PLAN:
            if tool_kind in (ToolKind.READ, ToolKind.SEARCH, ToolKind.THINK):
                return PolicyDecision.ALLOW
            return PolicyDecision.ASK_USER
        
        # 检查黑名单
        if tool_name in self._always_deny:
            return PolicyDecision.DENY
        
        # 检查白名单
        if tool_name in self._always_allow:
            return PolicyDecision.ALLOW
        
        # 应用规则
        for rule in self._rules:
            if self._match_pattern(tool_name, rule.tool_pattern):
                return rule.decision
        
        # 默认：有副作用的操作需要确认
        if is_mutator:
            return PolicyDecision.ASK_USER
        
        return PolicyDecision.ALLOW
    
    def _match_pattern(self, name: str, pattern: str) -> bool:
        """匹配工具名模式"""
        if pattern.endswith('*'):
            return name.startswith(pattern[:-1])
        return name == pattern
    
    def generate_confirmation_prompt(
        self,
        tool_name: str,
        arguments: Dict,
        affected_locations: List[str]
    ) -> str:
        """生成确认提示"""
        lines = [
            f"🔧 **Tool Execution Request**",
            f"",
            f"**Tool:** `{tool_name}`",
            f"**Arguments:**"
        ]
        
        for key, value in arguments.items():
            lines.append(f"  - {key}: `{value}`")
        
        if affected_locations:
            lines.extend([
                f"",
                f"**Affected Locations:**"
            ])
            for loc in affected_locations:
                lines.append(f"  - {loc}")
        
        lines.extend([
            f"",
            f"Do you want to proceed?"
        ])
        
        return "\n".join(lines)


class ConfirmationManager:
    """确认管理器"""
    
    def __init__(self):
        self._pending_confirmations: Dict[str, ConfirmationDetails] = {}
        self._callbacks: Dict[str, callable] = {}
    
    def request_confirmation(
        self,
        call_id: str,
        details: ConfirmationDetails,
        callback: callable
    ) -> None:
        """请求确认"""
        self._pending_confirmations[call_id] = details
        self._callbacks[call_id] = callback
    
    def respond(self, call_id: str, approved: bool, outcome: str = "proceed_once") -> bool:
        """响应确认请求"""
        if call_id not in self._pending_confirmations:
            return False
        
        callback = self._callbacks.get(call_id)
        if callback:
            callback(approved, outcome)
        
        # 清理
        del self._pending_confirmations[call_id]
        del self._callbacks[call_id]
        
        return True
    
    def get_pending(self) -> Dict[str, ConfirmationDetails]:
        """获取待处理的确认请求"""
        return self._pending_confirmations.copy()
    
    def cancel_all(self) -> None:
        """取消所有待处理的确认"""
        for call_id, callback in self._callbacks.items():
            callback(False, "cancel")
        self._pending_confirmations.clear()
        self._callbacks.clear()