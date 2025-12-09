# The Agent Company - Green Agent

Green agent (assessor) implementation for The Agent Company framework that evaluates white agents using standardized assessment protocols.

## Installation

```bash
git clone <repository-url>
cd the-agent-company
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Green Agent

### Local Development with AgentBeats

```bash
export HTTPS_ENABLED=true
export ROLE=green
agentbeats run_ctrl
```

Access the controller at `http://localhost:8010/info`.

### Direct Python Execution

```bash
python main.py green
```

Runs on `http://localhost:9001` by default.

### Environment Variables

- `AGENT_PORT`: Port number (default: `9001`)
- `HTTPS_ENABLED`: Enable HTTPS URLs (default: `false`)
- `CLOUDRUN_HOST`: External hostname for deployed services
- `ROLE`: Set to `green` for green agent

## Testing

### Test Agent Communication

```bash
python main.py test --url http://localhost:9001 --message "Hello!"
```

### Test Evaluation Workflow

```bash
# Run full evaluation test
python -m tests.test_evaluation

# Check evaluation results
python -m tests.check_results

# View full results
python -m tests.view_full_results
```

See `tests/README.md` for more details.

### Test Agent Card

```bash
curl http://localhost:9001/.well-known/agent-card.json
```

### Test Controller (if using AgentBeats)

```bash
curl http://localhost:8010/info
curl http://localhost:8010/agents
```

## Deployment

### Google Cloud Run

1. Set up Google Cloud project and enable billing:
```bash
gcloud projects create your-project-id
gcloud config set project your-project-id
gcloud billing projects link your-project-id --billing-account=YOUR_BILLING_ACCOUNT
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
```

2. Deploy:
```bash
gcloud run deploy agent-company-green-agent \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ROLE=green,HTTPS_ENABLED=true" \
  --memory 512Mi
```

3. Update with service URL:
```bash
SERVICE_URL=$(gcloud run services describe agent-company-green-agent --region us-central1 --format 'value(status.url)')
gcloud run services update agent-company-green-agent \
  --region us-central1 \
  --update-env-vars "ROLE=green,HTTPS_ENABLED=true,CLOUDRUN_HOST=${SERVICE_URL#https://}"
```

### Local Development with External Access (ngrok)

```bash
# Terminal 1: Start ngrok
ngrok http 8010

# Terminal 2: Run with ngrok URL
HTTPS_ENABLED=true CLOUDRUN_HOST=xxxx-xxxx.ngrok-free.dev ROLE=green agentbeats run_ctrl
```

## AgentBeats Platform Integration

1. Register agent with Controller URL (root URL, no `/info`):
   - Cloud Run: `https://your-service-url.run.app`
   - ngrok: `https://your-ngrok-url.ngrok-free.dev`

2. Set "Deploy Type" to "Remote" and check "Is Assessor (Green) Agent"

3. Click "Check Again" to verify agent card loads

## Evaluation Configuration

The green agent uses this evaluation config format:

```json
{
  "agent_strategy": "tool-calling",
  "agent_model": "gpt-4o",
  "agent_provider": "openai",
  "user_strategy": "react",
  "user_model": "gpt-4o",
  "user_provider": "openai"
}
```

Customize in `src/green_agent/green_agent.toml`.

## Project Structure

```
the-agent-company/
├── src/                    # Source code
│   ├── green_agent/        # Green agent (assessor) implementation
│   ├── white_agent/        # White agent (target) implementation
│   └── utils/              # Utility functions
├── tests/                  # Test scripts
├── scripts/                # Utility scripts
│   └── utils/              # Helper scripts (e.g., precomputation)
├── docs/                   # Documentation
├── external/               # External dependencies (TAC framework)
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

For detailed documentation, see:
- `docs/IMPLEMENTATION.md` - Full implementation guide
- `docs/TESTING_GUIDE.md` - Testing and evaluation guide
