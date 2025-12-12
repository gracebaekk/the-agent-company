#!/usr/bin/env python3
"""Check api-server status and logs."""

import subprocess
import sys
import time

def check_api_server():
    """Check if api-server container is running and show logs."""
    print("Checking api-server container status...")
    print("=" * 60)
    
    # Check if container exists
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=api-server", "--format", "{{.Names}}\t{{.Status}}"],
        capture_output=True,
        text=True
    )
    
    if not result.stdout.strip():
        print("❌ api-server container not found")
        print("\nThe container may have failed to start. Check Docker logs.")
        return 1
    
    print(f"Container status:\n{result.stdout}")
    
    # Check if it's running
    if "Up" not in result.stdout:
        print("\n⚠️  Container is not running!")
        print("\nShowing last 50 lines of logs:")
        print("=" * 60)
        subprocess.run(["docker", "logs", "--tail", "50", "api-server"])
        return 1
    
    # Check if port 2999 is accessible
    print("\nChecking if port 2999 is accessible...")
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 2999))
    sock.close()
    
    if result == 0:
        print("✓ Port 2999 is accessible")
        
        # Try HTTP request
        import urllib.request
        try:
            response = urllib.request.urlopen('http://localhost:2999', timeout=5)
            print(f"✓ HTTP response: {response.status}")
            return 0
        except Exception as e:
            print(f"⚠️  HTTP request failed: {e}")
            return 1
    else:
        print("✗ Port 2999 is not accessible")
        print("\nShowing last 50 lines of logs:")
        print("=" * 60)
        subprocess.run(["docker", "logs", "--tail", "50", "api-server"])
        return 1


if __name__ == "__main__":
    exit_code = check_api_server()
    sys.exit(exit_code)




