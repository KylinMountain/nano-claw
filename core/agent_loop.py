"""
Agent Loop - 核心循环架构
模仿Gemini CLI的CoderAgentExecutor和AgentLoop
"""
import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .types import (
    LoopState, Message, ToolCallRequest, ToolResult, AgentEvent,
    EventType, EventHandler, ToolSchema
)
from .llm_client import LLMClient, ConversationCompressor
from .policy import PolicyEngine, ConfirmationManager, PolicyDecision
from tools.base import ToolRegistry, ToolScheduler, MUTATOR_KINDS
from tools.builtin import register_builtin_tools


@dataclass
class AgentConfig:
    """Agent配置"""
    system_prompt: str = "You are a helpful AI assistant."
    max_turns: int = 100
    temperature: float = 0.7
    enable_compression: bool = True
    auto_approve_readonly: bool = True


class EventBus:
    """事件总线 - 解耦组件通信"""
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
    
    def on(self, event_type: str, handler: EventHandler) -> None:
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def off(self, event_type: str, handler: EventHandler) -> None:
        """取消订阅"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    async def emit(self, event: AgentEvent) -> None:
        """发布事件"""
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Error in event handler: {e}")


class AgentLoop:
    """
    Agent主循环
    
    核心流程:
    1. 接收用户输入
    2. 构建上下文（系统提示词 + 历史 + 记忆）
    3. 调用LLM
    4. 解析响应（内容或工具调用）
    5. 执行工具调用
    6. 将结果送回LLM，继续循环
    7. 直到没有更多工具调用，返回最终结果
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        config: AgentConfig = None,
        policy_engine: Optional[PolicyEngine] = None
    ):
        self.llm = llm_client
        self.config = config or AgentConfig()
        self.policy = policy_engine or PolicyEngine()
        
        # 组件
        self.tool_registry = ToolRegistry()
        self.tool_scheduler = ToolScheduler(self.tool_registry)
        self.confirmation_manager = ConfirmationManager()
        self.event_bus = EventBus()
        self.compressor = ConversationCompressor(llm_client)
        
        # 状态
        self.state = LoopState.IDLE
        self.history: List[Message] = []
        self.max_turns = self.config.max_turns
        self.current_turn = 0
        
        # 注册内置工具
        register_builtin_tools(self.tool_registry)
        
        # 额外上下文生成器
        self._context_generators: List[Callable[[], str]] = []
    
    def add_context_generator(self, generator: Callable[[], str]) -> None:
        """添加上下文生成器（用于注入Skills、Memory等）"""
        self._context_generators.append(generator)
    
    def _build_system_prompt(self) -> str:
        """构建完整系统提示词"""
        parts = [self.config.system_prompt]
        
        # 添加额外上下文
        for generator in self._context_generators:
            context = generator()
            if context:
                parts.append(context)
        
        # 添加工具使用说明
        parts.append("""
## Tool Usage Guidelines

You have access to various tools. When you need to use a tool:
1. Explain your intent before calling the tool
2. Use the exact tool name and parameters
3. Wait for the tool result before proceeding

Available tools are provided in the function definitions.""")
        
        return "\n\n".join(parts)
    
    async def run(self, user_input: str) -> AsyncIterator[AgentEvent]:
        """
        运行Agent循环
        
        Yields:
            AgentEvent: 各种事件（消息、工具调用、状态变化等）
        """
        if self.state == LoopState.RUNNING:
            yield AgentEvent(
                type=EventType.ERROR,
                data={"error": "Agent is already running"}
            )
            return
        
        self.state = LoopState.RUNNING
        yield AgentEvent(type=EventType.STATE_CHANGE, data={"state": "running"})
        
        # 添加用户输入到历史
        self.history.append(Message(role="user", content=user_input))
        yield AgentEvent(
            type=EventType.MESSAGE,
            data={"role": "user", "content": user_input}
        )
        
        try:
            agent_turn_active = True
            
            while agent_turn_active and self.current_turn < self.max_turns:
                self.current_turn += 1
                
                # 1. 检查是否需要压缩历史
                if self.config.enable_compression and self.compressor.should_compress(self.history):
                    yield AgentEvent(
                        type=EventType.THINKING,
                        data={"message": "Compressing conversation history..."}
                    )
                    self.history = await self.compressor.compress(self.history)
                
                # 2. 构建系统提示词
                system_prompt = self._build_system_prompt()
                
                # 3. 获取工具Schema
                tools = self.tool_registry.get_all_schemas()
                
                # 4. 调用LLM
                yield AgentEvent(
                    type=EventType.THINKING,
                    data={"message": "Thinking..."}
                )
                
                response = await self.llm.generate(
                    messages=self.history,
                    tools=tools if tools else None,
                    system_prompt=system_prompt,
                    temperature=self.config.temperature
                )
                
                # 5. 处理响应
                if response.content:
                    yield AgentEvent(
                        type=EventType.MESSAGE,
                        data={"role": "assistant", "content": response.content}
                    )
                
                # 6. 检查是否有工具调用
                if response.tool_calls:
                    # 解析工具调用
                    tool_requests = []
                    for tc in response.tool_calls:
                        func = tc.get("function", {})
                        tool_requests.append(ToolCallRequest(
                            id=tc.get("id", str(uuid.uuid4())),
                            name=func.get("name", ""),
                            arguments=json.loads(func.get("arguments", "{}"))
                        ))
                    
                    yield AgentEvent(
                        type=EventType.TOOL_CALL,
                        data={"calls": [t.__dict__ for t in tool_requests]}
                    )
                    
                    # 添加助手消息（包含工具调用）到历史
                    self.history.append(Message(
                        role="assistant",
                        content=response.content,
                        tool_calls=response.tool_calls
                    ))
                    
                    # 7. 执行工具调用
                    results = await self._execute_tool_calls(tool_requests)
                    
                    # 8. 将结果添加到历史
                    for result in results:
                        self.history.append(Message(
                            role="tool",
                            content=result.content if result.success else result.error,
                            tool_call_id=result.call_id
                        ))
                        
                        yield AgentEvent(
                            type=EventType.TOOL_RESULT,
                            data={
                                "call_id": result.call_id,
                                "success": result.success,
                                "content": result.content,
                                "error": result.error
                            }
                        )
                    
                    # 继续循环
                    continue
                
                # 没有工具调用，结束本轮
                agent_turn_active = False
                
                # 添加助手消息到历史
                self.history.append(Message(
                    role="assistant",
                    content=response.content
                ))
            
            # 循环结束
            self.state = LoopState.COMPLETED
            yield AgentEvent(
                type=EventType.COMPLETION,
                data={"turns": self.current_turn}
            )
            
        except Exception as e:
            self.state = LoopState.ERROR
            yield AgentEvent(
                type=EventType.ERROR,
                data={"error": str(e)}
            )
        finally:
            self.current_turn = 0
            if self.state == LoopState.RUNNING:
                self.state = LoopState.IDLE
            yield AgentEvent(
                type=EventType.STATE_CHANGE,
                data={"state": self.state.value}
            )
    
    async def _execute_tool_calls(
        self,
        requests: List[ToolCallRequest]
    ) -> List[ToolResult]:
        """执行工具调用（带确认流程）"""
        results = []
        
        for request in requests:
            # 获取工具
            tool = self.tool_registry.get(request.name)
            if not tool:
                results.append(ToolResult(
                    call_id=request.id,
                    success=False,
                    content="",
                    error=f"Tool '{request.name}' not found"
                ))
                continue
            
            # 策略检查
            is_mutator = tool.kind in MUTATOR_KINDS
            decision = self.policy.check(
                request.name,
                tool.kind,
                request.arguments,
                is_mutator
            )
            
            if decision == PolicyDecision.DENY:
                results.append(ToolResult(
                    call_id=request.id,
                    success=False,
                    content="",
                    error=f"Tool '{request.name}' is not allowed by policy"
                ))
                continue
            
            # 创建调用实例
            invocation = self.tool_registry.create_invocation(
                request.id,
                request.name,
                request.arguments
            )
            
            # 需要确认
            if decision == PolicyDecision.ASK_USER and invocation:
                details = None
                if hasattr(invocation, 'get_confirmation_details'):
                    details = invocation.get_confirmation_details()
                # 对没有专门确认详情的工具，生成兜底确认信息，避免绕过 ASK_USER。
                if not details:
                    affected_locations = []
                    if hasattr(invocation, 'get_affected_locations'):
                        try:
                            affected_locations = invocation.get_affected_locations()
                        except Exception:
                            affected_locations = []
                    details = type("ConfirmationDetailsShim", (), {
                        "title": f"Confirm tool: {request.name}",
                        "prompt": self.policy.generate_confirmation_prompt(
                            request.name,
                            request.arguments,
                            affected_locations
                        ),
                        "tool_name": request.name,
                        "arguments": request.arguments,
                    })()
                
                # 发送确认请求事件
                loop = asyncio.get_running_loop()
                future = loop.create_future()

                def on_response(approved: bool, outcome: str):
                    if not future.done():
                        future.set_result(approved)

                # 先注册，再发事件，避免“瞬时响应”竞态丢失。
                self.confirmation_manager.request_confirmation(
                    request.id,
                    None,
                    on_response
                )

                await self.event_bus.emit(AgentEvent(
                    type=EventType.TOOL_CONFIRMATION_REQUEST,
                    data={
                        "call_id": request.id,
                        "details": {
                            "title": details.title,
                            "prompt": details.prompt,
                            "tool_name": details.tool_name,
                            "arguments": details.arguments
                        }
                    }
                ))
                
                # 等待确认（这里简化处理，实际应该等待用户输入）
                # 在真实实现中，这会暂停并等待UI层返回确认结果
                try:
                    confirmed = await asyncio.wait_for(future, timeout=300)
                except asyncio.TimeoutError:
                    confirmed = False
                
                if not confirmed:
                    results.append(ToolResult(
                        call_id=request.id,
                        success=False,
                        content="",
                        error="User cancelled"
                    ))
                    continue
            
            # 执行工具
            cancel_event = asyncio.Event()
            result = await invocation.execute(cancel_event)
            results.append(result)
        
        return results
    
    async def _wait_for_confirmation(self, call_id: str) -> bool:
        """等待用户确认（简化实现）"""
        # 实际实现中，这会等待UI层的确认响应
        # 使用asyncio.create_future确保兼容性
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        
        def on_response(approved: bool, outcome: str):
            if not future.done():
                future.set_result(approved)
        
        self.confirmation_manager.request_confirmation(
            call_id,
            None,  # details会在上面发送
            on_response
        )
        
        try:
            # 5分钟超时
            return await asyncio.wait_for(future, timeout=300)
        except asyncio.TimeoutError:
            return False
    
    def respond_to_confirmation(self, call_id: str, approved: bool) -> bool:
        """响应对话确认"""
        return self.confirmation_manager.respond(call_id, approved)
    
    def get_history(self) -> List[Message]:
        """获取对话历史"""
        return self.history.copy()
    
    def clear_history(self) -> None:
        """清除对话历史"""
        self.history.clear()
    
    def stop(self) -> None:
        """停止Agent"""
        self.state = LoopState.IDLE
        self.confirmation_manager.cancel_all()
