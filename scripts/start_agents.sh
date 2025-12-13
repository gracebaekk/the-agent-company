#!/bin/bash
# Unified script to start agents for local testing or ngrok

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Parse command line arguments
MODE=${1:-tmux}  # Options: tmux, foreground

echo "=========================================="
echo "Starting TAC Agents"
echo "=========================================="
echo ""

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found at .venv"
    echo "Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Load API key from .env if it exists
if [ -f ".env" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "Loading environment from .env..."
    export $(cat .env | grep -v '^#' | grep OPENAI_API_KEY | xargs)
fi

# Verify API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set"
    echo "Set it with: export OPENAI_API_KEY='your-key-here'"
    echo ""
fi

if [ "$MODE" = "tmux" ]; then
    # Check if tmux is installed
    if ! command -v tmux &> /dev/null; then
        echo "❌ tmux is not installed."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "Install with: brew install tmux"
        else
            echo "Install with: sudo apt-get install tmux"
        fi
        exit 1
    fi

    # Kill existing sessions
    echo "Stopping any existing agent sessions..."
    tmux kill-session -t green_agent 2>/dev/null || true
    tmux kill-session -t white_agent 2>/dev/null || true
    
    # Start agents in tmux
    echo "Starting Green Agent on port 9001..."
    tmux new-session -d -s green_agent \
        "cd $PROJECT_ROOT && source .venv/bin/activate && python -c 'from src.green_agent import start_green_agent; start_green_agent(\"0.0.0.0\", 9001)'"
    
    echo "Starting White Agent on port 9002..."
    tmux new-session -d -s white_agent \
        "cd $PROJECT_ROOT && source .venv/bin/activate && python -c 'from src.white_agent import start_white_agent; start_white_agent(\"agent_company_white_agent\", \"0.0.0.0\", 9002)'"
    
    sleep 3
    
    echo ""
    echo "✅ Agents started in tmux!"
    echo ""
    echo "Agent URLs:"
    echo "  Green: http://localhost:9001"
    echo "  White: http://localhost:9002"
    echo ""
    echo "View logs:"
    echo "  tmux attach -t green_agent    # Ctrl+B then D to detach"
    echo "  tmux attach -t white_agent"
    echo ""
    echo "Stop agents:"
    echo "  tmux kill-session -t green_agent"
    echo "  tmux kill-session -t white_agent"
    echo ""
    echo "=========================================="
    echo "Next: Expose with ngrok"
    echo "=========================================="
    echo ""
    echo "Run: bash scripts/start_ngrok.sh"
    echo ""
    
elif [ "$MODE" = "foreground" ]; then
    echo "Starting agents in foreground mode (for debugging)..."
    echo ""
    echo "Green Agent: http://localhost:9001"
    echo "White Agent: http://localhost:9002"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Start green agent in background
    source .venv/bin/activate
    python -c "from src.green_agent import start_green_agent; start_green_agent('0.0.0.0', 9001)" &
    GREEN_PID=$!
    
    # Start white agent in background
    python -c "from src.white_agent import start_white_agent; start_white_agent('agent_company_white_agent', '0.0.0.0', 9002)" &
    WHITE_PID=$!
    
    # Cleanup on exit
    trap "kill $GREEN_PID $WHITE_PID 2>/dev/null" EXIT
    
    # Wait
    wait
else
    echo "❌ Invalid mode: $MODE"
    echo "Usage: $0 [tmux|foreground]"
    exit 1
fi

