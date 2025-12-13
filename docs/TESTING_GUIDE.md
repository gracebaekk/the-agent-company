# Testing Guide

## Quick Start

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start services (wait 2-3 min)
cd external/tac/servers && make start-api-server-with-setup

# Verify
python ../../scripts/check_services.py

# Run evaluation
export OPENAI_API_KEY="sk-proj-..."
python main.py launch
```

Results in `evaluation_results.txt`.

## Select Tasks

Edit `src/launcher.py` line ~95-115:
```python
"task_names": [
    "pm-send-hello-message",
    "admin-arrange-meeting-rooms",
]
```

## Agent Beats (Ngrok)

```bash
# Start agents
bash scripts/start_agents.sh tmux

# Check health
curl http://localhost:9001/.well-known/agent-card.json
curl http://localhost:9002/.well-known/agent-card.json

# Expose
bash scripts/start_ngrok.sh

# Register ngrok URLs in Agent Beats

# Stop
tmux kill-session -t green_agent
tmux kill-session -t white_agent
```

## Verify Services

```bash
python scripts/check_services.py

# Individual checks
curl http://localhost:2999      # API Server
curl http://localhost:3000      # RocketChat
curl http://localhost:8929      # GitLab
curl http://localhost:8091      # Plane
curl http://localhost:8092      # OwnCloud
```

## Debug

```bash
# Agent logs (tmux)
tmux attach -t green_agent    # Ctrl+B then D to detach

# Docker containers
docker ps --filter "name=tac_eval"

# Trajectories
ls -lt /var/folders/*/T/tac_eval_*/traj_*.json | head -5
cat <path> | python -m json.tool
```

## Common Issues

| Problem | Fix |
|---------|-----|
| Agents not running | `bash scripts/start_agents.sh tmux` |
| File not in container | Restart agents to reload Docker bridge |
| API key error | `export OPENAI_API_KEY="..."` in same terminal |
| Service down | `python scripts/check_services.py` then restart |
| Port in use | `lsof -ti:PORT \| xargs kill -9` |

## Restart Services

```bash
cd external/tac/servers
make restart-rocketchat
make restart-gitlab
make restart-api-server
```

## Task Categories

In `src/green_agent/evaluation/task_selector.py`:
- **PM**: RocketChat, Plane, GitLab
- **Admin**: Files, spreadsheets, PDFs
- **HR, Finance, SDE**: Various workflows
