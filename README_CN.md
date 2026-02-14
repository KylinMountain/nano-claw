# Nano Claw

[English](README.md) | [简体中文](README_CN.md)

一个受 Gemini CLI 启发的轻量级 Python Agent 框架，面向本地可落地工作流：
- Agent Loop + 工具调用
- MCP 集成
- Skills（渐进式披露）
- 记忆上下文
- 人类审批（Human-in-the-loop）

## 快速开始

```bash
git clone https://github.com/yourusername/nano-claw.git
cd nano-claw
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

在 `config.yaml` 中填好 API Key（或用环境变量），然后运行：

```bash
python main.py -c config.yaml
```

## 两种启动方式

### 1) `main.py`（推荐）
- 读取 `config.yaml`
- 按配置初始化 MCP
- 支持 `/mcp`、`/mode`、`/skills` 等命令

```bash
python main.py -c config.yaml
```

### 2) `cli.py`（轻量交互壳）
- 主要使用环境变量
- 输入交互体验更好（`prompt_toolkit`）

```bash
export OPENAI_API_KEY="your-key"
python cli.py
```

## 配置说明

先从示例文件复制：

```bash
cp config.example.yaml config.yaml
```

关键字段：
- `llm.provider`: `openai` 或 `gemini`
- `agent.approval_mode`: `plan` / `default` / `yolo` / `read_only`
- `skills.directories`: Skill 搜索路径
- `mcp.servers`: MCP 服务配置

## 目录结构

```text
core/         # Agent loop、策略、LLM 客户端、类型定义
tools/        # 内置/高级/通用工具
skills/       # Skill 加载与激活
memory/       # 记忆管理
mcp_client/   # MCP 连接与适配器
examples/     # 示例
tests/        # 测试
```

## 注意事项

- `config.yaml` 默认在 `.gitignore` 中，避免误提交密钥。
- 对外分享配置请使用 `config.example.yaml`。
- 项目名称已从 `nano_agent` 统一为 `nano_claw`。

## 开发与测试

```bash
python -m pytest tests/
python examples/basic_demo.py
python examples/mcp_demo.py
```

## 许可证

MIT，详见 `LICENSE`。
