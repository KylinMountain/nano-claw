"""
外部编程代理工具
用于将复杂编码任务委派给外部 CLI（默认 gemini CLI）
"""
import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import asyncio

from .base import ToolBuilder, ToolInvocation, ToolKind, ToolResult


@dataclass
class ExternalCoderSettings:
    """外部编程工具配置"""
    enabled: bool = True
    provider: str = "gemini_cli"
    command: str = "gemini"
    args_template: List[str] = field(default_factory=lambda: ["-p", "{task}"])
    timeout: int = 600
    working_dir: str = "."
    allow_commands: List[str] = field(default_factory=lambda: ["gemini", "codex"])
    pass_through_env: List[str] = field(default_factory=lambda: ["PATH", "HOME", "SHELL"])
    extra_env: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ExternalCoderSettings":
        data = raw or {}
        return cls(
            enabled=bool(data.get("enabled", True)),
            provider=str(data.get("provider", "gemini_cli")),
            command=str(data.get("command", "gemini")),
            args_template=list(data.get("args_template", ["-p", "{task}"])),
            timeout=int(data.get("timeout", 600)),
            working_dir=str(data.get("working_dir", ".")),
            allow_commands=list(data.get("allow_commands", ["gemini", "codex"])),
            pass_through_env=list(data.get("pass_through_env", ["PATH", "HOME", "SHELL"])),
            extra_env=dict(data.get("extra_env", {})),
        )


class ExternalCoderInvocation(ToolInvocation):
    """执行外部编程 CLI"""

    def __init__(self, *args, settings: ExternalCoderSettings, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings

    def get_affected_locations(self) -> List[str]:
        cwd = self.params.get("working_dir") or self.settings.working_dir
        return [cwd]

    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            command = self.settings.command.strip()
            if not command:
                return ToolResult(self.call_id, False, "", "External coder command is empty")

            if command not in self.settings.allow_commands:
                return ToolResult(
                    self.call_id,
                    False,
                    "",
                    f"Command '{command}' is not in allow_commands: {self.settings.allow_commands}",
                )

            executable = shutil.which(command)
            if not executable:
                return ToolResult(
                    self.call_id,
                    False,
                    "",
                    f"Command not found in PATH: {command}",
                )

            task = str(self.params.get("task", "")).strip()
            if not task:
                return ToolResult(self.call_id, False, "", "Missing required parameter: task")

            extra_context = str(self.params.get("context", "")).strip()
            final_task = task
            if extra_context:
                final_task = f"{task}\n\nAdditional context:\n{extra_context}"

            args = [str(a).replace("{task}", final_task) for a in self.settings.args_template]
            if not any("{task}" in str(a) for a in self.settings.args_template):
                # 若模板中未使用占位符，自动附加任务文本，避免空执行。
                args.append(final_task)

            working_dir = str(self.params.get("working_dir") or self.settings.working_dir or ".")
            working_dir = os.path.expanduser(working_dir)
            timeout = int(self.params.get("timeout") or self.settings.timeout)

            env: Dict[str, str] = {}
            for key in self.settings.pass_through_env:
                if key in os.environ:
                    env[key] = os.environ[key]
            for key, value in self.settings.extra_env.items():
                env[key] = os.path.expandvars(str(value))

            process = await asyncio.create_subprocess_exec(
                executable,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env or None,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    self.call_id,
                    False,
                    "",
                    f"External coder timed out after {timeout}s",
                )

            if cancellation_event.is_set():
                process.kill()
                return ToolResult(self.call_id, False, "", "Cancelled by user")

            output = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()

            if process.returncode != 0:
                return ToolResult(
                    self.call_id,
                    False,
                    output,
                    f"External coder exited with code {process.returncode}: {err}",
                )

            content = output or "External coder completed with no output."
            if err:
                content += f"\n\n[stderr]\n{err}"

            return ToolResult(self.call_id, True, content)

        except Exception as e:
            return ToolResult(self.call_id, False, "", str(e))


class ExternalCoderTool(ToolBuilder):
    """外部编程代理工具（受控）"""

    def __init__(self, settings: ExternalCoderSettings):
        self.settings = settings
        super().__init__(
            name="run_external_coder",
            display_name="Run External Coder",
            description=(
                "Delegate coding task to an external coding CLI (e.g., gemini/codex) "
                "with configured safety constraints."
            ),
            kind=ToolKind.EXECUTE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Coding task for external agent",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional additional context",
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Optional working directory override",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout override in seconds",
                    },
                },
                "required": ["task"],
            },
        )

    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return ExternalCoderInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id,
            settings=self.settings,
        )
