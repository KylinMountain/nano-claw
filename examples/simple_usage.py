"""
Nano Claw 简单使用示例
"""
import asyncio
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client import LLMClient
from core.agent_loop import AgentLoop, AgentConfig
from core.policy import PolicyEngine, ApprovalMode
from core.types import EventType


async def main():
    """简单示例"""
    # 检查 API 密钥
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("请设置 OPENAI_API_KEY 或 GEMINI_API_KEY 环境变量")
        return
    
    # 创建 LLM 客户端
    provider = "gemini" if os.getenv("GEMINI_API_KEY") else "openai"
    model = "gemini-2.0-flash" if provider == "gemini" else "gpt-4o-mini"
    
    llm = LLMClient(
        api_key=api_key,
        provider=provider,
        model=model
    )
    
    # 配置 Agent
    config = AgentConfig(
        system_prompt="""You are a helpful assistant with access to tools.
When using tools, explain your intent first.""",
        max_turns=10,
        temperature=0.7
    )
    
    # 创建策略引擎（默认模式）
    policy = PolicyEngine(mode=ApprovalMode.DEFAULT)
    
    # 创建 Agent
    agent = AgentLoop(
        llm_client=llm,
        config=config,
        policy_engine=policy
    )
    
    # 定义事件处理器
    def on_message(event):
        data = event.data
        if data.get("role") == "assistant" and data.get("content"):
            print(f"\n🤖 Assistant: {data['content']}")
    
    def on_tool_call(event):
        calls = event.data.get("calls", [])
        for call in calls:
            print(f"\n🔧 Calling tool: {call['name']}")
            print(f"   Arguments: {call['arguments']}")
    
    def on_tool_result(event):
        data = event.data
        if data.get("success"):
            print(f"\n✅ Tool result: {data['content'][:200]}...")
        else:
            print(f"\n❌ Tool error: {data.get('error')}")
    
    def on_thinking(event):
        if event.data.get("message"):
            print(f"\n💭 {event.data['message']}")
    
    # 注册事件处理器
    agent.event_bus.on(EventType.MESSAGE, on_message)
    agent.event_bus.on(EventType.TOOL_CALL, on_tool_call)
    agent.event_bus.on(EventType.TOOL_RESULT, on_tool_result)
    agent.event_bus.on(EventType.THINKING, on_thinking)
    
    # 运行对话
    user_input = "请读取当前目录下的 README.md 文件并总结一下内容"
    print(f"\n👤 User: {user_input}\n")
    
    async for event in agent.run(user_input):
        # 事件由处理器处理
        pass
    
    print("\n" + "="*50)
    print("对话完成！")


if __name__ == "__main__":
    asyncio.run(main())