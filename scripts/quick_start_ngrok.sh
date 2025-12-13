#!/bin/bash
# Quick start script for ngrok setup

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "🚀 TAC Agent + ngrok Quick Start"
echo "=========================================="
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed."
    echo ""
    echo "Install ngrok:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  brew install ngrok/ngrok/ngrok"
    else
        echo "  Visit: https://ngrok.com/download"
    fi
    echo ""
    echo "Then configure your authtoken:"
    echo "  ngrok config add-authtoken YOUR_AUTH_TOKEN"
    echo ""
    exit 1
fi

# Check if services are running
echo "Step 1: Checking TAC services..."
echo ""
python "$PROJECT_ROOT/scripts/check_services.py"
echo ""

read -p "Are all services accessible? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Please start services first:"
    echo "  cd external/tac && make start-all"
    echo ""
    exit 1
fi

# Start agents in tmux
echo ""
echo "Step 2: Starting agents in tmux..."
echo ""
bash "$SCRIPT_DIR/start_all_agents.sh"

# Wait for agents to be ready
echo "Waiting for agents to be ready..."
sleep 5

# Test agents
echo ""
echo "Step 3: Testing agent endpoints..."
echo ""

GREEN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9001/health || echo "000")
WHITE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9002/health || echo "000")

if [ "$GREEN_STATUS" = "200" ]; then
    echo "✅ Green Agent is running on http://localhost:9001"
else
    echo "❌ Green Agent failed to start (status: $GREEN_STATUS)"
    exit 1
fi

if [ "$WHITE_STATUS" = "200" ]; then
    echo "✅ White Agent is running on http://localhost:9002"
else
    echo "❌ White Agent failed to start (status: $WHITE_STATUS)"
    exit 1
fi

# Instructions for ngrok
echo ""
echo "=========================================="
echo "✅ Agents are running!"
echo "=========================================="
echo ""
echo "Step 4: Open ONE new terminal and run:"
echo ""
echo "  bash scripts/start_ngrok.sh"
echo ""
echo "This will start BOTH tunnels at once!"
echo ""
echo "=========================================="
echo "Step 5: Copy BOTH ngrok HTTPS URLs"
echo "=========================================="
echo ""
echo "From the ngrok output, copy BOTH HTTPS forwarding URLs:"
echo "  Green Agent (port 9001): https://abc123.ngrok-free.app"
echo "  White Agent (port 9002): https://def456.ngrok-free.app"
echo ""
echo "Then configure Agent Beats:"
echo ""
echo "  agents:"
echo "    - id: green_agent"
echo "      endpoint: \"https://YOUR_GREEN_URL.ngrok-free.app\""
echo "    - id: white_agent"
echo "      endpoint: \"https://YOUR_WHITE_URL.ngrok-free.app\""
echo ""
echo "=========================================="
echo "Step 6: Run Agent Beats assessment"
echo "=========================================="
echo ""
echo "  agentbeats run --task TASK_NAME"
echo ""
echo "📊 Monitor agents:"
echo "  tmux attach -t green_agent  # Press Ctrl+B then D to detach"
echo "  tmux attach -t white_agent  # Press Ctrl+B then D to detach"
echo ""
echo "🔍 View ngrok traffic:"
echo "  http://127.0.0.1:4040  # All tunnels in one interface!"
echo ""
echo "🛑 To stop everything:"
echo "  [Ctrl+C in ngrok terminal]"
echo "  tmux kill-session -t green_agent"
echo "  tmux kill-session -t white_agent"
echo ""
echo "📖 Full guide: docs/AGENTBEATS_NGROK_GUIDE.md"
echo ""

