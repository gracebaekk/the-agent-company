#!/bin/bash
# Fix api-server for macOS (Apple Silicon compatible)

echo "Fixing api-server for macOS..."

# Stop and remove existing container
docker stop api-server 2>/dev/null
docker rm api-server 2>/dev/null

# Start api-server with proper port mapping for macOS
echo "Starting api-server with macOS-compatible settings..."
docker run -d \
    --name api-server \
    --platform linux/amd64 \
    --add-host the-agent-company.com:host-gateway \
    -p 2999:2999 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e SKIP_SETUP=True \
    ghcr.io/theagentcompany/servers-api-server:1.0.0

echo "Waiting for api-server to start..."
sleep 10

# Check if it's running
if docker ps | grep -q api-server; then
    echo "✓ api-server container is running"
    echo "Checking port 2999..."
    
    # Wait up to 2 minutes for the service to be ready
    for i in {1..24}; do
        if curl -s http://localhost:2999 > /dev/null 2>&1; then
            echo "✓ api-server is responding on port 2999!"
            exit 0
        fi
        echo "  Attempt $i/24: Waiting for api-server..."
        sleep 5
    done
    
    echo "⚠️  api-server container is running but not responding yet"
    echo "View logs with: docker logs api-server"
    echo "Check status with: python scripts/check_api_server.py"
    exit 1
else
    echo "✗ api-server container failed to start"
    echo "View logs with: docker logs api-server"
    exit 1
fi




