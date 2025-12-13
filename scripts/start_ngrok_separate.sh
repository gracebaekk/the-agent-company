#!/bin/bash
# Start two separate ngrok processes in tmux to get different URLs

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "Starting ngrok tunnels (separate URLs)"
echo "=========================================="
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux is not installed."
    echo "Install: brew install tmux"
    exit 1
fi

# Check if agents are running
echo "Checking if agents are running..."
GREEN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9001/ 2>/dev/null || echo "000")
WHITE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9002/ 2>/dev/null || echo "000")

if [ "$GREEN_STATUS" = "000" ]; then
    echo "❌ Green Agent is not responding on port 9001"
    exit 1
fi

if [ "$WHITE_STATUS" = "000" ]; then
    echo "❌ White Agent is not responding on port 9002"
    exit 1
fi

echo "✅ Both agents are running"
echo ""

# Kill existing ngrok sessions if they exist
tmux kill-session -t ngrok_green 2>/dev/null || true
tmux kill-session -t ngrok_white 2>/dev/null || true

# Start ngrok for green agent in tmux
echo "Starting ngrok for Green Agent (port 9001)..."
tmux new-session -d -s ngrok_green "ngrok http 9001 --log stdout"

# Wait a moment
sleep 2

# Start ngrok for white agent in tmux
echo "Starting ngrok for White Agent (port 9002)..."
tmux new-session -d -s ngrok_white "ngrok http 9002 --log stdout"

# Wait for tunnels to establish
echo ""
echo "Waiting for tunnels to establish..."
sleep 5

# Get the URLs
echo ""
echo "=========================================="
echo "✅ ngrok Tunnels Started!"
echo "=========================================="
echo ""

GREEN_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data = json.load(sys.stdin); print([t['public_url'] for t in data['tunnels'] if 'https' in t['public_url']][0])" 2>/dev/null || echo "")
WHITE_URL=$(curl -s http://localhost:4041/api/tunnels | python3 -c "import sys, json; data = json.load(sys.stdin); print([t['public_url'] for t in data['tunnels'] if 'https' in t['public_url']][0])" 2>/dev/null || echo "")

if [ -n "$GREEN_URL" ]; then
    echo "🟢 Green Agent URL:"
    echo "   $GREEN_URL"
else
    echo "❌ Could not get Green Agent URL"
    echo "   View manually: http://localhost:4040"
fi

echo ""

if [ -n "$WHITE_URL" ]; then
    echo "⚪ White Agent URL:"
    echo "   $WHITE_URL"
else
    echo "❌ Could not get White Agent URL"
    echo "   View manually: http://localhost:4041"
fi

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Copy BOTH URLs above"
echo ""
echo "2. Configure Agent Beats:"
echo ""
echo "   agents:"
echo "     - id: green_agent"
echo "       endpoint: \"$GREEN_URL\""
echo "     - id: white_agent"
echo "       endpoint: \"$WHITE_URL\""
echo ""
echo "3. Run assessment:"
echo "   agentbeats run --task TASK_NAME"
echo ""
echo "=========================================="
echo "Monitoring:"
echo "=========================================="
echo ""
echo "View tunnel details:"
echo "  Green: http://localhost:4040"
echo "  White: http://localhost:4041"
echo ""
echo "View tunnel logs:"
echo "  tmux attach -t ngrok_green  # Ctrl+B then D to detach"
echo "  tmux attach -t ngrok_white  # Ctrl+B then D to detach"
echo ""
echo "Stop tunnels:"
echo "  tmux kill-session -t ngrok_green"
echo "  tmux kill-session -t ngrok_white"
echo ""

