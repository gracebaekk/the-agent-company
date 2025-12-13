#!/bin/bash
# Start both agents in tmux for easy ngrok exposure

set -e

echo "======================================"
echo "Starting Green and White Agents"
echo "======================================"
echo ""
echo "This will start both agents in the background using tmux."
echo "You can then expose them via ngrok."
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux is not installed. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install tmux
    else
        sudo apt-get install -y tmux
    fi
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Kill existing tmux sessions if they exist
tmux kill-session -t green_agent 2>/dev/null || true
tmux kill-session -t white_agent 2>/dev/null || true

echo "Starting Green Agent on port 9001..."
tmux new-session -d -s green_agent "cd $PROJECT_ROOT && source .venv/bin/activate && python -c 'from src.green_agent import start_green_agent; start_green_agent(\"0.0.0.0\", 9001)'"

echo "Starting White Agent on port 9002..."
tmux new-session -d -s white_agent "cd $PROJECT_ROOT && source .venv/bin/activate && python -c 'from src.white_agent import start_white_agent; start_white_agent(\"agent_company_white_agent\", \"0.0.0.0\", 9002)'"

sleep 3

echo ""
echo "✅ Agents started!"
echo ""
echo "Green Agent: http://localhost:9001"
echo "White Agent: http://localhost:9002"
echo ""
echo "To view agent logs:"
echo "  tmux attach -t green_agent    # Then Ctrl+B, D to detach"
echo "  tmux attach -t white_agent    # Then Ctrl+B, D to detach"
echo ""
echo "======================================"
echo "Next Steps: Expose with Ngrok"
echo "======================================"
echo ""
echo "Open two new terminals and run:"
echo ""
echo "Terminal 1:"
echo "  ngrok http 9001"
echo ""
echo "Terminal 2:"
echo "  ngrok http 9002"
echo ""
echo "Copy the forwarding URLs (https://xxxx.ngrok-free.app)"
echo "and use them when registering with Agent Beats."
echo ""

