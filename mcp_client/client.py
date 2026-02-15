"""
MCP (Model Context Protocol) 客户端
使用官方 mcp 库实现
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from tools.base import ToolBuilder, ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    command: Optional[str] = None
    args: List[str] = None
    env: Dict[str, str] = None
    transport: str = "stdio"
    url: Optional[str] = None
    headers: Dict[str, str] = None
    timeout: float = 30.0
    sse_read_timeout: float = 300.0
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}
        if self.headers is None:
            self.headers = {}
        if self.url and not self.transport:
            self.transport = "streamable_http"

    @classmethod
    def from_dict(cls, name: str, config: Dict[str, Any]) -> "MCPServerConfig":
        """
        从配置字典创建 MCPServerConfig。

        支持两种形式：
        1) stdio 形式：command/args/env
        2) remote 形式：url/headers（可选 transport）
        """
        transport = config.get("transport")
        if not transport:
            transport = "streamable_http" if config.get("url") else "stdio"

        return cls(
            name=name,
            command=config.get("command"),
            args=config.get("args", []),
            env=config.get("env", {}),
            transport=transport,
            url=config.get("url"),
            headers=config.get("headers", {}),
            timeout=float(config.get("timeout", 30)),
            sse_read_timeout=float(config.get("sse_read_timeout", 300)),
        )


class MCPConnection:
    """MCP连接 - 使用官方SDK"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._tools: List[Dict] = []
        self._resources: List[Dict] = []
        self._prompts: List[Dict] = []
        self._connected = False
    
    async def connect(self) -> bool:
        """建立连接"""
        try:
            transport = (self.config.transport or "stdio").lower()
            if transport in ("streamable-http", "streamablehttp", "http"):
                transport = "streamable_http"

            if transport == "stdio":
                if not self.config.command:
                    raise ValueError(f"MCP server '{self.config.name}' missing required field: command")
                # 创建服务器参数
                server_params = StdioServerParameters(
                    command=self.config.command,
                    args=self.config.args,
                    env=self._resolve_env(self.config.env)
                )
                read, write = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
            elif transport == "streamable_http":
                if not self.config.url:
                    raise ValueError(f"MCP server '{self.config.name}' missing required field: url")
                client_ctx = streamablehttp_client(
                    url=self._resolve_string(self.config.url),
                    headers=self._resolve_dict(self.config.headers) or None,
                    timeout=self.config.timeout,
                    sse_read_timeout=self.config.sse_read_timeout,
                )
                read, write, _ = await self.exit_stack.enter_async_context(client_ctx)
            elif transport == "sse":
                if not self.config.url:
                    raise ValueError(f"MCP server '{self.config.name}' missing required field: url")
                read, write = await self.exit_stack.enter_async_context(
                    sse_client(
                        url=self._resolve_string(self.config.url),
                        headers=self._resolve_dict(self.config.headers) or None,
                        timeout=self.config.timeout,
                        sse_read_timeout=self.config.sse_read_timeout,
                    )
                )
            else:
                raise ValueError(
                    f"Unsupported MCP transport '{self.config.transport}' for server '{self.config.name}'"
                )
            
            # 创建客户端会话
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # 初始化连接
            await self.session.initialize()
            
            # 获取服务器能力
            await self._discover_capabilities()
            
            self._connected = True
            logger.info(f"MCP server '{self.config.name}' connected successfully")
            return True
                    
        except Exception as e:
            logger.error(f"MCP connection error for '{self.config.name}': {e}")
            await self.disconnect()
            return False

    def _resolve_string(self, value: str) -> str:
        """解析字符串中的环境变量占位符，例如 ${TOKEN}。"""
        return os.path.expandvars(value)

    def _resolve_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """递归解析字典中的字符串环境变量。"""
        resolved: Dict[str, Any] = {}
        for key, value in (data or {}).items():
            if isinstance(value, str):
                resolved[key] = self._resolve_string(value)
            else:
                resolved[key] = value
        return resolved

    def _resolve_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """解析 env 值中的变量引用。"""
        return {k: self._resolve_string(str(v)) for k, v in (env or {}).items()}
    
    async def _discover_capabilities(self):
        """发现服务器能力"""
        if not self.session:
            return
        
        try:
            # 获取工具列表
            tools_result = await self.session.list_tools()
            self._tools = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema or {"type": "object"}
                }
                for tool in tools_result.tools
            ]
            logger.debug(f"Discovered {len(self._tools)} tools")
            
        except Exception as e:
            logger.debug(f"Failed to list tools: {e}")
        
        try:
            # 获取资源列表
            resources_result = await self.session.list_resources()
            self._resources = [
                {
                    "uri": resource.uri,
                    "name": resource.name or "",
                    "description": resource.description or "",
                    "mimeType": resource.mimeType
                }
                for resource in resources_result.resources
            ]
            logger.debug(f"Discovered {len(self._resources)} resources")
            
        except Exception as e:
            logger.debug(f"Failed to list resources: {e}")
        
        try:
            # 获取提示列表
            prompts_result = await self.session.list_prompts()
            self._prompts = [
                {
                    "name": prompt.name,
                    "description": prompt.description or "",
                    "arguments": [
                        {
                            "name": arg.name,
                            "description": arg.description or "",
                            "required": arg.required or False
                        }
                        for arg in (prompt.arguments or [])
                    ]
                }
                for prompt in prompts_result.prompts
            ]
            logger.debug(f"Discovered {len(self._prompts)} prompts")
            
        except Exception as e:
            logger.debug(f"Failed to list prompts: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """调用工具"""
        if not self.session or not self._connected:
            raise RuntimeError("MCP session not connected")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # 处理结果内容
            content_text = ""
            if result.content:
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        content_text += content_item.text + "\n"
                    elif hasattr(content_item, 'data'):
                        content_text += str(content_item.data) + "\n"
            
            return {
                "result": {
                    "content": [{"type": "text", "text": content_text.strip()}]
                }
            }
            
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {
                "error": {
                    "message": str(e)
                }
            }
    
    def get_tools(self) -> List[Dict]:
        """获取工具列表"""
        return self._tools
    
    def get_resources(self) -> List[Dict]:
        """获取资源列表"""
        return self._resources
    
    def get_prompts(self) -> List[Dict]:
        """获取提示列表"""
        return self._prompts
    
    async def disconnect(self) -> None:
        """断开连接"""
        try:
            await self.exit_stack.aclose()
            self._connected = False
            logger.debug(f"MCP server '{self.config.name}' disconnected")
        except BaseException as e:
            # 某些 MCP 传输在关闭时会抛 CancelledError，不应导致主程序退出失败。
            self._connected = False
            logger.warning(f"Error disconnecting MCP server '{self.config.name}': {e}")


class MCPToolInvocation(ToolInvocation):
    """MCP工具调用"""
    
    def __init__(self, *args, connection: MCPConnection, mcp_tool_name: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = connection
        self.mcp_tool_name = mcp_tool_name
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            response = await self.connection.call_tool(
                self.mcp_tool_name,
                self.params
            )
            
            if "error" in response:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=response["error"].get("message", "Unknown error")
                )
            
            result = response.get("result", {})
            content = result.get("content", [])
            
            # 提取文本内容
            text_content = "\n".join([
                item.get("text", "") 
                for item in content 
                if item.get("type") == "text"
            ])
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=text_content or "Tool executed successfully"
            )
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class MCPAdapter(ToolBuilder):
    """MCP工具适配器"""
    
    def __init__(
        self,
        server_name: str,
        mcp_tool: Dict,
        connection: MCPConnection
    ):
        self.server_name = server_name
        self.mcp_tool = mcp_tool
        self.connection = connection
        
        # 构建工具名（添加前缀避免冲突）
        tool_name = f"mcp__{server_name}__{mcp_tool['name']}"
        
        super().__init__(
            name=tool_name,
            display_name=f"[{server_name}] {mcp_tool['name']}",
            description=mcp_tool.get("description", ""),
            kind=ToolKind.OTHER,
            parameter_schema=mcp_tool.get("inputSchema", {"type": "object"})
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return MCPToolInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id,
            connection=self.connection,
            mcp_tool_name=self.mcp_tool["name"]
        )


class MCPManager:
    """MCP管理器 - 管理多个MCP服务器连接"""
    
    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self.adapters: List[MCPAdapter] = []
    
    async def add_server(self, config: MCPServerConfig) -> bool:
        """添加MCP服务器"""
        connection = MCPConnection(config)
        
        if await connection.connect():
            self.connections[config.name] = connection
            
            # 创建工具适配器
            for tool in connection.get_tools():
                adapter = MCPAdapter(config.name, tool, connection)
                self.adapters.append(adapter)
            
            logger.info(
                f"MCP server '{config.name}' added with "
                f"{len(connection.get_tools())} tools, "
                f"{len(connection.get_resources())} resources, "
                f"{len(connection.get_prompts())} prompts"
            )
            return True
        
        logger.error(f"Failed to connect to MCP server '{config.name}'")
        return False
    
    def get_adapters(self) -> List[MCPAdapter]:
        """获取所有MCP工具适配器"""
        return self.adapters
    
    async def remove_server(self, name: str) -> None:
        """移除MCP服务器"""
        if name in self.connections:
            await self.connections[name].disconnect()
            del self.connections[name]
            
            # 移除相关适配器
            self.adapters = [
                a for a in self.adapters 
                if not a.name.startswith(f"mcp__{name}__")
            ]
            logger.info(f"MCP server '{name}' removed")
    
    async def disconnect_all(self) -> None:
        """断开所有连接"""
        for name, connection in self.connections.items():
            await connection.disconnect()
        self.connections.clear()
        self.adapters.clear()
        logger.info("All MCP servers disconnected")
