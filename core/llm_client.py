"""
LLM客户端 - 支持OpenAI和Gemini API
模仿Gemini CLI的GeminiClient
"""
import os
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from .types import Message, ToolSchema


class LLMClient:
    """LLM客户端封装"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        provider: str = "openai"
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        # 支持Gemini API (OpenAI兼容模式)
        if provider == "gemini":
            base_url = base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )
    
    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolSchema]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Message:
        """生成非流式响应"""
        # 构建消息列表
        msgs: List[ChatCompletionMessageParam] = []
        
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            msg_dict = msg.to_dict()
            # 处理工具调用消息
            if msg.role == "tool":
                msgs.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "",
                    "content": msg.content or ""
                })
            elif msg.tool_calls:
                msgs.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": msg.tool_calls
                })
            else:
                msgs.append({"role": msg.role, "content": msg.content or ""})
        
        # 构建工具定义
        openai_tools = None
        if tools:
            openai_tools = [t.to_dict() for t in tools]
        
        # 调用API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=msgs,
            tools=openai_tools,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_choice="auto" if tools else None
        )
        
        # 解析响应
        choice = response.choices[0]
        message = choice.message
        
        # 构建返回消息
        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        return Message(
            role="assistant",
            content=message.content,
            tool_calls=tool_calls
        )
    
    async def generate_stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolSchema]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """生成流式响应"""
        msgs: List[ChatCompletionMessageParam] = []
        
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            if msg.role == "tool":
                msgs.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "",
                    "content": msg.content or ""
                })
            else:
                msgs.append({"role": msg.role, "content": msg.content or ""})
        
        openai_tools = None
        if tools:
            openai_tools = [t.to_dict() for t in tools]
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=msgs,
            tools=openai_tools,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_choice="auto" if tools else None,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def compress_history(
        self,
        messages: List[Message],
        prompt: str = "Summarize the conversation history concisely."
    ) -> str:
        """压缩历史记录"""
        compression_prompt = f"""You are a conversation compression assistant.

{prompt}

Please provide a concise summary maintaining:
- Key decisions made
- Important context
- Current task state
- Any errors or blockers encountered

Conversation to summarize:
"""
        
        # 将消息转换为文本
        conversation = "\n\n".join([
            f"{msg.role}: {msg.content}" 
            for msg in messages 
            if msg.content
        ])
        
        summary_messages = [
            Message(role="user", content=compression_prompt + conversation)
        ]
        
        response = await self.generate(summary_messages, temperature=0.3)
        return response.content or ""


class ConversationCompressor:
    """会话压缩器"""
    
    def __init__(
        self,
        llm_client: LLMClient,
        max_messages: int = 50,
        max_tokens: int = 10000
    ):
        self.llm_client = llm_client
        self.max_messages = max_messages
        self.max_tokens = max_tokens
    
    def should_compress(self, messages: List[Message]) -> bool:
        """判断是否需要压缩"""
        # 消息数量检查
        if len(messages) > self.max_messages:
            return True
        
        # Token数量估算 (简单估算：每4个字符约1个token)
        total_chars = sum(len(str(m.content or "")) for m in messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens > self.max_tokens:
            return True
        
        return False
    
    async def compress(self, messages: List[Message]) -> List[Message]:
        """压缩历史记录"""
        if not self.should_compress(messages):
            return messages
        
        # 保留最近的消息
        keep_recent = 10
        to_compress = messages[:-keep_recent]
        recent = messages[-keep_recent:]
        
        # 生成摘要
        summary = await self.llm_client.compress_history(to_compress)
        
        # 构建压缩后的历史
        compressed = [
            Message(
                role="system",
                content=f"## Previous Context Summary\n\n{summary}"
            ),
            *recent
        ]
        
        return compressed