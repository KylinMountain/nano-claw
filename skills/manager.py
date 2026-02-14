"""
Skills系统 - 渐进式披露设计
模仿Gemini CLI的Skills架构
"""
import os
import re
from typing import Dict, List, Optional
from pathlib import Path
import yaml

from core.types import SkillDefinition, ConfirmationDetails
from tools.base import ToolBuilder, ToolInvocation, ToolKind, ToolResult


# Frontmatter正则表达式
FRONTMATTER_REGEX = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', re.DOTALL)


class SkillLoader:
    """Skill加载器"""
    
    @staticmethod
    def parse_frontmatter(content: str) -> Optional[tuple]:
        """解析YAML Frontmatter"""
        match = FRONTMATTER_REGEX.match(content)
        if not match:
            return None
        
        try:
            frontmatter = yaml.safe_load(match.group(1))
            body = match.group(2).strip()
            return frontmatter, body
        except yaml.YAMLError:
            return None
    
    @classmethod
    def load_from_file(cls, file_path: str) -> Optional[SkillDefinition]:
        """从文件加载Skill"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed = cls.parse_frontmatter(content)
            if not parsed:
                return None
            
            frontmatter, body = parsed
            
            return SkillDefinition(
                name=frontmatter.get('name', ''),
                description=frontmatter.get('description', ''),
                location=file_path,
                body=body,
                disabled=frontmatter.get('disabled', False),
                is_builtin=frontmatter.get('is_builtin', False)
            )
        except Exception as e:
            print(f"Error loading skill from {file_path}: {e}")
            return None
    
    @classmethod
    def load_from_dir(cls, directory: str) -> List[SkillDefinition]:
        """从目录加载所有Skills"""
        skills = []
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return skills
        
        # 查找 SKILL.md 和 */SKILL.md
        patterns = ['SKILL.md', '*/SKILL.md']
        
        for pattern in patterns:
            for skill_file in dir_path.glob(pattern):
                skill = cls.load_from_file(str(skill_file))
                if skill:
                    skills.append(skill)
        
        return skills


class SkillManager:
    """Skill管理器"""
    
    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
        self._active_skills: set = set()
        self._builtin_dir: Optional[str] = None
        self._user_dir: Optional[str] = None
        self._workspace_dir: Optional[str] = None
    
    def set_directories(
        self,
        builtin_dir: Optional[str] = None,
        user_dir: Optional[str] = None,
        workspace_dir: Optional[str] = None
    ) -> None:
        """设置Skill目录"""
        self._builtin_dir = builtin_dir
        self._user_dir = user_dir
        self._workspace_dir = workspace_dir
    
    def discover_skills(self) -> None:
        """发现所有Skills（按优先级合并）"""
        self._skills.clear()
        
        # 1. 加载内置Skills（最低优先级）
        if self._builtin_dir:
            builtin_skills = SkillLoader.load_from_dir(self._builtin_dir)
            for skill in builtin_skills:
                skill.is_builtin = True
                self._add_skill(skill)
        
        # 2. 加载用户Skills
        if self._user_dir:
            user_skills = SkillLoader.load_from_dir(self._user_dir)
            for skill in user_skills:
                self._add_skill(skill, override=True)
        
        # 3. 加载Workspace Skills（最高优先级）
        if self._workspace_dir:
            workspace_skills = SkillLoader.load_from_dir(self._workspace_dir)
            for skill in workspace_skills:
                self._add_skill(skill, override=True)
    
    def _add_skill(self, skill: SkillDefinition, override: bool = False) -> None:
        """添加Skill"""
        existing = self._skills.get(skill.name)
        
        if existing and not override:
            return
        
        if existing and existing.is_builtin and not skill.is_builtin:
            print(f"Warning: Skill '{skill.name}' from '{skill.location}' is overriding built-in skill")
        elif existing and not existing.is_builtin:
            print(f"Warning: Skill conflict detected: '{skill.name}' from '{skill.location}' overrides '{existing.location}'")
        
        self._skills[skill.name] = skill
    
    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """获取Skill"""
        return self._skills.get(name)
    
    def get_all_skills(self) -> List[SkillDefinition]:
        """获取所有Skills"""
        return list(self._skills.values())
    
    def get_available_skills(self) -> List[SkillDefinition]:
        """获取可用的Skills（未禁用）"""
        return [s for s in self._skills.values() if not s.disabled]
    
    def get_displayable_skills(self) -> List[SkillDefinition]:
        """获取可显示的Skills（非内置、未禁用）"""
        return [s for s in self._skills.values() if not s.disabled and not s.is_builtin]
    
    def activate_skill(self, name: str) -> bool:
        """激活Skill"""
        skill = self._skills.get(name)
        if skill and not skill.disabled:
            self._active_skills.add(name)
            skill.active = True
            return True
        return False
    
    def deactivate_skill(self, name: str) -> None:
        """停用Skill"""
        self._active_skills.discard(name)
        if name in self._skills:
            self._skills[name].active = False
    
    def is_skill_active(self, name: str) -> bool:
        """检查Skill是否激活"""
        return name in self._active_skills
    
    def get_active_skills(self) -> List[SkillDefinition]:
        """获取已激活的Skills"""
        return [self._skills[name] for name in self._active_skills if name in self._skills]
    
    def generate_skills_prompt(self) -> str:
        """生成Skills提示词（仅Metadata，渐进式披露Level 1）"""
        skills = self.get_available_skills()
        
        if not skills:
            return ""
        
        skill_xml = '\n'.join([
            f"""  <skill>
    <name>{s.name}</name>
    <description>{s.description}</description>
    <location>{s.location}</location>
  </skill>"""
            for s in skills
        ])
        
        return f"""## Available Agent Skills

You have access to the following specialized skills. To activate a skill and receive its detailed instructions, call the `activate_skill` tool with the skill's name.

<available_skills>
{skill_xml}
</available_skills>

**Skill Guidance:** Once a skill is activated, its instructions and resources are returned wrapped in `<activated_skill>` tags. You MUST treat the content within `<instructions>` as expert procedural guidance, prioritizing these specialized rules and workflows over your general defaults for the duration of the task."""
    
    def get_activated_skill_content(self, name: str) -> Optional[str]:
        """获取已激活Skill的完整内容（渐进式披露Level 2）"""
        skill = self._skills.get(name)
        if not skill or not skill.active:
            return None
        
        # 获取技能目录下的资源
        skill_dir = os.path.dirname(skill.location)
        resources = []
        
        if os.path.exists(skill_dir):
            for item in os.listdir(skill_dir):
                if item != 'SKILL.md':
                    resources.append(item)
        
        resources_xml = '\n    '.join([f"<item>{r}</item>" for r in resources])
        
        return f"""<activated_skill name="{name}">
  <instructions>
{skill.body}
  </instructions>

  <available_resources>
    {resources_xml}
  </available_resources>
</activated_skill>"""


class ActivateSkillInvocation(ToolInvocation):
    """激活Skill工具调用"""
    
    def __init__(self, *args, skill_manager: SkillManager, **kwargs):
        super().__init__(*args, **kwargs)
        self.skill_manager = skill_manager
    
    def should_confirm(self) -> bool:
        """非内置Skill需要确认"""
        skill_name = self.params.get("name", "")
        skill = self.skill_manager.get_skill(skill_name)
        return skill is not None and not skill.is_builtin
    
    def get_confirmation_details(self):
        """获取确认详情"""
        skill_name = self.params.get("name", "")
        skill = self.skill_manager.get_skill(skill_name)
        
        if not skill or skill.is_builtin:
            return None
        
        return ConfirmationDetails(
            title=f"Activate Skill: {skill_name}",
            prompt=f"""You are about to enable the specialized agent skill **{skill_name}**.

**Description:**
{skill.description}

**Resources to be shared with the model:**
{os.path.dirname(skill.location)}""",
            tool_name=self.name,
            arguments=self.params
        )
    
    async def execute(self, cancellation_event) -> ToolResult:
        try:
            skill_name = self.params.get("name", "")
            skill = self.skill_manager.get_skill(skill_name)
            
            if not skill:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=f"Skill '{skill_name}' not found"
                )
            
            if skill.disabled:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=f"Skill '{skill_name}' is disabled"
                )
            
            # 激活Skill
            self.skill_manager.activate_skill(skill_name)
            
            # 获取完整内容
            content = self.skill_manager.get_activated_skill_content(skill_name)
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=content or f"Skill '{skill_name}' activated"
            )
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class ActivateSkillTool(ToolBuilder):
    """激活Skill工具"""
    
    def __init__(self, skill_manager: SkillManager):
        self.skill_manager = skill_manager
        super().__init__(
            name="activate_skill",
            display_name="Activate Skill",
            description="Activate a specialized skill to receive its detailed instructions and resources",
            kind=ToolKind.SKILL,
            parameter_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the skill to activate"
                    }
                },
                "required": ["name"]
            }
        )
    
    def build(self, call_id: str, params: dict) -> ToolInvocation:
        return ActivateSkillInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id,
            skill_manager=self.skill_manager
        )