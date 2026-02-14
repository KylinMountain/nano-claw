# Nano Claw

[English](README.md) | [简体中文](README_CN.md)

A lightweight Python agent framework inspired by Gemini CLI, focused on practical local workflows:
- Agent loop with tool calling
- MCP integration
- Skills (progressive disclosure)
- Memory context
- Human-in-the-loop approval

## Quick Start

```bash
git clone https://github.com/yourusername/nano-claw.git
cd nano-claw
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Set your API key in `config.yaml` (or environment variable), then run:

```bash
python main.py -c config.yaml
```

## Run Modes

### 1) `main.py` (recommended)
- Reads `config.yaml`
- Initializes MCP from config
- Supports commands like `/mcp`, `/mode`, `/skills`

```bash
python main.py -c config.yaml
```

### 2) `cli.py` (lighter interactive shell)
- Primarily uses environment variables
- Better prompt interaction (`prompt_toolkit`)

```bash
export OPENAI_API_KEY="your-key"
python cli.py
```

## Configuration

Start from `config.example.yaml`:

```bash
cp config.example.yaml config.yaml
```

Important fields:
- `llm.provider`: `openai` or `gemini`
- `agent.approval_mode`: `plan` / `default` / `yolo` / `read_only`
- `skills.directories`: skill search paths
- `mcp.servers`: MCP server definitions

## Project Structure

```text
core/         # agent loop, policy, llm client, types
tools/        # built-in / advanced / universal tools
skills/       # skill loader and activation
memory/       # memory manager
mcp_client/   # MCP connection and adapters
examples/     # demos
tests/        # tests
```

## Notes

- `config.yaml` is ignored by git by default (to avoid leaking keys).
- Use `config.example.yaml` for sharing config structure.
- If you previously used `nano_agent`, this project is now renamed to `nano_claw`.

## Development

```bash
python -m pytest tests/
python examples/basic_demo.py
python examples/mcp_demo.py
```

## License

MIT. See `LICENSE`.
