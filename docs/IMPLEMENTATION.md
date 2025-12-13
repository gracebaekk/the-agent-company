# TAC Agent Implementation

A2A-compatible evaluation system for The Agent Company benchmark.

## Architecture

```
Green Agent (Evaluator) → Selects tasks, sends to White Agent, runs Docker evaluation
White Agent (Target)    → Receives tasks, executes with Docker bridge for file access
```

## Key Features

### Docker Bridge
White agent reads/writes files directly in task containers:
- Detects paths: `/workspace/`, `/instruction/`, `/utils/`
- Uses `docker exec` (read) and `docker cp` (write)
- Filters out NPC containers

### Enhanced Tasks
- **PM**: RocketChat, Plane, GitLab APIs with conditional logic
- **Admin**: File operations in Docker containers
- **Service Integration**: RocketChat (3000), GitLab (8929), Plane (8091), OwnCloud (8092)

## Structure

```
src/
├── green_agent/evaluation/    # Task selection, evaluation, scoring
├── white_agent/agent.py       # Docker bridge + tool execution
├── data/task_instructions.json
└── launcher.py                # Auto-launch evaluation

scripts/
├── start_agents.sh            # Start agents in tmux
├── start_ngrok.sh             # Expose via ngrok
└── check_services.py          # Verify services

external/tac/servers/          # API server + all services
```

## Setup

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start services
cd external/tac/servers
make start-api-server-with-setup

# 3. Verify (wait 2-3 min)
python ../../scripts/check_services.py
```

## Usage

### Local
```bash
export OPENAI_API_KEY="sk-proj-..."
python main.py launch
```

### Agent Beats
```bash
bash scripts/start_agents.sh tmux
bash scripts/start_ngrok.sh
# Use ngrok URLs in Agent Beats
```

## Task Selection

Edit `src/launcher.py` line ~95:
```python
"task_names": ["pm-send-hello-message", "admin-arrange-meeting-rooms"]
```

## Environment

```bash
OPENAI_API_KEY=sk-proj-...
SERVER_HOSTNAME=localhost
LITELLM_MODEL=openai/gpt-4o
DECRYPTION_KEY='theagentcompany is all you need'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Services down | `make start-api-server-with-setup` in `external/tac/servers` |
| Files go to host | Restart agents to reload code |
| API key error | Export in same terminal as `python main.py launch` |
| Port conflict | `lsof -ti:PORT \| xargs kill -9` |
