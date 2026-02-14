"""
Nano Agent 主入口 - 支持配置文件
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from config_loader import load_config
from core.llm_client import LLMClient
from core.agent_loop import AgentLoop, AgentConfig
from core.policy import PolicyEngine, ApprovalMode
from core.types import EventType
from skills.manager import SkillManager, ActivateSkillTool
from memory.manager import MemoryManager
from mcp_client.client import MCPManager, MCPServerConfig


console = Console()


class NanoAgentApp:
    """Nano Agent 应用程序"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.agent = None
        self.skill_manager = None
        self.memory_manager = None
        self.mcp_manager = None
    
    def print_banner(self):
        """打印欢迎信息"""
        provider = self.config['llm']['provider']
        model = self.config['llm'][provider]['model']
        
        banner = f"""
╭────────────────────────────────────────────────────────────╮
│                                                            │
│   🤖 Nano Claw - Python Agent System                      │
│   LLM: {provider.upper():10} | Model: {model:20}   │
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
        console.print(banner, style="cyan")
    
    async def setup(self):
        """初始化设置"""
        # 检查API密钥
        api_key = self.config['llm'].get('api_key')
        if not api_key:
            console.print("[red]Error: API key not found![/red]")
            console.print("\nPlease set one of the following:")
            console.print("  1. Environment variable: OPENAI_API_KEY or GEMINI_API_KEY")
            console.print("  2. Add api_key to config.yaml")
            return False
        
        # 创建 LLM 客户端
        provider = self.config['llm']['provider']
        provider_config = self.config['llm'][provider]
        
        llm_client = LLMClient(
            api_key=api_key,
            provider=provider,
            model=provider_config['model'],
            base_url=provider_config.get('base_url')
        )
        
        # 设置记忆系统
        if self.config['memory']['enabled']:
            global_dir = self.config['memory'].get('global_dir', '~/.nano_claw')
            self.memory_manager = MemoryManager()
            self.memory_manager.global_memory_path = Path(global_dir).expanduser() / "memory.md"
            await self.memory_manager.refresh()
        
        # 设置Skills
        if self.config['skills']['enabled']:
            dirs = self.config['skills']['directories']
            self.skill_manager = SkillManager()
            self.skill_manager.set_directories(
                builtin_dir=dirs.get('builtin'),
                user_dir=dirs.get('user'),
                workspace_dir=dirs.get('workspace')
            )
            self.skill_manager.discover_skills()
        
        # 设置MCP
        if self.config['mcp']['enabled']:
            self.mcp_manager = MCPManager()
            for server_name, server_config in self.config['mcp']['servers'].items():
                mcp_config = MCPServerConfig(
                    name=server_name,
                    command=server_config.get('command'),
                    args=server_config.get('args', []),
                    env=server_config.get('env', {})
                )
                success = await self.mcp_manager.add_server(mcp_config)
                if success:
                    console.print(f"[green]✓ MCP server connected: {server_name}[/green]")
                else:
                    console.print(f"[red]✗ MCP server failed: {server_name}[/red]")
        
        # 配置Agent
        agent_config = AgentConfig(
            system_prompt=self.config['system_prompt'],
            max_turns=self.config['agent']['max_turns'],
            temperature=self.config['agent']['temperature'],
            enable_compression=self.config['agent']['enable_compression'],
            auto_approve_readonly=self.config['agent']['auto_approve_readonly']
        )
        
        # 设置批准模式
        mode_map = {
            'plan': ApprovalMode.PLAN,
            'default': ApprovalMode.DEFAULT,
            'yolo': ApprovalMode.YOLO,
            'read_only': ApprovalMode.READ_ONLY
        }
        approval_mode = mode_map.get(
            self.config['agent']['approval_mode'],
            ApprovalMode.DEFAULT
        )
        policy = PolicyEngine(mode=approval_mode)
        
        # 创建Agent
        self.agent = AgentLoop(
            llm_client=llm_client,
            config=agent_config,
            policy_engine=policy
        )
        
        # 注册上下文生成器
        if self.skill_manager:
            self.agent.add_context_generator(self.skill_manager.generate_skills_prompt)
        if self.memory_manager:
            self.agent.add_context_generator(self.memory_manager.format_for_system_prompt)
        
        # 注册ActivateSkill工具
        if self.skill_manager and self.skill_manager.get_available_skills():
            activate_skill_tool = ActivateSkillTool(self.skill_manager)
            self.agent.tool_registry.register(activate_skill_tool)
        
        # 注册MCP工具
        if self.mcp_manager:
            for adapter in self.mcp_manager.get_adapters():
                self.agent.tool_registry.register(adapter)
        
        # 监听事件
        self.agent.event_bus.on(EventType.MESSAGE, self._on_message)
        self.agent.event_bus.on(EventType.TOOL_CALL, self._on_tool_call)
        self.agent.event_bus.on(EventType.TOOL_RESULT, self._on_tool_result)
        self.agent.event_bus.on(EventType.TOOL_CONFIRMATION_REQUEST, self._on_confirmation_request)
        self.agent.event_bus.on(EventType.ERROR, self._on_error)
        self.agent.event_bus.on(EventType.THINKING, self._on_thinking)
        
        return True
    
    async def _on_message(self, event):
        data = event.data
        if data.get("role") == "assistant" and data.get("content"):
            console.print(Markdown(data["content"]))
    
    async def _on_tool_call(self, event):
        calls = event.data.get("calls", [])
        for call in calls:
            console.print(f"[dim]🔧 Calling: {call['name']}[/dim]")
    
    async def _on_tool_result(self, event):
        data = event.data
        if not data.get("success"):
            console.print(f"[red]Error: {data.get('error')}[/red]")
    
    async def _on_error(self, event):
        console.print(f"[red]Error: {event.data.get('error')}[/red]")
    
    async def _on_thinking(self, event):
        if event.data.get("message"):
            console.print(f"[dim]{event.data['message']}[/dim]")

    async def _on_confirmation_request(self, event):
        """处理工具确认请求"""
        details = event.data.get("details", {})
        title = details.get("title", "Confirmation Required")
        prompt = details.get("prompt", "Do you want to proceed?")
        call_id = event.data.get("call_id")

        console.print(Panel(prompt, title=title, border_style="yellow"))
        response = await asyncio.to_thread(input, "Proceed? [y/N]: ")
        approved = response.strip().lower() in ("y", "yes")
        self.agent.respond_to_confirmation(call_id, approved)
    
    async def run_interactive(self):
        """运行交互式会话"""
        self.print_banner()
        
        # 初始化
        if not await self.setup():
            return
        
        # 显示加载状态
        if self.skill_manager:
            skills = self.skill_manager.get_available_skills()
            console.print(f"[green]✓ {len(skills)} skills loaded[/green]")
        
        if self.memory_manager:
            memory = self.memory_manager.get_environment_memory()
            if memory:
                console.print(f"[green]✓ Project context loaded[/green]")
        
        console.print("\n[dim]Type /help for commands, /exit to quit[/dim]\n")
        
        while True:
            try:
                # 使用简单的input代替prompt_toolkit
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith('/'):
                    if await self._handle_command(user_input):
                        break
                    continue
                
                # 运行Agent
                console.print("\n[dim]Assistant thinking...[/dim]\n")
                
                async for event in self.agent.run(user_input):
                    # 处理事件（这里之前被忽略了！）
                    if event.type == EventType.MESSAGE and event.data.get("role") == "assistant":
                        content = event.data.get("content", "")
                        if content:
                            console.print(content)
                    elif event.type == EventType.TOOL_CALL:
                        calls = event.data.get("calls", [])
                        for call in calls:
                            console.print(f"[dim]🔧 Calling: {call['name']}[/dim]")
                    elif event.type == EventType.TOOL_RESULT:
                        success = event.data.get("success")
                        if not success:
                            console.print(f"[red]Tool error: {event.data.get('error')}[/red]")
                    elif event.type == EventType.ERROR:
                        console.print(f"[red]Error: {event.data.get('error')}[/red]")
                
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n[green]Goodbye! 👋[/green]")
                break
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    async def _handle_command(self, command: str) -> bool:
        """处理命令"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd in ('/exit', '/quit'):
            # 清理 MCP 连接
            if hasattr(self, 'mcp_manager') and self.mcp_manager:
                await self.mcp_manager.disconnect_all()
            console.print("[green]Goodbye! 👋[/green]")
            return True
        
        elif cmd == '/help':
            help_text = """
# Available Commands

- `/exit`, `/quit` - Exit the application
- `/help` - Show this help message
- `/skills` - List available skills
- `/clear` - Clear conversation history
- `/mode <plan|default|yolo|read_only>` - Change approval mode
- `/config` - Show current configuration
- `/mcp` - Show MCP server status and tools
            """
            console.print(Markdown(help_text))
        
        elif cmd == '/skills':
            if self.skill_manager:
                skills = self.skill_manager.get_available_skills()
                if skills:
                    console.print("[bold]Available Skills:[/bold]")
                    for skill in skills:
                        status = "🟢" if skill.active else "⚪"
                        console.print(f"{status} {skill.name}: {skill.description[:60]}...")
                else:
                    console.print("[yellow]No skills available[/yellow]")
        
        elif cmd == '/clear':
            self.agent.clear_history()
            console.print("[green]Conversation history cleared[/green]")
        
        elif cmd == '/mode' and args:
            mode_map = {
                'plan': ApprovalMode.PLAN,
                'default': ApprovalMode.DEFAULT,
                'yolo': ApprovalMode.YOLO,
                'read_only': ApprovalMode.READ_ONLY
            }
            mode = mode_map.get(args[0].lower())
            if mode:
                self.agent.policy.set_mode(mode)
                console.print(f"[green]Mode changed to: {args[0]}[/green]")
        
        elif cmd == '/config':
            console.print("[bold]Current Configuration:[/bold]")
            console.print(f"  LLM Provider: {self.config['llm']['provider']}")
            console.print(f"  Model: {self.config['llm'][self.config['llm']['provider']]['model']}")
            console.print(f"  Approval Mode: {self.config['agent']['approval_mode']}")
            console.print(f"  Max Turns: {self.config['agent']['max_turns']}")
            console.print(f"  Temperature: {self.config['agent']['temperature']}")
            
            # 显示 MCP 状态
            if self.config.get('mcp', {}).get('enabled', False):
                mcp_servers = len(self.config['mcp'].get('servers', {}))
                connected_servers = len(self.mcp_manager.connections) if hasattr(self, 'mcp_manager') and self.mcp_manager else 0
                console.print(f"  MCP: Enabled ({connected_servers}/{mcp_servers} servers connected)")
            else:
                console.print(f"  MCP: Disabled")
        
        elif cmd == '/mcp':
            if not self.config.get('mcp', {}).get('enabled', False):
                console.print("[yellow]MCP is not enabled in configuration[/yellow]")
            elif not hasattr(self, 'mcp_manager') or not self.mcp_manager:
                console.print("[yellow]MCP manager not initialized[/yellow]")
            else:
                console.print("[bold]MCP Status:[/bold]")
                
                # 显示连接的服务器
                if self.mcp_manager.connections:
                    console.print(f"\n[green]Connected Servers ({len(self.mcp_manager.connections)}):[/green]")
                    for name, connection in self.mcp_manager.connections.items():
                        tools_count = len(connection.get_tools())
                        resources_count = len(connection.get_resources())
                        prompts_count = len(connection.get_prompts())
                        console.print(f"  • {name}: {tools_count} tools, {resources_count} resources, {prompts_count} prompts")
                else:
                    console.print("[yellow]No MCP servers connected[/yellow]")
                
                # 显示可用工具
                adapters = self.mcp_manager.get_adapters()
                if adapters:
                    console.print(f"\n[green]Available MCP Tools ({len(adapters)}):[/green]")
                    for adapter in adapters[:10]:  # 只显示前10个
                        console.print(f"  • {adapter.display_name}")
                    if len(adapters) > 10:
                        console.print(f"  ... and {len(adapters) - 10} more")
        
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")
        
        return False


async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Nano Claw - Python Agent System')
    parser.add_argument('-c', '--config', default='config.yaml', help='Config file path')
    args = parser.parse_args()
    
    app = NanoAgentApp(config_path=args.config)
    await app.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
