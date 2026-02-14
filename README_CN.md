# 🤖 Nano Agent

> 仅用 ~5K 行代码实现的轻量级、强大的 AI Agent 框架

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Nano Agent 是一个超轻量级的 AI Agent 框架，灵感来自 [Google 的 Gemini CLI](https://github.com/google/generative-ai-docs/tree/main/gemini-cli)，提炼出其核心组件。仅用 **~5,000 行代码**（相比原版的 50,000+ 行），就实现了完整的 Agent 功能，同时保持易于理解和扩展。

[English](README.md) | 简体中文

## ✨ 特性

- 🎯 **超轻量级**：核心功能仅 4,070 行代码
- 🔄 **完整 Agent 循环**：完整的推理和行动周期
- 🛠️ **丰富工具系统**：内置、高级和通用工具
- 🧩 **技能框架**：复杂能力的渐进式披露系统
- 🔗 **MCP 集成**：支持 Model Context Protocol 扩展
- 💾 **记忆管理**：上下文感知的对话记忆
- 🎨 **智能策略引擎**：智能审批和安全控制
- 🌐 **多 LLM 支持**：OpenAI、Anthropic、Google 等

## 📊 代码统计

| 模块 | 行数 | 说明 |
|------|------|------|
| **core/** | 1,335 | Agent 循环、LLM 客户端、策略引擎 |
| **tools/** | 1,843 | 工具系统（基础、内置、高级、通用） |
| **skills/** | 337 | 技能管理系统 |
| **mcp/** | 330 | Model Context Protocol 集成 |
| **memory/** | 225 | 记忆管理系统 |
| **总计** | **~5K** | 完整的 Agent 框架 |

**对比**：Nano Agent 仅用类似框架 **10%** 的代码量就实现了完整功能。

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/nano-claw.git
cd nano-claw

# 安装依赖
pip install -r requirements.txt

# 设置 API 密钥
export OPENAI_API_KEY="your-api-key-here"
```

### 基础使用

```python
from nano_claw.core.llm_client import LLMClient
from nano_claw.core.agent_loop import AgentLoop, AgentConfig
from nano_claw.core.policy import PolicyEngine, ApprovalMode

# 初始化组件
llm = LLMClient(provider="openai", model="gpt-4")
policy = PolicyEngine(approval_mode=ApprovalMode.AUTO)
config = AgentConfig(max_iterations=10)

# 创建并运行 Agent
agent = AgentLoop(llm_client=llm, policy_engine=policy, config=config)
result = await agent.run("今天天气怎么样？")
```

### 命令行界面

```bash
# 交互模式
python main.py

# 使用自定义配置
python main.py --config my_config.yaml

# 运行演示
python examples/basic_demo.py
```

## 📖 文档

- [快速开始指南](docs/quickstart.md) - 5 分钟上手
- [架构概览](docs/architecture.md) - 系统设计和组件
- [MCP 集成指南](docs/mcp_guide.md) - 使用 MCP 服务器扩展
- [设计理念](docs/design.md) - Nano Agent 的设计哲学
- [教程系列](docs/tutorial/) - 深入学习（7 章教程）

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                     Agent 循环                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ 感知     │→ │ 推理     │→ │ 行动     │→ 结果       │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
         ↓              ↓              ↓
    ┌────────┐    ┌─────────┐   ┌──────────┐
    │ 记忆   │    │ 策略    │   │ 工具     │
    │ 系统   │    │ 引擎    │   │ 系统     │
    └────────┘    └─────────┘   └──────────┘
         ↓              ↓              ↓
    ┌────────────────────────────────────────┐
    │         LLM 客户端（多提供商）         │
    └────────────────────────────────────────┘
```

### 核心组件

1. **Agent 循环** (`core/agent_loop.py`) - 主推理和行动周期
2. **LLM 客户端** (`core/llm_client.py`) - 多提供商 LLM 接口
3. **策略引擎** (`core/policy.py`) - 安全和审批控制
4. **工具系统** (`tools/`) - 可扩展的工具框架
5. **技能管理器** (`skills/`) - 渐进式能力披露
6. **记忆管理器** (`memory/`) - 上下文感知的对话记忆
7. **MCP 客户端** (`mcp/`) - Model Context Protocol 集成

## 🛠️ 工具系统

Nano Agent 包含三层工具：

### 内置工具
- 文件操作（读取、写入、搜索）
- Shell 命令执行
- 网络搜索和抓取
- 代码分析

### 高级工具
- Git 操作
- 数据库查询
- API 集成
- 数据处理

### 通用工具
- 日历管理
- 邮件处理
- 笔记记录
- 任务管理

## 🧩 技能系统

技能提供复杂能力的渐进式披露：

```python
# 按需激活技能
agent.activate_skill("code-reviewer")
agent.activate_skill("docs-writer")
```

内置技能：
- **code-reviewer**：代码审查和分析
- **docs-writer**：文档生成
- **meeting-scheduler**：日历管理
- **study-helper**：学习辅助
- **travel-planner**：旅行规划

## 🔗 MCP 集成

使用 Model Context Protocol 服务器扩展 Nano Agent：

```yaml
# config.yaml
mcp:
  enabled: true
  servers:
    - name: filesystem
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
    - name: github
      command: npx
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: ${GITHUB_TOKEN}
```

## 🎯 使用场景

- **代码助手**：审查、重构和生成代码
- **研究助手**：搜索、总结和分析信息
- **任务自动化**：自动化重复性工作流
- **学习伙伴**：学习辅助和知识管理
- **项目管理**：规划、跟踪和协调

## 🔧 配置

创建 `config.yaml` 文件：

```yaml
llm:
  provider: openai  # openai, anthropic, google 等
  openai:
    model: gpt-4
    temperature: 0.7
    max_tokens: 2000

policy:
  approval_mode: auto  # auto, manual, smart
  allowed_tools:
    - read_file
    - write_file
    - run_command

memory:
  enabled: true
  max_context_length: 10000

skills:
  auto_activate: false
  available:
    - code-reviewer
    - docs-writer
```

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python tests/test_core.py

# 运行示例
python examples/basic_demo.py
python examples/mcp_demo.py
```

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。对于重大更改，请先开 issue 讨论您想要更改的内容。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 灵感来自 [Google 的 Gemini CLI](https://github.com/google/generative-ai-docs/tree/main/gemini-cli)
- 为 AI Agent 社区倾情打造
- 特别感谢所有贡献者

## 📬 联系方式

- GitHub Issues：[报告 bug 或请求功能](https://github.com/yourusername/nano-claw/issues)
- 讨论区：[加入讨论](https://github.com/yourusername/nano-claw/discussions)

## 🗺️ 路线图

- [ ] 发布到 PyPI
- [ ] Docker 支持
- [ ] Web UI 界面
- [ ] 更多内置技能
- [ ] 插件市场
- [ ] 多 Agent 协作
- [ ] 增强记忆系统
- [ ] 性能优化

---

**由 Nano Agent 团队用 ❤️ 打造**

*轻量级不意味着功能少 - 而是更专注。*
