# 🤖 Nano Agent

> A lightweight, powerful AI agent framework in just ~5K lines of code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Nano Agent is an ultra-lightweight AI agent framework inspired by [Google's Gemini CLI](https://github.com/google/generative-ai-docs/tree/main/gemini-cli), distilled down to its essential components. With only **~5,000 lines of code** (compared to 50,000+ in the original), it delivers complete agent functionality while remaining easy to understand and extend.

## ✨ Features

- 🎯 **Ultra Lightweight**: Core functionality in just 4,070 lines
- 🔄 **Complete Agent Loop**: Full reasoning and action cycle
- 🛠️ **Rich Tool System**: Built-in, advanced, and universal tools
- 🧩 **Skills Framework**: Progressive disclosure system for complex capabilities
- 🔗 **MCP Integration**: Model Context Protocol support for extensibility
- 💾 **Memory Management**: Context-aware conversation memory
- 🎨 **Smart Policy Engine**: Intelligent approval and safety controls
- 🌐 **Multi-LLM Support**: OpenAI, Anthropic, Google, and more

## 📊 Code Statistics

| Module | Lines | Description |
|--------|-------|-------------|
| **core/** | 1,335 | Agent loop, LLM client, policy engine |
| **tools/** | 1,843 | Tool system (base, builtin, advanced, universal) |
| **skills/** | 337 | Skills management system |
| **mcp/** | 330 | Model Context Protocol integration |
| **memory/** | 225 | Memory management system |
| **Total** | **~5K** | Complete agent framework |

**Comparison**: Nano Agent achieves full functionality with only **10%** of the code size of similar frameworks.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/nano-claw.git
cd nano-claw

# Install dependencies
pip install -r requirements.txt

# Set up your API key
export OPENAI_API_KEY="your-api-key-here"
```

### Basic Usage

```python
from nano_claw.core.llm_client import LLMClient
from nano_claw.core.agent_loop import AgentLoop, AgentConfig
from nano_claw.core.policy import PolicyEngine, ApprovalMode

# Initialize components
llm = LLMClient(provider="openai", model="gpt-4")
policy = PolicyEngine(approval_mode=ApprovalMode.AUTO)
config = AgentConfig(max_iterations=10)

# Create and run agent
agent = AgentLoop(llm_client=llm, policy_engine=policy, config=config)
result = await agent.run("What's the weather like today?")
```

### Command Line Interface

```bash
# Interactive mode
python main.py

# With custom config
python main.py --config my_config.yaml

# Run a demo
python examples/basic_demo.py
```

## 📖 Documentation

- [Quick Start Guide](docs/quickstart.md) - Get up and running in 5 minutes
- [Architecture Overview](docs/architecture.md) - System design and components
- [MCP Integration Guide](docs/mcp_guide.md) - Extend with MCP servers
- [Design Philosophy](docs/design.md) - Why Nano Agent exists
- [Tutorial Series](docs/tutorial/) - In-depth learning (7 chapters, Chinese)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Agent Loop                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Perceive │→ │ Reason   │→ │ Act      │→ Result     │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
         ↓              ↓              ↓
    ┌────────┐    ┌─────────┐   ┌──────────┐
    │ Memory │    │ Policy  │   │ Tools    │
    │ System │    │ Engine  │   │ System   │
    └────────┘    └─────────┘   └──────────┘
         ↓              ↓              ↓
    ┌────────────────────────────────────────┐
    │         LLM Client (Multi-Provider)    │
    └────────────────────────────────────────┘
```

### Core Components

1. **Agent Loop** (`core/agent_loop.py`) - Main reasoning and action cycle
2. **LLM Client** (`core/llm_client.py`) - Multi-provider LLM interface
3. **Policy Engine** (`core/policy.py`) - Safety and approval controls
4. **Tool System** (`tools/`) - Extensible tool framework
5. **Skills Manager** (`skills/`) - Progressive capability disclosure
6. **Memory Manager** (`memory/`) - Context-aware conversation memory
7. **MCP Client** (`mcp/`) - Model Context Protocol integration

## 🛠️ Tool System

Nano Agent includes three tiers of tools:

### Built-in Tools
- File operations (read, write, search)
- Shell command execution
- Web search and fetch
- Code analysis

### Advanced Tools
- Git operations
- Database queries
- API integrations
- Data processing

### Universal Tools
- Calendar management
- Email handling
- Note-taking
- Task management

## 🧩 Skills System

Skills provide progressive disclosure of complex capabilities:

```python
# Skills are activated on-demand
agent.activate_skill("code-reviewer")
agent.activate_skill("docs-writer")
```

Built-in skills:
- **code-reviewer**: Code review and analysis
- **docs-writer**: Documentation generation
- **meeting-scheduler**: Calendar management
- **study-helper**: Learning assistance
- **travel-planner**: Trip planning

## 🔗 MCP Integration

Extend Nano Agent with Model Context Protocol servers:

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

## 🎯 Use Cases

- **Code Assistant**: Review, refactor, and generate code
- **Research Helper**: Search, summarize, and analyze information
- **Task Automation**: Automate repetitive workflows
- **Learning Companion**: Study assistance and knowledge management
- **Project Management**: Planning, tracking, and coordination

## 🔧 Configuration

Create a `config.yaml` file:

```yaml
llm:
  provider: openai  # openai, anthropic, google, etc.
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

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/test_core.py

# Run examples
python examples/basic_demo.py
python examples/mcp_demo.py
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [Google's Gemini CLI](https://github.com/google/generative-ai-docs/tree/main/gemini-cli)
- Built with love for the AI agent community
- Special thanks to all contributors

## 📬 Contact

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/nano-claw/issues)
- Discussions: [Join the conversation](https://github.com/yourusername/nano-claw/discussions)

## 🗺️ Roadmap

- [ ] PyPI package release
- [ ] Docker support
- [ ] Web UI interface
- [ ] More built-in skills
- [ ] Plugin marketplace
- [ ] Multi-agent collaboration
- [ ] Enhanced memory system
- [ ] Performance optimizations

---

**Made with ❤️ by the Nano Agent team**

*Lightweight doesn't mean less powerful - it means more focused.*
