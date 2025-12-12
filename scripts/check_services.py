#!/usr/bin/env python3
"""Check if TAC services are running and accessible."""

import asyncio
import httpx
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

async def check_services(hostname: str = "localhost"):
    """Check if TAC services are accessible."""
    services = {
        "GitLab": f"http://{hostname}:8091",
        "RocketChat": f"http://{hostname}:3000",
        "OwnCloud": f"http://{hostname}:8092",
        "Plane": f"http://{hostname}:8091",  # Note: Plane and GitLab both use 8091, but Plane proxy handles routing
    }
    
    print(f"Checking TAC services at hostname: {hostname}")
    print("=" * 60)
    
    all_ok = True
    for name, url in services.items():
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, follow_redirects=True)
                if response.status_code < 500:
                    print(f"✓ {name:15} ({url:40}) - accessible (HTTP {response.status_code})")
                else:
                    print(f"✗ {name:15} ({url:40}) - returned HTTP {response.status_code}")
                    all_ok = False
        except httpx.ConnectError:
            print(f"✗ {name:15} ({url:40}) - connection refused (service not running?)")
            all_ok = False
        except httpx.TimeoutException:
            print(f"✗ {name:15} ({url:40}) - timeout (service slow or not responding)")
            all_ok = False
        except Exception as e:
            print(f"✗ {name:15} ({url:40}) - error: {type(e).__name__}: {e}")
            all_ok = False
    
    print("=" * 60)
    
    # Check Docker
    print("\nChecking Docker:")
    try:
        result = await asyncio.create_subprocess_exec(
            "docker", "ps",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=5.0)
        if result.returncode == 0:
            print("✓ Docker daemon - accessible")
        else:
            print(f"✗ Docker daemon - error (returncode: {result.returncode})")
            all_ok = False
    except FileNotFoundError:
        print("✗ Docker daemon - Docker not installed or not in PATH")
        all_ok = False
    except Exception as e:
        print(f"✗ Docker daemon - error: {type(e).__name__}: {e}")
        all_ok = False
    
    print("=" * 60)
    
    if all_ok:
        print("\n✓ All services are accessible!")
        return 0
    else:
        print("\n✗ Some services are not accessible.")
        print("\nTo start TAC services:")
        print("  cd external/tac/servers")
        print("  bash setup.sh")
        return 1


if __name__ == "__main__":
    hostname = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    exit_code = asyncio.run(check_services(hostname))
    sys.exit(exit_code)

