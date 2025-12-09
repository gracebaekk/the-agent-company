# Testing Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -e .
```

### 2. Start Agents

**Terminal 1** (White Agent):
```bash
python main.py white
```

**Terminal 2** (Green Agent):
```bash
python main.py green
```

### 3. Run Evaluation

**Option A: Automated** (starts/stops agents automatically):
```bash
python main.py launch
```

**Option B: Manual** (agents already running):
Send evaluation request via A2A client or curl to `http://localhost:9001`

Results saved to `evaluation_results.txt`.

## Full Test with Docker

### 1. Start TAC Services
```bash
cd external/tac/servers
bash setup.sh
```

### 2. Set Environment Variables
```bash
export SERVER_HOSTNAME=localhost
export LITELLM_API_KEY=your_api_key
export LITELLM_MODEL=openai/gpt-4o
export DECRYPTION_KEY='theagentcompany is all you need'
```

### 3. Run Evaluation
```bash
python main.py launch
```

## Precomputed Trajectories

To get real scores without running the agent:

1. **Add trajectory**:
   ```bash
   python scripts/utils/add_precomputed_trajectory.py <trajectory_file.json> --task-name <task_name>
   ```

2. **Run evaluation**: `python main.py launch`

The evaluator automatically uses precomputed trajectories if available.

## Manual Testing

### Check Agents
```bash
curl http://localhost:9001/.well-known/agent-card.json
curl http://localhost:9002/.well-known/agent-card.json
```

### Send Manual Request
```python
import asyncio
from src.utils.a2a_client import send_message_to_agent

async def test():
    message = """
Your task is to begin an assessment of the white agent located at:

<white_agent_url>
http://localhost:9002/
</white_agent_url>

Use the following evaluation configuration:

<evaluation_config>
{
  "task_subset": "beginner",
  "max_tasks": 1
}
</evaluation_config>
"""
    response = await send_message_to_agent("http://localhost:9001", message, timeout=900.0)
    print(response)

asyncio.run(test())
```

## Troubleshooting

- **Port already in use**: `lsof -ti:9001 | xargs kill -9`
- **Docker not found**: Install Docker or use mock mode
- **Module not found**: `pip install -e .`
- **Evaluation fails**: Check Docker, environment variables, TAC services
