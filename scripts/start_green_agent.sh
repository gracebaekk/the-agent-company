#!/bin/bash
# Start Green Agent for ngrok exposure

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "=========================================="
echo "Starting Green Agent"
echo "=========================================="
echo ""
echo "Host: 0.0.0.0"
echo "Port: 9001"
echo ""
echo "The agent will be accessible at:"
echo "  - Locally: http://localhost:9001"
echo "  - After ngrok: https://YOUR_NGROK_URL"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start green agent
python -c "from src.green_agent import start_green_agent; start_green_agent('0.0.0.0', 9001)"

