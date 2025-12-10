"""Docker container management for TAC evaluation."""

import os
import subprocess
import asyncio
import json
import tempfile
import platform
from typing import Optional, Dict, Any
from pathlib import Path


class DockerManager:
    """Manages Docker containers for TAC task evaluation."""
    
    def __init__(self, use_host_network: bool = True):
        """
        Initialize Docker manager.
        
        Args:
            use_host_network: Whether to use host networking (required for localhost services)
        """
        self.use_host_network = use_host_network
        # Check if we need platform emulation (Apple Silicon)
        self.needs_platform_flag = (platform.machine() == "arm64" or platform.processor() == "arm")
        # On Mac, host networking doesn't work the same way
        self.is_mac = platform.system() == "Darwin"
    
    async def pull_image(self, image_name: str) -> bool:
        """
        Pull Docker image if not already present.
        
        Args:
            image_name: Docker image name (e.g., "ghcr.io/theagentcompany/pm-schedule-meeting-1-image:1.0.0")
        
        Returns:
            True if image is available, False otherwise
        """
        try:
            print(f"Checking for Docker image: {image_name}")
            
            # Check if image exists locally (with short timeout)
            result = await self._run_command(["docker", "images", "-q", image_name], timeout=5.0)
            if result["stdout"].strip():
                print(f"✓ Image {image_name} already exists locally")
                return True
            
            # Pull image (with longer timeout for network operations)
            print(f"Pulling Docker image: {image_name}...")
            result = await self._run_command(["docker", "pull", image_name], timeout=120.0)
            
            if result["returncode"] == 0:
                print(f"✓ Successfully pulled {image_name}")
                return True
            else:
                print(f"✗ Failed to pull {image_name}: {result['stderr']}")
                return False
        except Exception as e:
            print(f"✗ Docker error (Docker may not be installed): {e}")
            return False
    
    async def get_task_instruction(self, image_name: str) -> str:
        """
        Extract task instruction from Docker image.
        
        Args:
            image_name: Docker image name
        
        Returns:
            Task instruction content from /instruction/task.md
        """
        print(f"Extracting task instruction from {image_name}...")
        
        # Create a temporary container to read the file
        container_name = f"tac_instruction_{os.getpid()}"
        
        try:
            # Build docker run command
            cmd = ["docker", "run", "--name", container_name, "--rm"]
            
            # Add platform flag for Apple Silicon compatibility
            if self.needs_platform_flag:
                cmd.extend(["--platform", "linux/amd64"])
            
            cmd.extend([
                image_name,
                "cat", "/instruction/task.md"
            ])
            
            result = await self._run_command(cmd, timeout=30)
            
            if result["returncode"] == 0:
                instruction = result["stdout"]
                print(f"✓ Retrieved task instruction ({len(instruction)} chars)")
                return instruction
            else:
                print(f"✗ Failed to get task instruction: {result['stderr']}")
                return f"Complete the task in /instruction/task.md"
        
        except Exception as e:
            print(f"✗ Error getting task instruction: {e}")
            return f"Complete the task in /instruction/task.md"
    
    async def initialize_task(
        self,
        image_name: str,
        container_name: str,
        server_hostname: str,
        env_llm_config: Dict[str, str],
    ) -> bool:
        """
        Initialize task environment by running /utils/init.sh in container.
        
        Args:
            image_name: Docker image name
            container_name: Name for the container
            server_hostname: Hostname where TAC services are running
            env_llm_config: Environment LLM configuration
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        print(f"Initializing task environment in container {container_name}...")
        
        # Build environment variables
        env_vars = {
            "SERVER_HOSTNAME": server_hostname,
            "LITELLM_API_KEY": env_llm_config.get("api_key", ""),
            "LITELLM_BASE_URL": env_llm_config.get("base_url", ""),
            "LITELLM_MODEL": env_llm_config.get("model", "openai/gpt-4o"),
        }
        
        # Build docker run command
        cmd = ["docker", "run"]
        
        # Add platform flag for Apple Silicon compatibility
        if self.needs_platform_flag:
            cmd.extend(["--platform", "linux/amd64"])
        
        # Note: On Mac, --network host doesn't work the same way as Linux
        if self.use_host_network and not self.is_mac:
            cmd.extend(["--network", "host"])
        elif self.is_mac:
            # On Mac, add hostname mapping for accessing host services
            cmd.extend(["--add-host", "the-agent-company.com:host-gateway"])
        
        # Add environment variables
        for key, value in env_vars.items():
            if value:
                cmd.extend(["-e", f"{key}={value}"])
        
        cmd.extend([
            "--name", container_name,
            image_name,
            "bash", "/utils/init.sh"
        ])
        
        # Run initialization (this can take up to 10 minutes)
        print("Running /utils/init.sh (this may take several minutes)...")
        result = await self._run_command(cmd, timeout=900)  # 15 minute timeout
        
        if result["returncode"] == 0:
            print(f"✓ Task environment initialized successfully")
            return True
        else:
            print(f"✗ Task initialization failed: {result['stderr']}")
            return False
    
    async def run_evaluation(
        self,
        image_name: str,
        container_name: str,
        trajectory_path: str,
        output_path: str,
        server_hostname: str,
        env_llm_config: Dict[str, str],
        decryption_key: str = "theagentcompany is all you need",
    ) -> Optional[Dict[str, Any]]:
        """
        Run TAC evaluation in Docker container.
        
        This runs both initialization (/utils/init.sh) and evaluation (/utils/eval.py)
        in sequence within the same container execution.
        
        Args:
            image_name: Docker image name
            container_name: Name for the container
            trajectory_path: Path to trajectory JSON file (must be absolute)
            output_path: Path to save evaluation results (must be absolute)
            server_hostname: Hostname where TAC services are running
            env_llm_config: Environment LLM configuration
            decryption_key: Decryption key for evaluator code
        
        Returns:
            Evaluation results dictionary, or None if evaluation failed
        """
        print(f"Running evaluation in container {container_name}...")
        
        # Ensure paths are absolute
        trajectory_path = os.path.abspath(trajectory_path)
        output_path = os.path.abspath(output_path)
        
        # Build environment variables
        env_vars = {
            "SERVER_HOSTNAME": server_hostname,
            "LITELLM_API_KEY": env_llm_config.get("api_key", ""),
            "LITELLM_BASE_URL": env_llm_config.get("base_url", ""),
            "LITELLM_MODEL": env_llm_config.get("model", "openai/gpt-4o"),
            "DECRYPTION_KEY": decryption_key,
        }
        
        # Build docker run command
        cmd = ["docker", "run"]
        
        # Add platform flag for Apple Silicon compatibility
        if self.needs_platform_flag:
            cmd.extend(["--platform", "linux/amd64"])
        
        # Note: On Mac, --network host doesn't work the same way as Linux
        # The init.sh script should handle hostname resolution
        if self.use_host_network and not self.is_mac:
            cmd.extend(["--network", "host"])
        elif self.is_mac:
            # On Mac, add host.docker.internal for accessing host services
            cmd.extend(["--add-host", "the-agent-company.com:host-gateway"])
        
        # Mount /tmp/workspace as /workspace so agent output can be seen by evaluation
        cmd.extend(["-v", "/tmp/workspace:/workspace:rw"])
        
        # Mount trajectory and output directories
        # If they're in the same directory, only mount once
        trajectory_dir = os.path.dirname(trajectory_path)
        output_dir = os.path.dirname(output_path)
        
        if trajectory_dir == output_dir:
            # Same directory - mount once as read-write
            cmd.extend([
                "-v", f"{trajectory_dir}:{trajectory_dir}:rw",
            ])
        else:
            # Different directories - mount both
            cmd.extend([
                "-v", f"{trajectory_dir}:{trajectory_dir}:ro",  # Read-only mount for trajectory
                "-v", f"{output_dir}:{output_dir}:rw",  # Read-write mount for output
            ])
        
        # Add environment variables
        for key, value in env_vars.items():
            if value:
                cmd.extend(["-e", f"{key}={value}"])
        
        # Run init.sh and then eval.py in sequence
        # Using bash -c to chain commands with timing
        # Note: For external agents (running on host), we SKIP the reset.sh
        # because the agent has already modified the services and we don't want to undo that
        # We create a custom init that only sets up hostnames without resetting
        init_and_eval = (
            f"echo '=== Setting up hostname resolution ===' && "
            f"SERVICE_IP=$(getent hosts ${{SERVER_HOSTNAME:-localhost}} | awk '{{print $1}}' || echo 'host-gateway') && "
            f"echo \"$SERVICE_IP the-agent-company.com\" >> /etc/hosts && "
            f"echo 'Hostname resolution configured' && "
            f"echo '=== Skipping reset.sh (external agent mode) ===' && "
            f"echo '=== Starting eval.py ===' && "
            f"time python_default /utils/eval.py "
            f"--trajectory_path {trajectory_path} "
            f"--result_path {output_path} && "
            f"echo '=== Evaluation completed ==='"
        )
        
        cmd.extend([
            "--rm",
            "--name", container_name,
            image_name,
            "bash", "-c", init_and_eval,
        ])
        
        # Run evaluation (init + eval can take up to 15 minutes)
        print(f"Running initialization and evaluation...")
        print(f"  This includes:")
        print(f"    1. /utils/init.sh - Resets services (can take 5-10 minutes)")
        print(f"    2. /utils/eval.py - Runs evaluation (usually 1-2 minutes)")
        import time as time_module
        start_time = time_module.time()
        result = await self._run_command(cmd, timeout=900)  # 15 minute timeout
        elapsed = time_module.time() - start_time
        print(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        
        if result["returncode"] != 0:
            print(f"✗ Evaluation failed: {result['stderr']}")
            print(f"stdout (last 500 chars): {result['stdout'][-500:]}")
            # Check if it failed during init or eval
            if "=== Starting /utils/init.sh ===" in result['stdout']:
                if "=== init.sh completed" not in result['stdout']:
                    print("  ⚠️  Failed during /utils/init.sh (service initialization)")
                else:
                    print("  ⚠️  Failed during /utils/eval.py (evaluation)")
            return None
        
        # Read and parse output JSON
        try:
            if os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    evaluation_result = json.load(f)
                print(f"✓ Evaluation completed successfully")
                return evaluation_result
            else:
                print(f"✗ Evaluation output file not found: {output_path}")
                return None
        except Exception as e:
            print(f"✗ Failed to read evaluation results: {e}")
            return None
    
    async def cleanup_container(self, container_name: str) -> bool:
        """
        Remove a Docker container.
        
        Args:
            container_name: Name of container to remove
        
        Returns:
            True if cleanup succeeded, False otherwise
        """
        try:
            result = await self._run_command(["docker", "rm", "-f", container_name])
            return result["returncode"] == 0
        except Exception as e:
            print(f"Warning: Failed to cleanup container {container_name}: {e}")
            return False
    
    async def _run_command(
        self,
        cmd: list,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run a shell command asynchronously.
        
        Args:
            cmd: Command and arguments as list
            timeout: Timeout in seconds
        
        Returns:
            Dictionary with 'returncode', 'stdout', 'stderr'
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
            }
        except asyncio.TimeoutError:
            print(f"Command timed out after {timeout} seconds")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
            }

