"""
工具基类 - 所有工具的基类
模仿Gemini CLI的工具系统
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import uuid


class ToolKind(str, Enum):
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


class ToolResult:
    """工具执行结果"""
    
    def __init__(
        self,
        call_id: str,
        success: bool,
        content: str = "",
        error: str = None,
        metadata: Dict = None
    ):
        self.call_id = call_id
        self.success = success
        self.content = content
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        result = {
            "success": self.success,
            "content": self.content,
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class ToolBuilder(ABC):
    """工具构建器基类"""
    
    def __init__(
        self,
        name: str,
        display_name: str = None,
        description: str = "",
        kind: ToolKind = ToolKind.OTHER,
        parameter_schema: Dict = None,
        confirmation_required: bool = False,
        confirmation_prompt: str = None
    ):
        self.name = name
        self.display_name = display_name or name
        self.description = description
        self.kind = kind
        self.parameter_schema = parameter_schema or {"type": "object", "properties": {}}
        self.confirmation_required = confirmation_required
        self.confirmation_prompt = confirmation_prompt
    
    @abstractmethod
    def build(self, call_id: str, params: Dict[str, Any]):
        """构建工具调用实例"""
        pass
    
    def to_schema(self) -> Dict:
        """转换为OpenAI工具格式"""
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameter_schema
            }
        }
        return schema


class ToolInvocation:
    """工具调用实例"""
    
    def __init__(
        self,
        name: str,
        display_name: str = None,
        kind: ToolKind = ToolKind.OTHER,
        params: Dict[str, Any] = None,
        call_id: str = None
    ):
        self.name = name
        self.display_name = display_name or name
        self.kind = kind
        self.params = params or {}
        self.call_id = call_id or ""
    
    async def execute(self, cancellation_event = None) -> ToolResult:
        """执行工具调用（子类重写）"""
        return ToolResult(
            call_id=self.call_id,
            success=True,
            content="Tool executed"
        )


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, ToolBuilder] = {}
        self._call_id_counter = 0
    
    def register(self, tool: ToolBuilder) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:
        """注销工具"""
        self._tools.pop(name, None)
    
    def get(self, name: str) -> Optional[ToolBuilder]:
        """获取工具"""
        return self._tools.get(name)
    
    def get_all(self) -> list:
        """获取所有工具"""
        return list(self._tools.values())
    
    def build_tool(self, name: str, call_id: str = None, params: Dict[str, Any] = None):
        """构建工具调用"""
        tool = self._tools.get(name)
        if not tool:
            return None
        
        self._call_id_counter += 1
        call_id = call_id or f"call_{self._call_id_counter}"
        
        return tool.build(call_id, params or {})
    
    def get_all_schemas(self) -> List:
        """获取所有工具的Schema"""
        from core.types import ToolSchema
        schemas = []
        for tool in self._tools.values():
            schema = ToolSchema(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameter_schema
            )
            schemas.append(schema)
        return schemas
    
    def create_invocation(self, call_id: str, name: str, params: Dict[str, Any]):
        """创建工具调用实例"""
        tool = self._tools.get(name)
        if not tool:
            return None
        return tool.build(call_id, params)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
    
    def __len__(self) -> int:
        return len(self._tools)


@dataclass
class ToolExecutionContext:
    """工具执行上下文"""
    call_id: str
    tool_name: str
    params: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    parent_call_id: Optional[str] = None
    depth: int = 0
    user_confirmation: Optional[bool] = None
    
    
class ToolScheduler:
    """工具调度器 - 管理工具的执行顺序和依赖"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.execution_queue: List[ToolExecutionContext] = []
        self.execution_history: List[ToolExecutionContext] = []
        self.dependency_graph: Dict[str, List[str]] = {}
        self.max_concurrent: int = 3
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
    
    def add_to_schedule(
        self,
        tool_name: str,
        params: Dict[str, Any] = None,
        parent_call_id: str = None,
        depth: int = 0
    ) -> str:
        """添加工具调用到调度队列"""
        call_id = str(uuid.uuid4())[:8]
        context = ToolExecutionContext(
            call_id=call_id,
            tool_name=tool_name,
            params=params or {},
            parent_call_id=parent_call_id,
            depth=depth
        )
        self.execution_queue.append(context)
        return call_id
    
    def add_dependency(self, tool_name: str, depends_on: List[str]) -> None:
        """添加工具依赖关系"""
        self.dependency_graph[tool_name] = depends_on
    
    async def execute_scheduled(self, executor: Callable[[ToolExecutionContext], Any] = None) -> List[ToolResult]:
        """执行所有调度的工具调用"""
        results = []
        
        async def run_with_semaphore(context: ToolExecutionContext):
            async with self.semaphore:
                if executor:
                    result = await executor(context)
                else:
                    result = await self._default_execute(context)
                self.execution_history.append(context)
                return result
        
        # 简单顺序执行（可以扩展为并发执行）
        for context in self.execution_queue:
            if context.tool_name in self.registry:
                result = await run_with_semaphore(context)
                results.append(result)
            else:
                results.append(ToolResult(
                    call_id=context.call_id,
                    success=False,
                    error=f"Tool not found: {context.tool_name}"
                ))
        
        self.execution_queue.clear()
        return results
    
    async def _default_execute(self, context: ToolExecutionContext) -> ToolResult:
        """默认执行逻辑"""
        tool_invocation = self.registry.build_tool(
            context.tool_name,
            context.call_id,
            context.params
        )
        if tool_invocation:
            return await tool_invocation.execute()
        return ToolResult(
            call_id=context.call_id,
            success=False,
            error=f"Failed to build tool: {context.tool_name}"
        )
    
    def get_execution_order(self) -> List[str]:
        """获取执行顺序（考虑依赖）"""
        order = []
        visited = set()
        
        def visit(tool_name: str):
            if tool_name in visited:
                return
            visited.add(tool_name)
            
            if tool_name in self.dependency_graph:
                for dep in self.dependency_graph[tool_name]:
                    visit(dep)
            
            order.append(tool_name)
        
        for context in self.execution_queue:
            visit(context.tool_name)
        
        return order
    
    def clear(self) -> None:
        """清空调度队列"""
        self.execution_queue.clear()
        self.execution_history.clear()
