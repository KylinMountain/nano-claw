"""
记忆系统 - 三层记忆架构
模仿Gemini CLI的记忆系统
"""
import os
import re
from typing import Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryEntry:
    """记忆条目"""
    timestamp: float
    category: str
    content: str
    metadata: Dict = field(default_factory=dict)


class MemoryManager:
    """记忆管理器 - 管理三层记忆"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.global_memory_path = Path.home() / ".nano_claw" / "memory.md"
        self.environment_memory_path = self.project_root / "GEMINI.md"
        
        self._global_memory: str = ""
        self._environment_memory: str = ""
        self._jit_context: Dict[str, str] = {}
        self._loaded_paths: Set[str] = set()
    
    async def refresh(self) -> None:
        """刷新所有记忆"""
        await self._load_global_memory()
        await self._load_environment_memory()
    
    async def _load_global_memory(self) -> None:
        """加载全局记忆 (Tier 1)"""
        if self.global_memory_path.exists():
            try:
                self._global_memory = self.global_memory_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Error loading global memory: {e}")
                self._global_memory = ""
    
    async def _load_environment_memory(self) -> None:
        """加载环境记忆 (Tier 2)"""
        if self.environment_memory_path.exists():
            try:
                self._environment_memory = self.environment_memory_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Error loading environment memory: {e}")
                self._environment_memory = ""
    
    async def discover_context(self, accessed_path: str, trusted_roots: List[str]) -> str:
        """
        动态发现JIT上下文 (Tier 3)
        基于访问路径动态加载子目录特定上下文
        """
        # 简化实现：查找访问路径下的.nano_claw/memory.md
        path = Path(accessed_path)
        context_parts = []
        
        # 遍历路径层次，查找上下文文件
        current = path if path.is_dir() else path.parent
        
        while current != current.parent:  # 直到根目录
            context_file = current / ".nano_claw" / "context.md"
            
            if context_file.exists():
                file_key = str(context_file)
                
                if file_key not in self._loaded_paths:
                    try:
                        content = context_file.read_text(encoding='utf-8')
                        self._jit_context[file_key] = content
                        self._loaded_paths.add(file_key)
                    except Exception as e:
                        print(f"Error loading JIT context from {context_file}: {e}")
                
                if file_key in self._jit_context:
                    context_parts.append(self._jit_context[file_key])
            
            # 向上遍历
            current = current.parent
            
            # 检查是否超出信任根目录
            if not any(str(current).startswith(root) for root in trusted_roots):
                break
        
        return "\n\n".join(reversed(context_parts))
    
    def get_global_memory(self) -> str:
        """获取全局记忆"""
        return self._global_memory
    
    def get_environment_memory(self) -> str:
        """获取环境记忆"""
        return self._environment_memory
    
    def get_jit_context(self) -> str:
        """获取JIT上下文"""
        return "\n\n".join(self._jit_context.values())
    
    def get_combined_context(self) -> str:
        """获取组合后的完整上下文"""
        parts = []
        
        if self._global_memory:
            parts.append(f"## Global Memory\n{self._global_memory}")
        
        if self._environment_memory:
            parts.append(f"## Project Context (GEMINI.md)\n{self._environment_memory}")
        
        jit = self.get_jit_context()
        if jit:
            parts.append(f"## Additional Context\n{jit}")
        
        return "\n\n".join(parts)
    
    async def add_global_memory(self, category: str, content: str) -> None:
        """添加全局记忆条目"""
        entry = MemoryEntry(
            timestamp=datetime.now().timestamp(),
            category=category,
            content=content
        )
        
        # 确保目录存在
        self.global_memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 追加到文件
        entry_text = f"""
---
timestamp: {entry.timestamp}
category: {category}
---
{content}
"""
        
        with open(self.global_memory_path, 'a', encoding='utf-8') as f:
            f.write(entry_text)
        
        # 刷新
        await self._load_global_memory()
    
    def format_for_system_prompt(self) -> str:
        """格式化为系统提示词的一部分"""
        context = self.get_combined_context()
        if not context:
            return ""
        
        return f"""## Memory and Context

{context}

**Note:** Use the above context to inform your responses and decisions."""


class ProjectContextExtractor:
    """项目上下文提取器"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
    
    def extract_structure(self, max_depth: int = 3) -> str:
        """提取项目结构"""
        lines = ["Project Structure:"]
        
        for root, dirs, files in os.walk(self.project_root):
            depth = root.count(os.sep) - str(self.project_root).count(os.sep)
            
            if depth > max_depth:
                del dirs[:]
                continue
            
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            indent = "  " * depth
            rel_path = os.path.relpath(root, self.project_root)
            if rel_path == '.':
                rel_path = os.path.basename(self.project_root) or "."
            
            lines.append(f"{indent}{rel_path}/")
            
            # 显示文件（限制数量）
            shown_files = [f for f in files if not f.startswith('.')][:5]
            for f in shown_files:
                lines.append(f"{indent}  {f}")
            
            if len(files) > 5:
                lines.append(f"{indent}  ... and {len(files) - 5} more files")
        
        return "\n".join(lines)
    
    def find_gemini_md(self) -> Optional[str]:
        """查找GEMINI.md文件"""
        gemini_md = self.project_root / "GEMINI.md"
        if gemini_md.exists():
            return str(gemini_md)
        return None
    
    def extract_tech_stack(self) -> Dict[str, List[str]]:
        """提取技术栈信息"""
        indicators = {
            "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "javascript": ["package.json", "package-lock.json", "yarn.lock"],
            "typescript": ["tsconfig.json"],
            "rust": ["Cargo.toml"],
            "go": ["go.mod"],
            "docker": ["Dockerfile", "docker-compose.yml"],
        }
        
        detected = {k: [] for k in indicators.keys()}
        
        for item in self.project_root.iterdir():
            if item.is_file():
                for tech, files in indicators.items():
                    if item.name in files:
                        detected[tech].append(item.name)
        
        return {k: v for k, v in detected.items() if v}