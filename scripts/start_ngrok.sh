#!/bin/bash
# Start ngrok tunnels for both agents using ngrok.yml config

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Starting ngrok tunnels"
echo "=========================================="
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Install: brew install ngrok/ngrok/ngrok"
    else
        echo "Install: https://ngrok.com/download"
    fi
    exit 1
fi

# Check if ngrok.yml exists
if [ ! -f "ngrok.yml" ]; then
    echo "❌ ngrok.yml not found"
    echo "Please create ngrok.yml with your tunnels config"
    exit 1
fi

# Check if agents are running
echo "Checking if agents are running..."
GREEN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9001 2>/dev/null || echo "000")
WHITE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9002 2>/dev/null || echo "000")

if [ "$GREEN_STATUS" = "000" ] || [ "$WHITE_STATUS" = "000" ]; then
    echo "⚠️  Warning: Agents may not be running"
    echo ""
    echo "Green Agent (9001): $GREEN_STATUS"
    echo "White Agent (9002): $WHITE_STATUS"
    echo ""
    echo "Start agents first with:"
    echo "  bash scripts/start_agents.sh tmux"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Starting both ngrok tunnels using ngrok.yml..."
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start ngrok with config file (starts all defined tunnels)
ngrok start --all --config ngrok.yml

