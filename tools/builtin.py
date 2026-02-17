"""
内置工具实现 - 文件操作、Shell执行等
"""
import os
import json
import subprocess
import glob as glob_module
from typing import Any, Dict, List
import asyncio

from .base import ToolBuilder, ToolInvocation, ToolKind
from .base import ToolResult


class ReadFileInvocation(ToolInvocation):
    """读取文件工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            file_path = self.params.get("path", "")
            offset = self.params.get("offset", 0)
            limit = self.params.get("limit")
            
            if not os.path.exists(file_path):
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}"
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 应用offset和limit
            start = offset
            end = offset + limit if limit else len(lines)
            selected_lines = lines[start:end]
            
            content = ''.join(selected_lines)
            
            # 添加行号
            numbered_content = '\n'.join([
                f"{i + offset + 1:4d} | {line.rstrip()}"
                for i, line in enumerate(selected_lines)
            ])
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=f"File: {file_path}\n```\n{numbered_content}\n```"
            )
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class ReadFileTool(ToolBuilder):
    """读取文件工具"""
    
    def __init__(self):
        super().__init__(
            name="read_file",
            display_name="Read File",
            description="Read contents of a file with optional offset and line limit",
            kind=ToolKind.READ,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line offset to start reading from",
                        "default": 0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read"
                    }
                },
                "required": ["path"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return ReadFileInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class WriteFileInvocation(ToolInvocation):
    """写入文件工具调用"""
    
    def get_affected_locations(self) -> List[str]:
        return [self.params.get("path", "")]
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            file_path = self.params.get("path", "")
            content = self.params.get("content", "")

            if not file_path:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error="Missing required parameter: path"
                )

            original_path = file_path
            cwd = os.getcwd()

            # 如果给了不可写的绝对路径，自动回落到当前目录同名文件。
            if os.path.isabs(file_path):
                target_dir = os.path.dirname(file_path) or file_path
                if not os.access(target_dir, os.W_OK):
                    file_path = os.path.join(cwd, os.path.basename(file_path))

            # 确保目录存在（仅当目录非空）
            target_dir = os.path.dirname(file_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            message = f"Successfully wrote to {file_path}"
            if file_path != original_path:
                message += f" (fallback from unwritable path: {original_path})"

            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=message
            )
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class WriteFileTool(ToolBuilder):
    """写入文件工具"""
    
    def __init__(self):
        super().__init__(
            name="write_file",
            display_name="Write File",
            description="Write content to a file, creating directories if needed",
            kind=ToolKind.EDIT,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["path", "content"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return WriteFileInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class ShellCommandInvocation(ToolInvocation):
    """Shell命令工具调用"""
    
    def get_affected_locations(self) -> List[str]:
        return [self.params.get("working_dir", os.getcwd())]
    
    def get_description(self) -> str:
        return f"Execute: {self.params.get('command', '')}"
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            command = self.params.get("command", "")
            working_dir = self.params.get("working_dir", os.getcwd())
            timeout = self.params.get("timeout", 30)
            
            # 使用asyncio创建子进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            # 等待完成或取消
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=f"Command timed out after {timeout}s"
                )
            
            # 检查是否被取消
            if cancellation_event.is_set():
                process.kill()
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error="Cancelled by user"
                )
            
            output = stdout.decode('utf-8', errors='replace')
            error_output = stderr.decode('utf-8', errors='replace')
            
            if process.returncode != 0:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content=output,
                    error=f"Exit code {process.returncode}: {error_output}"
                )
            
            result_content = output
            if error_output:
                result_content += f"\n[stderr]\n{error_output}"
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=result_content or "Command executed successfully (no output)"
            )
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class ShellCommandTool(ToolBuilder):
    """Shell命令工具"""
    
    def __init__(self):
        super().__init__(
            name="shell",
            display_name="Shell Command",
            description="Execute a shell command with optional working directory and timeout",
            kind=ToolKind.EXECUTE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory for the command"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 30
                    }
                },
                "required": ["command"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return ShellCommandInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class GlobInvocation(ToolInvocation):
    """文件搜索工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            pattern = self.params.get("pattern", "")
            cwd = self.params.get("cwd", ".")
            
            matches = glob_module.glob(pattern, root_dir=cwd, recursive=True)
            
            # 限制结果数量
            matches = matches[:100]
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=f"Found {len(matches)} files:\n" + "\n".join(matches)
            )
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class GlobTool(ToolBuilder):
    """文件搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="glob",
            display_name="Glob Search",
            description="Search for files matching a glob pattern",
            kind=ToolKind.SEARCH,
            parameter_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '**/*.py')"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "."
                    }
                },
                "required": ["pattern"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return GlobInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class AskUserInvocation(ToolInvocation):
    """询问用户工具调用"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._response_future: asyncio.Future = asyncio.get_event_loop().create_future()
    
    def set_response(self, response: str):
        """设置用户响应"""
        if not self._response_future.done():
            self._response_future.set_result(response)
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            question = self.params.get("question", "Please provide your input:")
            options = self.params.get("options") or []
            timeout = int(self.params.get("timeout", 300))

            prompt = f"\n[AskUser] {question}"
            if options:
                prompt += f"\nOptions: {', '.join(str(o) for o in options)}"
            prompt += "\nYour response: "

            # 终端直连输入，避免工具调用后无响应悬挂。
            response = await asyncio.wait_for(
                asyncio.to_thread(input, prompt),
                timeout=timeout
            )
            self.set_response(response)
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=f"User response: {response}"
            )
        except asyncio.TimeoutError:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error="Timeout waiting for user response"
            )


class AskUserTool(ToolBuilder):
    """询问用户工具 - HumanInTheLoop核心"""
    
    def __init__(self):
        super().__init__(
            name="ask_user",
            display_name="Ask User",
            description="Ask the user a question and wait for their response",
            kind=ToolKind.COMMUNICATE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to ask the user"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional predefined options"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds for waiting user response",
                        "default": 300
                    }
                },
                "required": ["question"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return AskUserInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


def register_builtin_tools(registry):
    """注册所有内置工具"""
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ShellCommandTool())
    registry.register(GlobTool())
    registry.register(AskUserTool())
    
    # 注册高级工具
    try:
        from .advanced import register_advanced_tools
        register_advanced_tools(registry)
    except ImportError as e:
        print(f"Warning: Could not load advanced tools: {e}")
