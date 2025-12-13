#!/bin/bash
# Start both agents in tmux sessions for ngrok exposure

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "Starting Green & White Agents in tmux"
echo "=========================================="
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux is not installed."
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing via Homebrew..."
        brew install tmux
    else
        echo "Please install tmux:"
        echo "  Ubuntu/Debian: sudo apt-get install tmux"
        echo "  CentOS/RHEL: sudo yum install tmux"
        exit 1
    fi
fi

# Kill existing sessions if they exist
echo "Stopping any existing agent sessions..."
tmux kill-session -t green_agent 2>/dev/null || true
tmux kill-session -t white_agent 2>/dev/null || true

# Start green agent in tmux
echo "Starting Green Agent on port 9001..."
tmux new-session -d -s green_agent "cd $PROJECT_ROOT && bash scripts/start_green_agent.sh"

# Start white agent in tmux
echo "Starting White Agent on port 9002..."
tmux new-session -d -s white_agent "cd $PROJECT_ROOT && bash scripts/start_white_agent.sh"

# Wait a moment for agents to start
sleep 3

echo ""
echo "✅ Both agents started in tmux!"
echo ""
echo "Agent URLs (for local testing):"
echo "  Green Agent: http://localhost:9001"
echo "  White Agent: http://localhost:9002"
echo ""
echo "To view agent logs:"
echo "  tmux attach -t green_agent    # Press Ctrl+B then D to detach"
echo "  tmux attach -t white_agent    # Press Ctrl+B then D to detach"
echo ""
echo "To stop agents:"
echo "  tmux kill-session -t green_agent"
echo "  tmux kill-session -t white_agent"
echo ""
echo "=========================================="
echo "Next: Expose with ngrok"
echo "=========================================="
echo ""
echo "Open TWO new terminal windows and run:"
echo ""
echo "Terminal 1:"
echo "  ngrok http 9001"
echo ""
echo "Terminal 2:"
echo "  ngrok http 9002"
echo ""
echo "Copy the HTTPS forwarding URLs and use them in Agent Beats!"
echo ""

