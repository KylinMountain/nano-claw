"""
Nano Agent CLI - 命令行界面
"""
import asyncio
import os
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from core.llm_client import LLMClient
from core.agent_loop import AgentLoop, AgentConfig
from core.policy import PolicyEngine, ApprovalMode
from core.types import EventType
from skills.manager import SkillManager, ActivateSkillTool
from memory.manager import MemoryManager, ProjectContextExtractor


# 自定义样式
style = Style.from_dict({
    'prompt': '#00aa00 bold',
    'hint': '#666666',
})


class NanoClawCLI:
    """Nano Claw命令行界面"""
    
    def __init__(self):
        self.console = Console()
        self.session = PromptSession(style=style)
        self.agent: Optional[AgentLoop] = None
        self.skill_manager = SkillManager()
        self.memory_manager: Optional[MemoryManager] = None
        self.project_extractor: Optional[ProjectContextExtractor] = None
    
    def print_banner(self):
        """打印欢迎信息"""
        banner = """
╭────────────────────────────────────────────────────────────╮
│                                                            │
│   Nano Claw - Python Agent System                         │
│   Inspired by Google Gemini CLI                            │
│                                                            │
│   Features:                                                │
│   • Agent Loop with Tool Calling                           │
│   • MCP (Model Context Protocol)                           │
│   • Skills System (Progressive Disclosure)                 │
│   • Memory System (GEMINI.md)                              │
│   • Human-in-the-Loop                                      │
│                                                            │
╰────────────────────────────────────────────────────────────╯
        """
        self.console.print(banner, style="cyan")
    
    async def setup(self):
        """初始化设置"""
        # 检查API密钥
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.console.print("[red]Error: Please set OPENAI_API_KEY or GEMINI_API_KEY environment variable[/red]")
            sys.exit(1)
        
        # 初始化组件
        provider = "gemini" if os.getenv("GEMINI_API_KEY") else "openai"
        model = "gemini-2.0-flash" if provider == "gemini" else "gpt-4o-mini"
        
        llm_client = LLMClient(
            api_key=api_key,
            provider=provider,
            model=model
        )
        
        # 设置记忆系统
        self.memory_manager = MemoryManager()
        await self.memory_manager.refresh()
        
        # 设置项目上下文
        self.project_extractor = ProjectContextExtractor()
        
        # 设置Skills
        user_home = os.path.expanduser("~")
        self.skill_manager.set_directories(
            builtin_dir=os.path.join(os.path.dirname(__file__), "skills", "builtin"),
            user_dir=os.path.join(user_home, ".nano_claw", "skills"),
            workspace_dir=os.path.join(".nano_claw", "skills")
        )
        self.skill_manager.discover_skills()
        
        # 配置Agent
        config = AgentConfig(
            system_prompt="""You are Nano Claw, a helpful AI assistant with access to tools.

When using tools:
1. Explain your intent before calling a tool
2. Use the exact tool name and parameters
3. Wait for results before proceeding
4. Report the outcome to the user

Be concise but thorough in your responses.""",
            max_turns=50,
            temperature=0.7
        )
        
        policy = PolicyEngine(mode=ApprovalMode.DEFAULT)
        
        self.agent = AgentLoop(
            llm_client=llm_client,
            config=config,
            policy_engine=policy
        )
        
        # 注册Skills上下文
        self.agent.add_context_generator(self.skill_manager.generate_skills_prompt)
        self.agent.add_context_generator(self.memory_manager.format_for_system_prompt)
        
        # 注册ActivateSkill工具
        if self.skill_manager.get_available_skills():
            activate_skill_tool = ActivateSkillTool(self.skill_manager)
            self.agent.tool_registry.register(activate_skill_tool)
        
        # 监听事件
        self.agent.event_bus.on(EventType.MESSAGE, self._on_message)
        self.agent.event_bus.on(EventType.TOOL_CALL, self._on_tool_call)
        self.agent.event_bus.on(EventType.TOOL_RESULT, self._on_tool_result)
        self.agent.event_bus.on(EventType.TOOL_CONFIRMATION_REQUEST, self._on_confirmation_request)
        self.agent.event_bus.on(EventType.ERROR, self._on_error)
        self.agent.event_bus.on(EventType.THINKING, self._on_thinking)
    
    async def _on_message(self, event):
        """处理消息事件"""
        data = event.data
        if data.get("role") == "assistant" and data.get("content"):
            self.console.print(Markdown(data["content"]))
    
    async def _on_tool_call(self, event):
        """处理工具调用事件"""
        calls = event.data.get("calls", [])
        for call in calls:
            self.console.print(
                f"[dim]🔧 Calling tool: {call['name']}[/dim]",
                highlight=False
            )
    
    async def _on_tool_result(self, event):
        """处理工具结果事件"""
        data = event.data
        if not data.get("success"):
            self.console.print(f"[red]Tool error: {data.get('error')}[/red]")
    
    async def _on_confirmation_request(self, event):
        """处理确认请求"""
        details = event.data.get("details", {})
        
        self.console.print(Panel(
            details.get("prompt", "Confirm action?"),
            title=details.get("title", "Confirmation Required"),
            border_style="yellow"
        ))
        
        # 简单确认
        response = await self.session.prompt_async("Proceed? [y/N]: ")
        approved = response.strip().lower() in ('y', 'yes')
        
        # 响应确认
        call_id = event.data.get("call_id")
        self.agent.respond_to_confirmation(call_id, approved)
    
    async def _on_error(self, event):
        """处理错误事件"""
        self.console.print(f"[red]Error: {event.data.get('error')}[/red]")
    
    async def _on_thinking(self, event):
        """处理思考事件"""
        if event.data.get("message"):
            self.console.print(f"[dim]{event.data['message']}[/dim]")
    
    async def run_interactive(self):
        """运行交互式会话"""
        self.print_banner()
        
        # 显示加载的Skills
        skills = self.skill_manager.get_available_skills()
        if skills:
            self.console.print(f"[green]✓ Loaded {len(skills)} skills[/green]")
            for skill in skills:
                self.console.print(f"  • {skill.name}: {skill.description[:50]}...")
        
        # 显示记忆
        memory = self.memory_manager.get_environment_memory()
        if memory:
            self.console.print(f"[green]✓ Loaded project context from GEMINI.md[/green]")
        
        self.console.print("\n[dim]Type /help for commands, /exit to quit[/dim]\n")
        
        while True:
            try:
                user_input = await self.session.prompt_async("You: ", style="class:prompt")
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.startswith('/'):
                    if await self._handle_command(user_input):
                        break
                    continue
                
                # 运行Agent
                self.console.print("\n[dim]Assistant thinking...[/dim]\n")
                
                async for event in self.agent.run(user_input):
                    pass  # 事件由事件处理器处理
                
                self.console.print()  # 空行分隔
                
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    async def _handle_command(self, command: str) -> bool:
        """处理命令，返回True表示退出"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == '/exit' or cmd == '/quit':
            self.console.print("[green]Goodbye![/green]")
            return True
        
        elif cmd == '/help':
            help_text = """
# Available Commands

- `/exit`, `/quit` - Exit the application
- `/help` - Show this help message
- `/skills` - List available skills
- `/skills enable <name>` - Enable a skill
- `/skills disable <name>` - Disable a skill
- `/clear` - Clear conversation history
- `/mode <plan|default|yolo>` - Change approval mode
            """
            self.console.print(Markdown(help_text))
        
        elif cmd == '/skills':
            skills = self.skill_manager.get_available_skills()
            if not skills:
                self.console.print("[yellow]No skills available[/yellow]")
            else:
                self.console.print("[bold]Available Skills:[/bold]")
                for skill in skills:
                    status = "🟢" if skill.active else "⚪"
                    self.console.print(f"{status} {skill.name}: {skill.description[:60]}...")
        
        elif cmd == '/clear':
            self.agent.clear_history()
            self.console.print("[green]Conversation history cleared[/green]")
        
        elif cmd == '/mode' and args:
            mode_map = {
                'plan': ApprovalMode.PLAN,
                'default': ApprovalMode.DEFAULT,
                'yolo': ApprovalMode.YOLO
            }
            mode = mode_map.get(args[0].lower())
            if mode:
                self.agent.policy.set_mode(mode)
                self.console.print(f"[green]Mode changed to: {args[0]}[/green]")
            else:
                self.console.print(f"[red]Unknown mode: {args[0]}[/red]")
        
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
        
        return False


async def main():
    """主入口"""
    cli = NanoClawCLI()
    await cli.setup()
    await cli.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())