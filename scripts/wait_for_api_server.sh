#!/bin/bash
# Wait for api-server Flask app to actually start responding

echo "Waiting for api-server Flask app to start..."
echo "This can take 10-20 minutes while it starts all services (GitLab, RocketChat, OwnCloud, Plane)"
echo ""

MAX_ATTEMPTS=240  # 20 minutes (240 * 5 seconds)
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    # Try to get a response from Flask
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:2999/api/healthcheck/redis 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" != "000" ] && [ "$HTTP_CODE" != "" ]; then
        echo ""
        echo "✓ Flask is responding! HTTP code: $HTTP_CODE"
        echo "✓ api-server is ready"
        exit 0
    fi
    
    if [ $((ATTEMPT % 12)) -eq 0 ]; then
        ELAPSED=$((ATTEMPT * 5))
        echo "  Still waiting... ($(($ELAPSED / 60)) minutes elapsed)"
    fi
    
    sleep 5
done

echo ""
echo "⚠️  Flask did not start after 20 minutes"
echo "Check logs: docker logs api-server"
exit 1




