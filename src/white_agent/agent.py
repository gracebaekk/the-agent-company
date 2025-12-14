"""White agent implementation - the target agent being tested."""

import os
import json
import subprocess
import asyncio
from typing import List, Dict, Any
from pathlib import Path
import uvicorn
from dotenv import load_dotenv
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill, AgentCard, AgentCapabilities
from a2a.utils import new_agent_text_message
from litellm import completion

load_dotenv()


def load_config_files() -> Dict[str, Any]:
    """Load configuration files (credentials, API reference, domain rules)."""
    data_dir = Path(__file__).parent.parent / "data"
    config = {}
    
    try:
        with open(data_dir / "service_credentials.json") as f:
            config["credentials"] = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load service_credentials.json: {e}")
        config["credentials"] = {}
    
    try:
        with open(data_dir / "api_reference.json") as f:
            config["api_reference"] = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load api_reference.json: {e}")
        config["api_reference"] = {}
    
    try:
        with open(data_dir / "domain_rules.json") as f:
            config["domain_rules"] = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load domain_rules.json: {e}")
        config["domain_rules"] = {}
    
    return config


def format_config_for_system_message(config: Dict[str, Any]) -> str:
    """Format configuration data into a concise system message section."""
    creds = config.get("credentials", {})
    api_ref = config.get("api_reference", {})
    rules = config.get("domain_rules", {})
    
    sections = []
    
    # Service credentials
    if creds:
        sections.append("SERVICE CREDENTIALS:")
        if "owncloud" in creds:
            oc = creds["owncloud"]
            sections.append(f"- ownCloud ({oc['url']}): Username: {oc['username']}, Password: {oc['password']}")
        if "gitlab" in creds:
            gl = creds["gitlab"]
            sections.append(f"- GitLab ({gl['url']}): Username: {gl['username']}, API Token: {gl['api_token']}")
        if "rocketchat" in creds:
            rc = creds["rocketchat"]
            sections.append(f"- RocketChat ({rc['url']}): Username: {rc['username']}, Password: {rc['password']}")
        if "plane" in creds:
            pl = creds["plane"]
            sections.append(f"- Plane ({pl['url']}): API Key: {pl['api_key']}, Workspace: {pl['workspace']}")
        sections.append("")
    
    # Critical API notes
    if "rocketchat" in api_ref:
        rc_ref = api_ref["rocketchat"]
        sections.append("ROCKETCHAT CRITICAL:")
        if "critical_notes" in rc_ref:
            for note in rc_ref["critical_notes"]:
                sections.append(f"- {note}")
        sections.append("")
    
    # Error handling
    if "rocketchat" in api_ref and "error_handling" in api_ref["rocketchat"]:
        sections.append("ERROR HANDLING:")
        for key, value in api_ref["rocketchat"]["error_handling"].items():
            sections.append(f"- {key.replace('_', ' ').title()}: {value}")
        sections.append("")
    
    # Domain rules summary
    if rules:
        if "time_handling" in rules:
            sections.append("TIME HANDLING: " + rules["time_handling"]["description"])
        if "csv_handling" in rules:
            sections.append("CSV HANDLING: " + rules["csv_handling"]["description"])
        if "reimbursement_calculations" in rules:
            reimb = rules["reimbursement_calculations"]
            sections.append("REIMBURSEMENT: " + "; ".join(reimb["rules"][:2]))
        sections.append("")
    
    # Reference to full documentation
    sections.append("For detailed API examples and commands, refer to the JSON files in /workspace if available, or use the patterns above.")
    
    return "\n".join(sections)


# Tool definitions for function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a bash command in the shell. Returns the output and exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    }
]


def execute_bash(command: str) -> Dict[str, Any]:
    """Execute a bash command and return the result. Can run in container or on host."""
    try:
        # Check if we should run this in a Docker container
        # Commands that reference container-specific paths should run in container
        run_in_container = any(path in command for path in ['/instruction/', '/workspace/', '/output/', '/utils/', '/npc/'])
        
        if run_in_container:
            # Find the active task evaluation container
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=tac_eval", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_name = result.stdout.strip().split('\n')[0]
                # Run command in container
                docker_result = subprocess.run(
                    ["docker", "exec", container_name, "bash", "-c", command],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                return {
                    "success": True,
                    "stdout": docker_result.stdout,
                    "stderr": docker_result.stderr,
                    "exit_code": docker_result.returncode,
                    "container": container_name
                }
        
        # Run on host
        # Replace the-agent-company.com with localhost for local execution
        command = command.replace("the-agent-company.com", "localhost")
        command = command.replace("http://localhost", "http://localhost")  # Ensure http not https
        
        # Replace /workspace with /tmp/workspace for Mac compatibility (local dev only)
        # On AgentBeats/Linux, /workspace exists natively so skip this substitution
        import platform
        if platform.system() == "Darwin":  # macOS
            command = command.replace("/workspace", "/tmp/workspace")
        
        # Fix escaped quotes that come from LLM - the shell expects unescaped quotes
        # inside the command string. The LLM sometimes sends \' which should be '
        command = command.replace("\\'", "'")
        command = command.replace('\\"', '"')
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120  # Increased timeout for slow GitLab operations
        )
        
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 120 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def read_file(file_path: str) -> Dict[str, Any]:
    """Read a file and return its contents. Supports both host and Docker container files."""
    try:
        # First, try to read from host filesystem
        import platform
        host_file_path = file_path
        if platform.system() == "Darwin":
            host_file_path = file_path.replace("/workspace", "/tmp/workspace")
        
        try:
            with open(host_file_path, 'r') as f:
                content = f.read()
            return {
                "success": True,
                "content": content
            }
        except FileNotFoundError:
            # If file not on host, try to read from Docker container
            # Look for paths that are typically in containers
            if file_path.startswith(('/instruction/', '/workspace/', '/output/', '/utils/', '/npc/')):
                try:
                    # Find the active task evaluation container (exclude NPC containers)
                    result = subprocess.run(
                        ["docker", "ps", "--filter", "name=tac_eval", "--format", "{{.Names}}"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        # Filter out NPC containers - get the most recent non-NPC container
                        containers = [c for c in result.stdout.strip().split('\n') if 'tac_npc' not in c]
                        if containers:
                            container_name = containers[0]
                            # Read file from container
                            docker_result = subprocess.run(
                                ["docker", "exec", container_name, "cat", file_path],
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            
                            if docker_result.returncode == 0:
                                return {
                                    "success": True,
                                    "content": docker_result.stdout,
                                    "source": f"container:{container_name}"
                                }
                except Exception:
                    # Docker bridge failed, continue to raise FileNotFoundError below
                    pass
            
            # If we get here, file doesn't exist on host or in container
            raise FileNotFoundError(f"File not found: {file_path}")
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to a file. Supports both host and Docker container files."""
    # Check if path looks like it's in a container
    # For admin tasks, /workspace/ should go to container, not host
    if file_path.startswith(('/instruction/', '/utils/', '/output/', '/workspace/')):
        try:
            # Find the active task evaluation container (exclude NPC containers)
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=tac_eval", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Filter out NPC containers - get the most recent non-NPC container
                containers = [c for c in result.stdout.strip().split('\n') if 'tac_npc' not in c]
                if containers:
                    container_name = containers[0]
                    # Write file to container - create temp file and copy
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                        tmp.write(content)
                        tmp_path = tmp.name
                    
                    try:
                        # Copy file into container
                        docker_result = subprocess.run(
                            ["docker", "cp", tmp_path, f"{container_name}:{file_path}"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if docker_result.returncode == 0:
                            return {
                                "success": True,
                                "message": f"Successfully wrote to {file_path} in container {container_name}"
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Failed to write to container: {docker_result.stderr}"
                            }
                    finally:
                        os.unlink(tmp_path)
        except Exception as e:
            # Docker bridge failed, fall through to host write
            pass
    
    # Write to host filesystem
    try:
        import platform
        host_file_path = file_path
        if platform.system() == "Darwin":
            host_file_path = file_path.replace("/workspace", "/tmp/workspace")
            # ALSO replace /workspace in the content itself (for Python scripts, etc.)
            content = content.replace("/workspace", "/tmp/workspace")
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(host_file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(host_file_path, 'w') as f:
            f.write(content)
        return {
            "success": True,
            "message": f"Successfully wrote to {host_file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool based on its name."""
    if tool_name == "execute_bash":
        return execute_bash(tool_args["command"])
    elif tool_name == "read_file":
        return read_file(tool_args["file_path"])
    elif tool_name == "write_file":
        return write_file(tool_args["file_path"], tool_args["content"])
    else:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}


def prepare_white_agent_card(url):
    """Prepare the agent card for the white agent."""
    skill = AgentSkill(
        id="task_fulfillment",
        name="Task Fulfillment",
        description="Handles user requests and completes tasks using TheAgentCompany framework",
        tags=["general", "the-agent-company"],
        examples=[],
    )
    
    card = AgentCard(
        name="agent_company_white_agent",
        description="White agent for TheAgentCompany evaluation",
        url=url,
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(message=True, task=False, streaming=False),
        skills=[skill],
    )
    
    return card


class GeneralWhiteAgentExecutor(AgentExecutor):
    """Executor for the white agent that handles user requests with tool execution."""
    
    def __init__(self, max_iterations: int = 30):
        self.ctx_id_to_messages = {}
        self.max_iterations = max_iterations
        self.config = load_config_files()
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent's task fulfillment logic with tool calling."""
        # Parse the task
        user_input = context.get_user_input()
        
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = []
        
        messages = self.ctx_id_to_messages[context.context_id]
        
        # Add system message on first interaction
        if len(messages) == 0:
            config_text = format_config_for_system_message(self.config)
            system_message = {
                "role": "system",
                "content": (
                    "You are an AI agent that MUST complete tasks by executing real actions. "
                    "You are running inside a Linux environment with full access to bash, files, and network.\n\n"
                    "CRITICAL INSTRUCTIONS:\n"
                    "1. You MUST use the tools provided to complete ALL steps of the task\n"
                    "2. Do NOT just explain what to do - actually EXECUTE the commands\n"
                    "3. Keep executing tools until the ENTIRE task is complete\n"
                    "4. If a step fails, check the error message:\n"
                    "   - If it says 'already exists' or 'already has role' → SUCCESS, continue\n"
                    "   - If it says 'not found' → Create/initialize the resource first\n"
                    "   - If it's a real error → Try an alternative approach\n"
                    "5. ALWAYS authenticate when accessing services\n"
                    "6. ALWAYS check API responses and extract IDs before using them in next steps\n"
                    "7. If task instructions say to visit URLs (like /home), you MUST execute curl to that URL\n\n"
                    "Available tools:\n"
                    "- execute_bash: Run ANY bash command (curl, git, python, pip install, etc.)\n"
                    "- read_file: Read file contents\n"
                    "- write_file: Write content to files\n\n"
                    f"{config_text}\n"
                    "For detailed API examples, commands, and domain-specific rules, you can read the JSON files:\n"
                    "- /workspace/service_credentials.json (if available in task container)\n"
                    "- /workspace/api_reference.json (if available in task container)\n"
                    "- /workspace/domain_rules.json (if available in task container)\n"
                    "Or use read_file tool to access: src/data/service_credentials.json, src/data/api_reference.json, src/data/domain_rules.json\n\n"
                    "REMEMBER: Execute ALL steps of the task. Do not stop until everything is done!"
                )
            }
            messages.append(system_message)
        
        messages.append({
            "role": "user",
            "content": user_input,
        })
        
        # Get model and provider from environment variables, with defaults
        model = os.getenv("AGENT_MODEL", "gpt-4o")
        provider = os.getenv("AGENT_PROVIDER", "openai")
        
        # Get API key - try multiple environment variable names
        api_key = (
            os.getenv("OPENAI_API_KEY") or 
            os.getenv("AGENT_API_KEY") or 
            os.getenv("LITELLM_API_KEY")
        )
        
        if not api_key:
            error_msg = (
                "Error: No API key found. Please set one of:\n"
                "  - OPENAI_API_KEY\n"
                "  - AGENT_API_KEY\n"
                "  - LITELLM_API_KEY\n"
                "in your .env file or environment variables."
            )
            await event_queue.enqueue_event(
                new_agent_text_message(error_msg, context_id=context.context_id)
            )
            return
        
        # Collect all output to send at the end
        execution_log = []
        
        # Track recent commands to detect loops
        recent_commands = []
        
        # Agent loop with tool calling
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            try:
                # Call LLM with tool support
                response = completion(
                    messages=messages,
                    model=model,
                    custom_llm_provider=provider,
                    temperature=0.0,
                    api_key=api_key,
                    tools=TOOLS,
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                
                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": response_message.tool_calls if hasattr(response_message, 'tool_calls') else None
                })
                
                # Check if the model wants to use tools
                if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                    # Execute all tool calls
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        # Execute the tool first
                        tool_result = execute_tool(tool_name, tool_args)
                        
                        # Create a signature that includes the result status for loop detection
                        command_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}:failed={not tool_result.get('success', False)}"
                        recent_commands.append(command_signature)
                        
                        # Keep only last 10 commands to save memory
                        if len(recent_commands) > 10:
                            recent_commands = recent_commands[-10:]
                        
                        # Check if the same FAILING command has been repeated 3+ times in last 5 commands
                        # Only trigger loop detection for failures, not successful commands
                        if not tool_result.get('success', False):
                            last_5 = recent_commands[-5:] if len(recent_commands) >= 5 else recent_commands
                            if last_5.count(command_signature) >= 3:
                                # Stuck in a loop of failures! Add hint to messages
                                loop_warning = (
                                    f"LOOP DETECTED: The same command has FAILED 3+ times with the same error. "
                                    f"The command '{tool_name}' keeps failing. Try a DIFFERENT approach:\n"
                                    f"- For RocketChat API: Make sure ALL POST requests include -H 'Content-Type: application/json'\n"
                                    f"- Check the API documentation or error message for correct syntax\n"
                                    f"- Try a simpler test command first to verify connectivity\n"
                                    f"- Last error: {tool_result.get('error', 'Unknown')[:200]}"
                                )
                                execution_log.append(f"⚠️ {loop_warning}")
                                # Add the loop warning as a tool result so the model knows
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_name,
                                    "content": json.dumps({"success": False, "error": loop_warning})
                                })
                                continue  # Skip the normal result processing, let LLM try something else
                        
                        # Log progress (collect instead of sending immediately)
                        # Include full tool argument values (do not truncate) so evaluators can
                        # match required substrings like 'dir=/Documents/Financials'.
                        arg_strs = []
                        for k, v in tool_args.items():
                            try:
                                # Prefer preserving the original string for readability
                                arg_val = v if not isinstance(v, str) else v
                            except Exception:
                                arg_val = str(v)
                            arg_strs.append(f"{k}={arg_val}")
                        progress_msg = f"🔧 Executing: {tool_name}({', '.join(arg_strs)})\n"
                        if tool_result.get("success"):
                            stdout = tool_result.get('stdout', '')
                            stderr = tool_result.get('stderr', '')
                            if stdout:
                                progress_msg += f"Output: {stdout[:300]}"
                            elif stderr:
                                progress_msg += f"Stderr: {stderr[:300]}"
                            elif "content" in tool_result:
                                progress_msg += f"Content: {tool_result['content'][:300]}"
                            elif "message" in tool_result:
                                progress_msg += f"{tool_result['message']}"
                            else:
                                progress_msg += f"(command completed with no output)"
                        else:
                            progress_msg += f"Error: {tool_result.get('error', 'Unknown error')}"
                        
                        execution_log.append(progress_msg)
                        
                        # Truncate tool result to avoid context window overflow
                        # Keep only essential info for the LLM to reason about
                        truncated_result = tool_result.copy()
                        for key in ['stdout', 'content', 'message', 'error']:
                            if key in truncated_result and isinstance(truncated_result[key], str):
                                if len(truncated_result[key]) > 2000:
                                    truncated_result[key] = truncated_result[key][:2000] + "... [truncated]"
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(truncated_result)
                        })
                    
                    # Continue the loop to get the next response
                    continue
                
                # No more tool calls, send final response with all execution logs
                final_response = "\n\n".join(execution_log)
                if response_message.content:
                    final_response += f"\n\n📋 Final Summary:\n{response_message.content}"
                
                await event_queue.enqueue_event(
                    new_agent_text_message(final_response, context_id=context.context_id)
                )
                break
                
            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error and retry after delay
                if "RateLimitError" in error_str or "rate limit" in error_str.lower():
                    import re
                    # Try to extract wait time from error message
                    wait_match = re.search(r'try again in (\d+\.?\d*)', error_str.lower())
                    wait_time = float(wait_match.group(1)) if wait_match else 10
                    wait_time = min(wait_time + 2, 30)  # Add buffer, max 30s
                    execution_log.append(f"⏳ Rate limited, waiting {wait_time}s...")
                    import time
                    time.sleep(wait_time)
                    continue  # Retry the iteration
                
                error_msg = f"Error during execution: {error_str}"
                execution_log.append(error_msg)
                final_response = "\n\n".join(execution_log)
                await event_queue.enqueue_event(
                    new_agent_text_message(final_response, context_id=context.context_id)
                )
                break
        
        if iteration >= self.max_iterations:
            final_response = "\n\n".join(execution_log)
            final_response += "\n\n⚠️ Reached maximum iteration limit. Task may be incomplete."
            await event_queue.enqueue_event(
                new_agent_text_message(final_response, context_id=context.context_id)
            )
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the current execution."""
        pass


def start_white_agent(agent_name="general_white_agent", host=None, port=None):
    """Start the white agent server."""
    # Use environment variables if provided, otherwise use defaults
    host = host or os.getenv("HOST", "0.0.0.0")
    # Prioritize port argument (from agentbeats), then AGENT_PORT (set by agentbeats), then PORT (Cloud Run default), then default
    # AGENT_PORT is set by agentbeats when it spawns the agent process
    port = port or int(os.getenv("AGENT_PORT") or os.getenv("PORT") or "9002")
    
    # Determine the agent URL based on HTTPS_ENABLED and CLOUDRUN_HOST (like green agent)
    https_enabled = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
    cloudrun_host = os.getenv("CLOUDRUN_HOST")
    
    if cloudrun_host:
        # Use Cloud Run hostname (agentbeats will handle port assignment via port argument)
        protocol = "https" if https_enabled else "http"
        url = f"{protocol}://{cloudrun_host}"
    else:
        # Use local host and port
        protocol = "https" if https_enabled else "http"
        url = f"{protocol}://{host}:{port}"
    
    print("Starting white agent...")
    card = prepare_white_agent_card(url)
    
    request_handler = DefaultRequestHandler(
        agent_executor=GeneralWhiteAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    app = A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler,
    ).build()
    
    print(f"Starting white agent at: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

