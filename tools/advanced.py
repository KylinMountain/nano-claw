"""
高级工具实现 - 补充Gemini CLI的核心功能
"""
import os
import json
import subprocess
import requests
import ast
from typing import Any, Dict, List, Optional
import asyncio
from pathlib import Path

from .base import ToolBuilder, ToolInvocation, ToolKind, ToolResult


class GitInvocation(ToolInvocation):
    """Git操作工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            command = self.params.get("command", "")
            args = self.params.get("args", [])
            
            # 构建git命令
            git_cmd = ["git", command] + args
            
            # 执行git命令
            process = await asyncio.create_subprocess_exec(
                *git_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=f"Git command failed: {stderr.decode()}"
                )
            
            output = stdout.decode().strip()
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=f"Git {command} output:\n{output}" if output else f"Git {command} completed successfully"
            )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class GitTool(ToolBuilder):
    """Git操作工具"""
    
    def __init__(self):
        super().__init__(
            name="git",
            display_name="Git Operations",
            description="Execute git commands for version control operations",
            kind=ToolKind.EXECUTE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Git command (status, add, commit, push, pull, log, etc.)",
                        "enum": ["status", "add", "commit", "push", "pull", "log", "diff", "branch", "checkout"]
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional arguments for the git command"
                    }
                },
                "required": ["command"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return GitInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class CodeAnalysisInvocation(ToolInvocation):
    """代码分析工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            file_path = self.params.get("path", "")
            analysis_type = self.params.get("type", "structure")
            
            if not os.path.exists(file_path):
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}"
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if analysis_type == "structure":
                result = self._analyze_structure(content, file_path)
            elif analysis_type == "complexity":
                result = self._analyze_complexity(content, file_path)
            elif analysis_type == "dependencies":
                result = self._analyze_dependencies(content, file_path)
            else:
                result = "Unknown analysis type"
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=result
            )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )
    
    def _analyze_structure(self, content: str, file_path: str) -> str:
        """分析代码结构"""
        if not file_path.endswith('.py'):
            return "Code structure analysis currently supports Python files only"
        
        try:
            tree = ast.parse(content)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods
                    })
                elif isinstance(node, ast.FunctionDef) and not any(node.lineno >= cls["line"] for cls in classes):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args)
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        imports.append(f"{node.module}.{alias.name}" for alias in node.names)
            
            result = f"## Code Structure Analysis: {file_path}\n\n"
            
            if imports:
                result += f"### Imports ({len(imports)})\n"
                for imp in imports[:10]:  # 限制显示数量
                    result += f"- {imp}\n"
                if len(imports) > 10:
                    result += f"... and {len(imports) - 10} more\n"
                result += "\n"
            
            if classes:
                result += f"### Classes ({len(classes)})\n"
                for cls in classes:
                    result += f"- **{cls['name']}** (line {cls['line']})\n"
                    if cls['methods']:
                        result += f"  - Methods: {', '.join(cls['methods'][:5])}\n"
                        if len(cls['methods']) > 5:
                            result += f"  - ... and {len(cls['methods']) - 5} more methods\n"
                result += "\n"
            
            if functions:
                result += f"### Functions ({len(functions)})\n"
                for func in functions[:10]:
                    result += f"- **{func['name']}** (line {func['line']}, {func['args']} args)\n"
                if len(functions) > 10:
                    result += f"... and {len(functions) - 10} more functions\n"
            
            return result
            
        except SyntaxError as e:
            return f"Syntax error in Python file: {e}"
    
    def _analyze_complexity(self, content: str, file_path: str) -> str:
        """分析代码复杂度"""
        lines = content.split('\n')
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        blank_lines = total_lines - code_lines - comment_lines
        
        return f"""## Code Complexity Analysis: {file_path}

### Basic Metrics
- Total lines: {total_lines}
- Code lines: {code_lines}
- Comment lines: {comment_lines}
- Blank lines: {blank_lines}
- Comment ratio: {comment_lines/total_lines*100:.1f}%

### Complexity Indicators
- Average line length: {sum(len(line) for line in lines)/total_lines:.1f} chars
- Long lines (>80 chars): {len([line for line in lines if len(line) > 80])}
"""
    
    def _analyze_dependencies(self, content: str, file_path: str) -> str:
        """分析依赖关系"""
        if file_path.endswith('.py'):
            try:
                tree = ast.parse(content)
                imports = set()
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.update(alias.name.split('.')[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module.split('.')[0])
                
                stdlib_modules = {
                    'os', 'sys', 'json', 'time', 'datetime', 'collections', 'itertools',
                    'functools', 'operator', 're', 'math', 'random', 'urllib', 'http',
                    'pathlib', 'subprocess', 'threading', 'asyncio', 'typing'
                }
                
                stdlib = imports & stdlib_modules
                third_party = imports - stdlib_modules
                
                result = f"## Dependency Analysis: {file_path}\n\n"
                
                if stdlib:
                    result += f"### Standard Library ({len(stdlib)})\n"
                    for mod in sorted(stdlib):
                        result += f"- {mod}\n"
                    result += "\n"
                
                if third_party:
                    result += f"### Third Party ({len(third_party)})\n"
                    for mod in sorted(third_party):
                        result += f"- {mod}\n"
                
                return result
                
            except SyntaxError:
                return "Could not parse Python file for dependency analysis"
        
        return "Dependency analysis currently supports Python files only"


class CodeAnalysisTool(ToolBuilder):
    """代码分析工具"""
    
    def __init__(self):
        super().__init__(
            name="analyze_code",
            display_name="Code Analysis",
            description="Analyze code structure, complexity, and dependencies",
            kind=ToolKind.OTHER,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the code file to analyze"
                    },
                    "type": {
                        "type": "string",
                        "description": "Type of analysis to perform",
                        "enum": ["structure", "complexity", "dependencies"],
                        "default": "structure"
                    }
                },
                "required": ["path"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return CodeAnalysisInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class ProjectAnalysisInvocation(ToolInvocation):
    """项目分析工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            project_path = self.params.get("path", ".")
            analysis_type = self.params.get("type", "overview")
            
            if analysis_type == "overview":
                result = self._analyze_project_overview(project_path)
            elif analysis_type == "structure":
                result = self._analyze_project_structure(project_path)
            elif analysis_type == "tech_stack":
                result = self._analyze_tech_stack(project_path)
            else:
                result = "Unknown analysis type"
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=result
            )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )
    
    def _analyze_project_overview(self, project_path: str) -> str:
        """分析项目概览"""
        path = Path(project_path)
        
        # 统计文件类型
        file_types = {}
        total_files = 0
        total_size = 0
        
        for file_path in path.rglob('*'):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                total_files += 1
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    
                    ext = file_path.suffix.lower()
                    if ext:
                        file_types[ext] = file_types.get(ext, 0) + 1
                    else:
                        file_types['no_ext'] = file_types.get('no_ext', 0) + 1
                except:
                    pass
        
        # 检测项目类型
        project_type = self._detect_project_type(path)
        
        result = f"## Project Overview: {path.name}\n\n"
        result += f"**Project Type**: {project_type}\n"
        result += f"**Total Files**: {total_files}\n"
        result += f"**Total Size**: {total_size / 1024:.1f} KB\n\n"
        
        if file_types:
            result += "### File Types\n"
            sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)
            for ext, count in sorted_types[:10]:
                ext_name = ext if ext != 'no_ext' else '(no extension)'
                result += f"- {ext_name}: {count} files\n"
        
        return result
    
    def _analyze_project_structure(self, project_path: str) -> str:
        """分析项目结构"""
        path = Path(project_path)
        
        def build_tree(directory: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> str:
            if current_depth >= max_depth:
                return ""
            
            items = []
            try:
                for item in sorted(directory.iterdir()):
                    if item.name.startswith('.'):
                        continue
                    items.append(item)
            except PermissionError:
                return f"{prefix}[Permission Denied]\n"
            
            result = ""
            for i, item in enumerate(items[:20]):  # 限制显示数量
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                result += f"{prefix}{current_prefix}{item.name}\n"
                
                if item.is_dir() and current_depth < max_depth - 1:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    result += build_tree(item, next_prefix, max_depth, current_depth + 1)
            
            if len(items) > 20:
                result += f"{prefix}... and {len(items) - 20} more items\n"
            
            return result
        
        result = f"## Project Structure: {path.name}\n\n```\n{path.name}/\n"
        result += build_tree(path)
        result += "```"
        
        return result
    
    def _analyze_tech_stack(self, project_path: str) -> str:
        """分析技术栈"""
        path = Path(project_path)
        
        indicators = {
            "Python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "*.py"],
            "JavaScript/Node.js": ["package.json", "package-lock.json", "yarn.lock", "*.js"],
            "TypeScript": ["tsconfig.json", "*.ts"],
            "React": ["package.json"],  # 需要进一步检查内容
            "Vue": ["vue.config.js", "*.vue"],
            "Docker": ["Dockerfile", "docker-compose.yml"],
            "Rust": ["Cargo.toml", "*.rs"],
            "Go": ["go.mod", "*.go"],
            "Java": ["pom.xml", "build.gradle", "*.java"],
            "C/C++": ["Makefile", "CMakeLists.txt", "*.c", "*.cpp"],
        }
        
        detected = {}
        
        for tech, patterns in indicators.items():
            for pattern in patterns:
                if pattern.startswith('*.'):
                    # 文件扩展名检查
                    ext = pattern[1:]
                    if any(path.rglob(f"*{ext}")):
                        detected[tech] = detected.get(tech, [])
                        detected[tech].append(f"Files with {ext} extension")
                        break
                else:
                    # 特定文件检查
                    if (path / pattern).exists():
                        detected[tech] = detected.get(tech, [])
                        detected[tech].append(pattern)
        
        # 特殊检查：React
        package_json = path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    if "react" in deps:
                        detected["React"] = detected.get("React", [])
                        detected["React"].append("React dependency in package.json")
            except:
                pass
        
        result = f"## Technology Stack Analysis: {path.name}\n\n"
        
        if detected:
            result += "### Detected Technologies\n"
            for tech, indicators in detected.items():
                result += f"- **{tech}**\n"
                for indicator in indicators:
                    result += f"  - {indicator}\n"
        else:
            result += "No specific technology stack detected.\n"
        
        return result
    
    def _detect_project_type(self, path: Path) -> str:
        """检测项目类型"""
        if (path / "package.json").exists():
            return "Node.js/JavaScript Project"
        elif (path / "requirements.txt").exists() or (path / "setup.py").exists():
            return "Python Project"
        elif (path / "Cargo.toml").exists():
            return "Rust Project"
        elif (path / "go.mod").exists():
            return "Go Project"
        elif (path / "pom.xml").exists() or (path / "build.gradle").exists():
            return "Java Project"
        elif (path / "Dockerfile").exists():
            return "Containerized Project"
        else:
            return "Generic Project"


class ProjectAnalysisTool(ToolBuilder):
    """项目分析工具"""
    
    def __init__(self):
        super().__init__(
            name="analyze_project",
            display_name="Project Analysis",
            description="Analyze project structure, overview, and technology stack",
            kind=ToolKind.OTHER,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the project directory",
                        "default": "."
                    },
                    "type": {
                        "type": "string",
                        "description": "Type of analysis to perform",
                        "enum": ["overview", "structure", "tech_stack"],
                        "default": "overview"
                    }
                }
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return ProjectAnalysisInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


def register_advanced_tools(registry):
    """注册高级工具"""
    registry.register(GitTool())
    registry.register(CodeAnalysisTool())
    registry.register(ProjectAnalysisTool())