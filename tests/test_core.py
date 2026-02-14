"""
测试用例 - Nano Claw System
"""
import pytest
from pathlib import Path
import tempfile
import shutil

# 测试导入
from nano_claw.core.types import AgentState, Message, ToolResult
from nano_claw.core.tool_registry import ToolRegistry, tool
from nano_claw.tools.builtin import BuiltinTools
from nano_claw.skills.manager import SkillsManager
from nano_claw.memory.manager import MemoryManager
from nano_claw.core.policy import PolicyEngine, PolicyDecision


class TestToolRegistry:
    """测试工具注册系统"""
    
    def setup_method(self):
        self.registry = ToolRegistry()
    
    def test_register_function_tool(self):
        """测试注册函数工具"""
        @tool(description="测试工具")
        def test_tool(x: int, y: int = 10) -> int:
            return x + y
        
        self.registry.register(test_tool)
        assert "test_tool" in self.registry.list_tools()
    
    def test_call_tool(self):
        """测试调用工具"""
        @tool(description="加法工具")
        def add(a: int, b: int) -> int:
            return a + b
        
        self.registry.register(add)
        result = self.registry.call("add", {"a": 5, "b": 3})
        assert result.success
        assert result.result == 8


class TestBuiltinTools:
    """测试内置工具"""
    
    def test_file_read(self):
        """测试文件读取工具"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello World")
            f.flush()
            
            tools = BuiltinTools()
            result = tools.read_file(f.name)
            
            assert result.success
            assert "Hello World" in result.result
            
            # 清理
            Path(f.name).unlink()
    
    def test_file_write(self):
        """测试文件写入工具"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = f"{tmpdir}/test.txt"
            tools = BuiltinTools()
            result = tools.write_file(filepath, "Test Content")
            
            assert result.success
            assert Path(filepath).read_text() == "Test Content"
    
    def test_list_directory(self):
        """测试目录列表工具"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(f"{tmpdir}/file1.txt").touch()
            Path(f"{tmpdir}/file2.txt").touch()
            
            tools = BuiltinTools()
            result = tools.list_dir(tmpdir)
            
            assert result.success
            assert "file1.txt" in result.result
            assert "file2.txt" in result.result


class TestSkillsManager:
    """测试技能管理系统"""
    
    def test_load_skill(self):
        """测试加载技能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建临时技能目录
            skill_dir = Path(tmpdir) / "test_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""
# Test Skill
描述: 这是一个测试技能
使用方法: test_skill [参数]
            """)
            
            manager = SkillsManager(tmpdir)
            skills = manager.load_all_skills()
            
            assert len(skills) == 1
            assert skills[0].name == "test_skill"


class TestMemoryManager:
    """测试记忆管理系统"""
    
    def test_gemini_md_read(self):
        """测试GEMINI.md读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gemini_md = Path(tmpdir) / "GEMINI.md"
            gemini_md.write_text("""
# Project Context
这是一个测试项目
            """)
            
            manager = MemoryManager(tmpdir)
            memory = manager.read_gemini_md()
            
            assert memory is not None
            assert "测试项目" in memory
    
    def test_working_memory(self):
        """测试工作记忆"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(tmpdir)
            
            # 添加工作记忆
            manager.add_working_memory("user preference", "user likes Python")
            
            # 检索
            results = manager.retrieve_working_memory("preference")
            assert len(results) > 0


class TestPolicyEngine:
    """测试策略引擎"""
    
    def test_policy_check(self):
        """测试策略检查"""
        engine = PolicyEngine()
        
        # 无风险操作应通过
        decision = engine.evaluate(
            action="read_file",
            target="/safe/path",
            context={}
        )
        assert decision == PolicyDecision.APPROVED
        
        # 高风险操作应需要确认
        decision = engine.evaluate(
            action="delete_file",
            target="/important/path",
            context={}
        )
        assert decision == PolicyDecision.REQUIRES_CONFIRMATION


class TestAgentState:
    """测试Agent状态"""
    
    def test_state_transitions(self):
        """测试状态转换"""
        state = AgentState()
        
        assert state.current == "idle"
        
        state.transition("processing")
        assert state.current == "processing"
        
        state.transition("waiting_for_human")
        assert state.current == "waiting_for_human"
        
        state.transition("completed")
        assert state.current == "completed"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
