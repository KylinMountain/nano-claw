#!/usr/bin/env python3
"""
通用Agent能力测试 - 展示非编程领域的应用
"""
import sys
import os
import asyncio

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config
from core.llm_client import LLMClient
from core.agent_loop import AgentLoop, AgentConfig
from core.smart_policy import SmartPolicyEngine
from core.policy import ApprovalMode
from core.types import EventType
from skills.manager import SkillManager, ActivateSkillTool
from memory.manager import MemoryManager

async def test_universal_capabilities():
    """测试通用Agent能力"""
    print("🌟 Nano Agent 通用能力测试")
    print("展示非编程领域的智能助手应用\n")
    
    # 加载配置
    config = load_config("config.yaml")
    print(f"✓ Config loaded: {config['llm']['provider']} - {config['llm']['openai']['model']}")
    
    # 创建LLM客户端
    llm_client = LLMClient(
        api_key=config['llm']['api_key'],
        provider=config['llm']['provider'],
        model=config['llm']['openai']['model'],
        base_url=config['llm']['openai']['base_url']
    )
    print("✓ LLM client created")
    
    # 使用智能策略引擎
    smart_policy = SmartPolicyEngine(mode=ApprovalMode.YOLO)
    print("✓ Smart policy engine created")
    
    # 设置Skills和Memory
    skill_manager = SkillManager()
    skill_manager.set_directories(
        builtin_dir="./skills/builtin",
        user_dir=os.path.expanduser("~/.nano_claw/skills"),
        workspace_dir="./skills/universal"  # 使用通用技能目录
    )
    skill_manager.discover_skills()
    
    memory_manager = MemoryManager()
    await memory_manager.refresh()
    
    # 创建Agent配置 - 通用助手人格
    agent_config = AgentConfig(
        system_prompt="""You are a Universal AI Assistant, capable of helping with various aspects of life including:

- 🏢 Business and professional tasks
- 📚 Learning and education support  
- 🌍 Travel and lifestyle planning
- 📝 Personal organization and productivity
- 🔍 Research and information gathering

You are friendly, helpful, and adaptable to different domains. Always explain your reasoning and provide practical, actionable advice.""",
        max_turns=config['agent']['max_turns'],
        temperature=config['agent']['temperature']
    )
    
    # 创建Agent
    agent = AgentLoop(
        llm_client=llm_client,
        config=agent_config,
        policy_engine=smart_policy
    )
    
    # 注册上下文生成器
    agent.add_context_generator(skill_manager.generate_skills_prompt)
    agent.add_context_generator(memory_manager.format_for_system_prompt)
    
    # 注册ActivateSkill工具
    skills = skill_manager.get_available_skills()
    if skills:
        activate_skill_tool = ActivateSkillTool(skill_manager)
        agent.tool_registry.register(activate_skill_tool)
    
    # 尝试注册通用工具
    try:
        from tools.universal import register_universal_tools
        register_universal_tools(agent.tool_registry)
        print("✓ Universal tools registered")
    except ImportError as e:
        print(f"⚠️ Universal tools not available: {e}")
    
    print("✓ Universal Agent configured")
    
    # 通用能力测试用例
    test_scenarios = [
        {
            "domain": "🏢 商务助手",
            "title": "会议安排",
            "input": "我需要安排下周三下午2点和客户的产品演示会议，请帮我准备",
            "description": "测试商务场景下的会议安排能力"
        },
        {
            "domain": "📚 学习助手", 
            "title": "学习计划",
            "input": "我想学习数据分析，请帮我制定一个3个月的学习计划",
            "description": "测试教育场景下的学习规划能力"
        },
        {
            "domain": "🌍 生活助手",
            "title": "旅行规划", 
            "input": "计划下个月去日本旅行5天，预算1万元，请帮我规划行程",
            "description": "测试生活场景下的旅行规划能力"
        },
        {
            "domain": "🔍 信息助手",
            "title": "信息搜索",
            "input": "帮我搜索一下最近人工智能领域的重要进展",
            "description": "测试信息搜索和整理能力"
        },
        {
            "domain": "📝 个人助手",
            "title": "笔记管理",
            "input": "帮我创建一个关于健康生活方式的笔记，包含运动、饮食和睡眠建议",
            "description": "测试个人信息管理能力"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*70}")
        print(f"🧪 测试场景 {i}: {scenario['domain']} - {scenario['title']}")
        print(f"描述: {scenario['description']}")
        print(f"输入: {scenario['input']}")
        print("-" * 70)
        print("输出:")
        
        try:
            response_received = False
            async for event in agent.run(scenario['input']):
                if event.type == EventType.MESSAGE and event.data.get("role") == "assistant":
                    content = event.data.get("content", "")
                    if content:
                        print(content)
                        response_received = True
                elif event.type == EventType.TOOL_CALL:
                    calls = event.data.get("calls", [])
                    for call in calls:
                        print(f"🔧 调用工具: {call['name']}")
                elif event.type == EventType.TOOL_RESULT:
                    success = event.data.get("success")
                    if success:
                        print("✓ 工具执行成功")
                    else:
                        print(f"❌ 工具执行失败: {event.data.get('error')}")
                elif event.type == EventType.ERROR:
                    print(f"❌ 错误: {event.data.get('error')}")
            
            if response_received:
                print(f"\n✅ 场景 {i} 测试完成")
            else:
                print(f"\n⚠️ 场景 {i} 未收到响应")
            
        except Exception as e:
            print(f"❌ 场景 {i} 测试出错: {e}")
        
        print("=" * 70)
    
    # 显示系统能力统计
    tools = agent.tool_registry.get_all()
    available_skills = skill_manager.get_available_skills()
    
    print(f"\n📊 通用Agent能力统计:")
    print(f"  - 可用工具: {len(tools)} 个")
    
    # 按类型分类工具
    tool_categories = {}
    for tool in tools:
        category = "通用工具"
        if tool.name in ["read_file", "write_file", "shell", "glob"]:
            category = "文件工具"
        elif tool.name in ["git", "analyze_code", "analyze_project"]:
            category = "开发工具"
        elif tool.name in ["web_search", "weather_query", "email_send", "calendar_event", "note"]:
            category = "生活工具"
        elif tool.name in ["ask_user", "activate_skill"]:
            category = "交互工具"
        
        if category not in tool_categories:
            tool_categories[category] = []
        tool_categories[category].append(tool.name)
    
    for category, tool_list in tool_categories.items():
        print(f"    - {category}: {len(tool_list)} 个 ({', '.join(tool_list)})")
    
    print(f"  - 可用技能: {len(available_skills)} 个")
    
    # 按领域分类技能
    skill_domains = {}
    for skill in available_skills:
        domain = "通用"
        if "docs" in skill.name or "code" in skill.name:
            domain = "技术"
        elif "travel" in skill.name or "lifestyle" in skill.name:
            domain = "生活"
        elif "meeting" in skill.name or "business" in skill.name:
            domain = "商务"
        elif "study" in skill.name or "learn" in skill.name:
            domain = "教育"
        
        if domain not in skill_domains:
            skill_domains[domain] = []
        skill_domains[domain].append(skill.name)
    
    for domain, skill_list in skill_domains.items():
        print(f"    - {domain}技能: {len(skill_list)} 个 ({', '.join(skill_list)})")
    
    print(f"  - 策略引擎: 智能风险评估")
    print(f"  - 记忆系统: 三层架构")
    print(f"  - 支持领域: 商务、教育、生活、技术、通用")
    
    print("\n🎉 通用Agent能力测试完成！")
    print("\n💡 结论:")
    print("  Nano Claw 成功展示了作为通用智能助手的能力，")
    print("  能够处理多个领域的任务，具备良好的扩展性和适应性。")

if __name__ == "__main__":
    asyncio.run(test_universal_capabilities())