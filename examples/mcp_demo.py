#!/usr/bin/env python3
"""
MCP 功能演示
展示如何使用 Nano Agent 的 MCP 集成
"""
import asyncio
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mcp_client.client import MCPManager, MCPServerConfig

console = Console()


async def demo_mcp():
    """演示 MCP 功能"""
    console.print(Panel.fit("🔗 Nano Agent MCP 演示", style="bold blue"))
    
    # 读取配置
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        console.print("[red]错误: 找不到 config.yaml 文件[/red]")
        return
    
    if not config.get('mcp', {}).get('enabled', False):
        console.print("[yellow]MCP 未启用，请在 config.yaml 中启用 MCP[/yellow]")
        return
    
    manager = MCPManager()
    
    try:
        # 连接所有配置的服务器
        servers = config['mcp']['servers']
        console.print(f"\n📡 正在连接 {len(servers)} 个 MCP 服务器...")
        
        connected_servers = []
        for server_name, server_config in servers.items():
            console.print(f"  连接 {server_name}...", end="")
            
            mcp_config = MCPServerConfig(
                name=server_name,
                command=server_config.get('command'),
                args=server_config.get('args', []),
                env=server_config.get('env', {})
            )
            
            success = await manager.add_server(mcp_config)
            if success:
                console.print(" [green]✓[/green]")
                connected_servers.append(server_name)
            else:
                console.print(" [red]✗[/red]")
        
        if not connected_servers:
            console.print("[red]没有成功连接任何 MCP 服务器[/red]")
            return
        
        console.print(f"\n✅ 成功连接 {len(connected_servers)} 个服务器")
        
        # 显示发现的工具
        adapters = manager.get_adapters()
        if adapters:
            console.print(f"\n🛠️  发现 {len(adapters)} 个工具:")
            
            # 创建工具表格
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("服务器", style="cyan")
            table.add_column("工具名", style="green")
            table.add_column("描述", style="white")
            
            for adapter in adapters:
                server_name = adapter.server_name
                tool_name = adapter.mcp_tool['name']
                description = adapter.description[:50] + "..." if len(adapter.description) > 50 else adapter.description
                table.add_row(server_name, tool_name, description)
            
            console.print(table)
        else:
            console.print("[yellow]没有发现任何工具[/yellow]")
        
        # 显示连接的服务器信息
        console.print(f"\n📊 服务器详情:")
        for name, connection in manager.connections.items():
            tools_count = len(connection.get_tools())
            resources_count = len(connection.get_resources())
            prompts_count = len(connection.get_prompts())
            
            info_panel = Panel(
                f"工具: {tools_count} | 资源: {resources_count} | 提示: {prompts_count}",
                title=f"[bold]{name}[/bold]",
                border_style="green"
            )
            console.print(info_panel)
        
        console.print("\n[dim]提示: 在 Nano Agent 中，这些工具会自动可用于 AI 助手使用[/dim]")
        
    except Exception as e:
        console.print(f"[red]演示过程中出错: {e}[/red]")
        
    finally:
        # 清理连接
        await manager.disconnect_all()
        console.print("\n🔌 MCP 连接已清理")


if __name__ == "__main__":
    asyncio.run(demo_mcp())
