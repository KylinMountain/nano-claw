#!/usr/bin/env python3
"""
Nano Agent 演示脚本
展示系统的主要功能
"""
import sys
import os
import asyncio

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config
from core.llm_client import LLMClient
from core.agent_loop import AgentLoop, AgentConfig
from core.policy import PolicyEngine, ApprovalMode
from core.types import EventType
from skills.manager import SkillManager, ActivateSkillTool
from memory.manager import MemoryManager

class NanoAgentDemo:
    """Nano Agent 演示类"""
    
    def __init__(self):
        self.agent = None
        self.skill_manager = None
        self.memory_manager = None
    
    async def setup(self):
        """初始化系统"""
        print("🤖 Nano Claw Demo - Setting up...\n")
        
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
        
        # 设置记忆系统
        self.memory_manager = MemoryManager()
        await self.memory_manager.refresh()
        print("✓ Memory system initialized")
        
        # 设置Skills
        self.skill_manager = SkillManager()
        self.skill_manager.set_directories(
            builtin_dir="./skills/builtin",
            user_dir=os.path.expanduser("~/.nano_claw/skills"),
            workspace_dir=".nano_claw/skills"
        )
        self.skill_manager.discover_skills()
        skills = self.skill_manager.get_available_skills()
        print(f"✓ Skills system loaded: {len(skills)} skills")
        
        # 创建Agent配置
        agent_config = AgentConfig(
            system_prompt=config['system_prompt'],
            max_turns=config['agent']['max_turns'],
            temperature=config['agent']['temperature']
        )
        
        # 创建策略引擎（演示模式使用YOLO）
        policy = PolicyEngine(mode=ApprovalMode.YOLO)
        
        # 创建Agent
        self.agent = AgentLoop(
            llm_client=llm_client,
            config=agent_config,
            policy_engine=policy
        )
        
        # 注册上下文生成器
        self.agent.add_context_generator(self.skill_manager.generate_skills_prompt)
        self.agent.add_context_generator(self.memory_manager.format_for_system_prompt)
        
        # 注册ActivateSkill工具
        if skills:
            activate_skill_tool = ActivateSkillTool(self.skill_manager)
            self.agent.tool_registry.register(activate_skill_tool)
        
        print("✓ Agent fully configured\n")
    
    async def run_demo(self):
        """运行演示"""
        print("=" * 60)
        print("🎯 Nano Claw 功能演示")
        print("=" * 60)
        
        demos = [
            {
                "title": "1. 基本对话能力",
                "input": "你好！请介绍一下你自己和你的能力。",
                "description": "测试基本的对话和自我介绍能力"
            },
            {
                "title": "2. 工具使用能力",
                "input": "请帮我查看当前目录下有哪些文件？",
                "description": "测试文件系统工具的使用"
            },
            {
                "title": "3. Skills系统",
                "input": "请激活docs-writer技能，然后帮我写一个Python项目的README模板。",
                "description": "测试Skills系统的渐进式披露功能"
            },
            {
                "title": "4. 文件操作能力",
                "input": "请创建一个名为demo_output.txt的文件，内容是'Nano Claw演示成功！'",
                "description": "测试文件写入功能"
            }
        ]
        
        for demo in demos:
            print(f"\n{demo['title']}")
            print(f"描述: {demo['description']}")
            print(f"输入: {demo['input']}")
            print("-" * 50)
            print("输出:")
            
            try:
                async for event in self.agent.run(demo['input']):
                    if event.type == EventType.MESSAGE and event.data.get("role") == "assistant":
                        content = event.data.get("content", "")
                        if content:
                            print(content)
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
                
                print("\n✓ 演示完成")
                
            except Exception as e:
                print(f"❌ 演示出错: {e}")
            
            print("=" * 60)
        
        print("\n🎉 所有演示完成！")
        print("\n📊 系统统计:")
        print(f"  - 可用工具: {len(self.agent.tool_registry.get_all())} 个")
        print(f"  - 可用技能: {len(self.skill_manager.get_available_skills())} 个")
        print(f"  - 对话轮数: {self.agent.current_turn} 轮")
        
        # 检查是否创建了演示文件
        if os.path.exists("demo_output.txt"):
            print("  - 文件操作: ✓ 成功创建演示文件")
        else:
            print("  - 文件操作: ❌ 未创建演示文件")

async def main():
    """主函数"""
    demo = NanoAgentDemo()
    await demo.setup()
    await demo.run_demo()

if __name__ == "__main__":
    asyncio.run(main())