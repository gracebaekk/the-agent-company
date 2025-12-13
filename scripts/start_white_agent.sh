#!/bin/bash
# Start White Agent for ngrok exposure

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "=========================================="
echo "Starting White Agent"
echo "=========================================="
echo ""
echo "Host: 0.0.0.0"
echo "Port: 9002"
echo ""
echo "The agent will be accessible at:"
echo "  - Locally: http://localhost:9002"
echo "  - After ngrok: https://YOUR_NGROK_URL"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start white agent
python -c "from src.white_agent import start_white_agent; start_white_agent('agent_company_white_agent', '0.0.0.0', 9002)"

