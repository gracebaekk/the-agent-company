# TAC Green Agent Implementation

A2A-compatible assessment agent that evaluates white agents using the TAC benchmark framework.

## Overview

The green agent:
- Selects tasks from predefined subsets
- Sends tasks to white agents via A2A protocol
- Collects trajectories of agent actions
- Runs Docker-based TAC evaluations
- Aggregates and reports results

## Architecture

```
Green Agent (A2A Server)
  ├── TaskSelector → Selects tasks from TASK_SUBSETS
  ├── TACEvaluator → Orchestrates evaluation
  │   ├── DockerManager → Manages Docker containers
  │   └── TrajectoryCollector → Tracks agent actions
  └── White Agent (A2A) → Receives tasks, performs actions
```

## Components

### 1. Green Agent (`src/green_agent/agent.py`)
- Parses evaluation requests (white agent URL + config)
- Selects tasks using `TaskSelector`
- Runs evaluations using `TACEvaluator`
- Formats and returns results

**Request Format:**
```
Your task is to begin an assessment of the white agent located at:

<white_agent_url>
http://localhost:9002/
</white_agent_url>

Use the following evaluation configuration:

<evaluation_config>
{
  "task_subset": "intermediate",
  "max_tasks": 3
}
</evaluation_config>
```

### 2. Task Selector (`src/green_agent/evaluation/task_selector.py`)
Selects tasks from predefined subsets: `beginner`, `intermediate`, `advanced`, `coding_focused`, `communication_focused`, `multi_service`.

### 3. Docker Manager (`src/utils/docker_manager.py`)
Manages Docker containers: pulls images, extracts instructions, initializes tasks, runs evaluations.

### 4. Trajectory Collector (`src/data/trajectory_collector.py`)
Collects and saves agent interaction trajectories in TAC-compatible JSON format.

### 5. TAC Evaluator (`src/green_agent/evaluation/evaluator.py`)
Orchestrates evaluation: pulls Docker image → extracts task → sends to white agent → collects trajectory → runs Docker evaluation → returns results.

## Setup

### Prerequisites
- Docker installed and running
- TAC services (GitLab, RocketChat, Plane, OwnCloud)
- Python 3.12+ with dependencies: `pip install -e .`

### Environment Variables
```bash
SERVER_HOSTNAME=localhost
LITELLM_API_KEY=your_api_key
LITELLM_MODEL=openai/gpt-4o
DECRYPTION_KEY='theagentcompany is all you need'
```

## Usage

1. **Start TAC Services**: `cd external/tac/servers && bash setup.sh`
2. **Start White Agent**: `python main.py white`
3. **Start Green Agent**: `python main.py green`
4. **Run Evaluation**: `python main.py launch`

Results saved to `evaluation_results.txt`.

## File Structure

```
src/
├── green_agent/
│   ├── agent.py                 # Main executor
│   └── evaluation/
│       ├── evaluator.py         # Evaluation orchestrator
│       ├── task_selector.py     # Task selection
│       └── scoring.py           # Custom scoring (optional)
├── white_agent/
│   └── agent.py                 # White agent implementation
├── utils/
│   ├── a2a_client.py           # A2A client utilities
│   └── docker_manager.py       # Docker management
└── data/
    ├── trajectory_collector.py  # Trajectory collection
    └── trajectories/            # Precomputed trajectories
```

## Customization

**Task Selection**: Modify `TASK_SUBSETS` in `task_selector.py`

**Scoring**: Implement custom strategies in `scoring.py` and integrate in `evaluator.py`

## Testing

**Automated**: `python main.py launch` (starts/stops agents automatically)

**Manual**: Start agents separately, then send evaluation request via A2A client.

## Troubleshooting

- **Docker not found**: Install Docker Desktop/Engine
- **Cannot connect to Docker**: Start Docker daemon
- **Network host not supported** (Mac/Windows): Enable host networking in Docker Desktop
- **Services not accessible**: Check `SERVER_HOSTNAME` matches service location
- **Evaluation fails**: Check environment variables, Docker logs, service health
