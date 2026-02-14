"""
智能策略引擎 - 更接近Gemini CLI的智能确认机制
"""
import os
import re
from typing import Dict, List, Set, Optional
from pathlib import Path

from .policy import PolicyEngine, ApprovalMode, PolicyDecision
from tools.base import ToolKind


class SmartPolicyEngine(PolicyEngine):
    """智能策略引擎"""
    
    def __init__(self, mode: ApprovalMode = ApprovalMode.DEFAULT):
        super().__init__(mode)
        self._setup_smart_rules()
    
    def _setup_smart_rules(self):
        """设置智能规则"""
        # 高风险操作模式
        self.high_risk_patterns = {
            # 文件操作风险
            'system_files': [
                r'/etc/.*',
                r'/usr/.*',
                r'/bin/.*',
                r'/sbin/.*',
                r'C:\\Windows\\.*',
                r'C:\\Program Files\\.*'
            ],
            # 危险命令
            'dangerous_commands': [
                r'rm\s+-rf\s+/',
                r'del\s+/s\s+/q\s+C:\\',
                r'format\s+',
                r'fdisk\s+',
                r'dd\s+if=.*of=/dev/',
                r'sudo\s+rm\s+-rf',
                r'chmod\s+777\s+/',
                r'chown\s+.*\s+/'
            ],
            # 网络操作
            'network_operations': [
                r'curl\s+.*\|\s*sh',
                r'wget\s+.*\|\s*sh',
                r'nc\s+-l',
                r'netcat\s+-l'
            ]
        }
        
        # 安全操作模式
        self.safe_patterns = {
            'read_operations': [
                r'cat\s+',
                r'less\s+',
                r'head\s+',
                r'tail\s+',
                r'grep\s+',
                r'find\s+',
                r'ls\s+',
                r'dir\s+'
            ],
            'safe_directories': [
                r'./.*',
                r'~/.*',
                r'/tmp/.*',
                r'/var/tmp/.*'
            ]
        }
    
    def check(
        self,
        tool_name: str,
        tool_kind: ToolKind,
        arguments: Dict,
        is_mutator: bool = False
    ) -> PolicyDecision:
        """智能检查工具调用"""
        
        # 首先执行基础检查
        base_decision = super().check(tool_name, tool_kind, arguments, is_mutator)
        
        # 如果基础策略已经拒绝，直接返回
        if base_decision == PolicyDecision.DENY:
            return base_decision
        
        # 如果是YOLO模式，进行安全检查后允许
        if self.mode == ApprovalMode.YOLO:
            if self._is_high_risk_operation(tool_name, arguments):
                return PolicyDecision.ASK_USER
            return PolicyDecision.ALLOW
        
        # 智能风险评估
        risk_level = self._assess_risk(tool_name, tool_kind, arguments)
        
        if risk_level == "high":
            return PolicyDecision.ASK_USER
        elif risk_level == "medium" and self.mode == ApprovalMode.DEFAULT:
            return PolicyDecision.ASK_USER
        elif risk_level == "low":
            return PolicyDecision.ALLOW
        
        return base_decision
    
    def _assess_risk(self, tool_name: str, tool_kind: ToolKind, arguments: Dict) -> str:
        """评估操作风险级别"""
        
        # 高风险操作
        if self._is_high_risk_operation(tool_name, arguments):
            return "high"
        
        # 中等风险操作
        if self._is_medium_risk_operation(tool_name, arguments):
            return "medium"
        
        # 低风险操作
        if self._is_low_risk_operation(tool_name, arguments):
            return "low"
        
        # 默认根据工具类型判断
        if tool_kind in [ToolKind.DELETE, ToolKind.EXECUTE]:
            return "medium"
        elif tool_kind in [ToolKind.EDIT, ToolKind.MOVE]:
            return "low"
        else:
            return "low"
    
    def _is_high_risk_operation(self, tool_name: str, arguments: Dict) -> bool:
        """检查是否为高风险操作"""
        
        # 检查文件路径
        if 'path' in arguments:
            path = str(arguments['path'])
            for pattern in self.high_risk_patterns['system_files']:
                if re.match(pattern, path, re.IGNORECASE):
                    return True
        
        # 检查命令内容
        if 'command' in arguments:
            command = str(arguments['command'])
            for pattern in self.high_risk_patterns['dangerous_commands']:
                if re.search(pattern, command, re.IGNORECASE):
                    return True
            for pattern in self.high_risk_patterns['network_operations']:
                if re.search(pattern, command, re.IGNORECASE):
                    return True
        
        # 检查Git操作
        if tool_name == 'git':
            git_command = arguments.get('command', '')
            if git_command in ['push', 'reset', 'rebase', 'force-push']:
                return True
        
        return False
    
    def _is_medium_risk_operation(self, tool_name: str, arguments: Dict) -> bool:
        """检查是否为中等风险操作"""
        
        # 写入操作到重要目录
        if tool_name == 'write_file' and 'path' in arguments:
            path = Path(arguments['path'])
            important_files = [
                'package.json', 'requirements.txt', 'Cargo.toml', 'go.mod',
                'Dockerfile', 'docker-compose.yml', '.gitignore', 'README.md'
            ]
            if path.name in important_files:
                return True
        
        # Shell命令执行
        if tool_name == 'shell' and 'command' in arguments:
            command = str(arguments['command'])
            # 包含sudo或管理员权限
            if re.search(r'sudo\s+', command) or re.search(r'runas\s+', command):
                return True
            # 安装或卸载软件
            if re.search(r'(apt|yum|brew|pip|npm)\s+(install|uninstall|remove)', command):
                return True
        
        return False
    
    def _is_low_risk_operation(self, tool_name: str, arguments: Dict) -> bool:
        """检查是否为低风险操作"""
        
        # 读取操作
        if tool_name in ['read_file', 'glob', 'analyze_code', 'analyze_project']:
            return True
        
        # 安全目录的写入操作
        if 'path' in arguments:
            path = str(arguments['path'])
            for pattern in self.safe_patterns['safe_directories']:
                if re.match(pattern, path):
                    return True
        
        # 安全的shell命令
        if 'command' in arguments:
            command = str(arguments['command'])
            for pattern in self.safe_patterns['read_operations']:
                if re.search(pattern, command):
                    return True
        
        return False
    
    def generate_smart_confirmation_prompt(
        self,
        tool_name: str,
        arguments: Dict,
        risk_level: str
    ) -> str:
        """生成智能确认提示"""
        
        risk_emoji = {
            "high": "🚨",
            "medium": "⚠️",
            "low": "ℹ️"
        }
        
        risk_colors = {
            "high": "🔴",
            "medium": "🟡", 
            "low": "🟢"
        }
        
        prompt = f"{risk_emoji.get(risk_level, 'ℹ️')} **Tool Execution Request**\n\n"
        prompt += f"**Risk Level**: {risk_colors.get(risk_level, '🟢')} {risk_level.upper()}\n"
        prompt += f"**Tool**: `{tool_name}`\n\n"
        
        # 显示参数
        prompt += "**Arguments**:\n"
        for key, value in arguments.items():
            if len(str(value)) > 100:
                value = str(value)[:100] + "..."
            prompt += f"  - {key}: `{value}`\n"
        
        # 根据风险级别添加特定警告
        if risk_level == "high":
            prompt += "\n🚨 **HIGH RISK OPERATION**\n"
            prompt += "This operation could potentially:\n"
            prompt += "- Modify system files\n"
            prompt += "- Execute dangerous commands\n"
            prompt += "- Affect system security\n"
            prompt += "\nPlease review carefully before proceeding.\n"
        
        elif risk_level == "medium":
            prompt += "\n⚠️ **MEDIUM RISK OPERATION**\n"
            prompt += "This operation will make changes that could affect:\n"
            prompt += "- Project configuration\n"
            prompt += "- Important files\n"
            prompt += "- System packages\n"
        
        prompt += "\nDo you want to proceed?"
        
        return prompt


class RiskAssessment:
    """风险评估工具"""
    
    @staticmethod
    def assess_file_operation(path: str, operation: str) -> Dict:
        """评估文件操作风险"""
        path_obj = Path(path)
        
        assessment = {
            "risk_level": "low",
            "factors": [],
            "recommendations": []
        }
        
        # 检查路径风险
        if path_obj.is_absolute():
            if str(path_obj).startswith(('/etc', '/usr', '/bin', '/sbin')):
                assessment["risk_level"] = "high"
                assessment["factors"].append("System directory access")
                assessment["recommendations"].append("Avoid modifying system files")
        
        # 检查文件类型
        if path_obj.suffix in ['.exe', '.bat', '.sh', '.py']:
            if assessment["risk_level"] == "low":
                assessment["risk_level"] = "medium"
            assessment["factors"].append("Executable file")
            assessment["recommendations"].append("Review executable content carefully")
        
        # 检查重要配置文件
        important_files = [
            'package.json', 'requirements.txt', 'Dockerfile', 
            '.gitignore', 'config.yaml', 'settings.py'
        ]
        if path_obj.name in important_files:
            if assessment["risk_level"] == "low":
                assessment["risk_level"] = "medium"
            assessment["factors"].append("Important configuration file")
            assessment["recommendations"].append("Backup before modification")
        
        return assessment
    
    @staticmethod
    def assess_command_risk(command: str) -> Dict:
        """评估命令风险"""
        assessment = {
            "risk_level": "low",
            "factors": [],
            "recommendations": []
        }
        
        # 高风险命令模式
        high_risk_patterns = [
            r'rm\s+-rf',
            r'sudo\s+',
            r'chmod\s+777',
            r'curl\s+.*\|\s*sh',
            r'wget\s+.*\|\s*sh'
        ]
        
        for pattern in high_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                assessment["risk_level"] = "high"
                assessment["factors"].append(f"Dangerous command pattern: {pattern}")
                assessment["recommendations"].append("Review command carefully")
                break
        
        # 中等风险命令
        medium_risk_patterns = [
            r'(apt|yum|brew|pip|npm)\s+(install|remove)',
            r'git\s+(push|reset|rebase)',
            r'docker\s+(run|exec)'
        ]
        
        if assessment["risk_level"] != "high":
            for pattern in medium_risk_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    assessment["risk_level"] = "medium"
                    assessment["factors"].append(f"System modification command")
                    assessment["recommendations"].append("Ensure you understand the impact")
                    break
        
        return assessment