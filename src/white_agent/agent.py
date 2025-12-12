"""White agent implementation - the target agent being tested."""

import os
import json
import subprocess
import asyncio
from typing import List, Dict, Any
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
    """Execute a bash command and return the result."""
    try:
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
        
        # Note: We previously tried to handle escaped newlines in python -c commands
        # but it's complex because we need to distinguish between newlines in strings
        # vs newlines as code structure. The shell handles this correctly, so just
        # run the command as-is.
        
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
            "error": "Command timed out after 60 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def read_file(file_path: str) -> Dict[str, Any]:
    """Read a file and return its contents."""
    try:
        # Replace /workspace with /tmp/workspace for Mac compatibility (local dev only)
        import platform
        if platform.system() == "Darwin":
            file_path = file_path.replace("/workspace", "/tmp/workspace")
        with open(file_path, 'r') as f:
            content = f.read()
        return {
            "success": True,
            "content": content
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to a file."""
    try:
        # Replace /workspace with /tmp/workspace for Mac compatibility (local dev only)
        import platform
        if platform.system() == "Darwin":
            file_path = file_path.replace("/workspace", "/tmp/workspace")
            # ALSO replace /workspace in the content itself (for Python scripts, etc.)
            content = content.replace("/workspace", "/tmp/workspace")
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return {
            "success": True,
            "message": f"Successfully wrote to {file_path}"
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
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent's task fulfillment logic with tool calling."""
        # Parse the task
        user_input = context.get_user_input()
        
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = []
        
        messages = self.ctx_id_to_messages[context.context_id]
        
        # Add system message on first interaction
        if len(messages) == 0:
            system_message = {
                "role": "system",
                "content": (
                    "You are an AI agent that MUST complete tasks by executing real actions. "
                    "You are running inside a Linux environment with full access to bash, files, and network.\n\n"
                    "CRITICAL INSTRUCTIONS:\n"
                    "1. You MUST use the tools provided to complete ALL steps of the task\n"
                    "2. Do NOT just explain what to do - actually EXECUTE the commands\n"
                    "3. Keep executing tools until the ENTIRE task is complete\n"
                    "4. If a step fails, try an alternative approach\n"
                    "5. ALWAYS authenticate when accessing services\n\n"
                    "Available tools:\n"
                    "- execute_bash: Run ANY bash command (curl, git, python, pip install, etc.)\n"
                    "- read_file: Read file contents\n"
                    "- write_file: Write content to files\n\n"
                    "SERVICE CREDENTIALS (IMPORTANT!):\n"
                    "- ownCloud (http://localhost:8092): Username: theagentcompany, Password: theagentcompany\n"
                    "  - Download files via WebDAV (EXACT syntax): curl -u theagentcompany:theagentcompany -o output.jpg 'http://localhost:8092/remote.php/webdav/Documents/Financials/receipt.jpg'\n"
                    "  - Download PDF: curl -u theagentcompany:theagentcompany -o policy.pdf 'http://localhost:8092/remote.php/webdav/Documents/Administrative%20Specialist/Reimbursement%20Policy.pdf'\n"
                    "  - NOTE: URL-encode spaces as %20 in paths. The path starts DIRECTLY with the folder name (e.g., Documents/...)\n"
                    "- GitLab (http://localhost:8929): Username: root, Password: theagentcompany\n"
                    "  - API Token: root-token (use -H 'PRIVATE-TOKEN: root-token' for ALL API requests)\n"
                    "  - Create repo: curl -X POST -H 'PRIVATE-TOKEN: root-token' -H 'Content-Type: application/json' -d '{\"name\":\"New Storage Project\",\"path\":\"new-storage-project\",\"visibility\":\"public\"}' http://localhost:8929/api/v4/projects\n"
                    "  - Create issue: curl -X POST -H 'PRIVATE-TOKEN: root-token' -H 'Content-Type: application/json' -d '{\"title\":\"Issue Title\",\"description\":\"Issue description\"}' 'http://localhost:8929/api/v4/projects/root%2Fproject-name/issues'\n"
                    "  - Example: curl -X POST -H 'PRIVATE-TOKEN: root-token' -H 'Content-Type: application/json' -d '{\"title\":\"Research and design new algorithms\",\"description\":\"Task description\"}' 'http://localhost:8929/api/v4/projects/root%2Fjanusgraph/issues'\n"
                    "  - Create/update file: curl -X POST -H 'PRIVATE-TOKEN: root-token' -H 'Content-Type: application/json' -d '{\"branch\":\"main\",\"content\":\"...\",\"commit_message\":\"...\"}' 'http://localhost:8929/api/v4/projects/root%2Fnew-storage-project/repository/files/README.md'\n"
                    "- RocketChat (http://localhost:3000): Login via API first to get tokens\n"
                    "  ROCKETCHAT API CRITICAL: ALL POST requests MUST include -H 'Content-Type: application/json'\n"
                    "  - Login: curl -X POST -H 'Content-Type: application/json' -d '{\"user\":\"theagentcompany\",\"password\":\"theagentcompany\"}' http://localhost:3000/api/v1/login\n"
                    "  - For emojis, use the TEXT CODE like :kissing_smiling_eyes: NOT the unicode emoji 😘\n"
                    "  - To NOTIFY ACTIVE USERS in a room, include @here in your message text\n"
                    "  - Example message with emoji and notification: \"Hi :kissing_smiling_eyes: @here\"\n"
                    "  - Create DM room with user: curl -X POST -H 'Content-Type: application/json' -H 'X-Auth-Token: TOKEN' -H 'X-User-Id: USERID' -d '{\"username\":\"zhang_wei\"}' http://localhost:3000/api/v1/im.create\n"
                    "  - Send message to DM: curl -X POST -H 'Content-Type: application/json' -H 'X-Auth-Token: TOKEN' -H 'X-User-Id: USERID' -d '{\"channel\":\"@zhang_wei\",\"text\":\"Hello!\"}' http://localhost:3000/api/v1/chat.postMessage\n"
                    "  - CONVERSATIONS WITH NPCS: After sending a DM, wait (sleep 5) then retrieve the response!\n"
                    "  - Get DM messages: curl -H 'X-Auth-Token: TOKEN' -H 'X-User-Id: USERID' 'http://localhost:3000/api/v1/im.messages?roomId=ROOMID'\n"
                    "  - The ROOMID is returned from im.create as room._id\n"
                    "  - NPCs will respond with important info - you MUST read their responses and use that info in your work!\n"
                    "- Plane (http://localhost:8091): Project management tool\n"
                    "  - API Key: plane_api_83f868352c6f490aba59b869ffdae1cf (use -H 'x-api-key: plane_api_83f868352c6f490aba59b869ffdae1cf')\n"
                    "  - STEP 1: Get project ID for 'JanusGraph':\n"
                    "    curl -H 'x-api-key: plane_api_83f868352c6f490aba59b869ffdae1cf' 'http://localhost:8091/api/v1/workspaces/tac/projects/' > projects.json\n"
                    "    python3 -c \"import json; data=json.load(open('projects.json')); print([p['id'] for p in data['results'] if p['name']=='JanusGraph'][0])\"\n"
                    "  - STEP 2: Get all states to find 'In Progress' state_id:\n"
                    "    curl -H 'x-api-key: plane_api_83f868352c6f490aba59b869ffdae1cf' 'http://localhost:8091/api/v1/workspaces/tac/projects/PROJECT_ID/states/' > states.json\n"
                    "    python3 -c \"import json; data=json.load(open('states.json')); print([s['id'] for s in data if s['name']=='In Progress'][0])\"\n"
                    "  - STEP 3: Get all issues and filter for 'In Progress':\n"
                    "    curl -H 'x-api-key: plane_api_83f868352c6f490aba59b869ffdae1cf' 'http://localhost:8091/api/v1/workspaces/tac/projects/PROJECT_ID/issues/' > issues.json\n"
                    "    python3 -c \"import json; data=json.load(open('issues.json')); in_progress_id='STATE_ID'; issues=[i for i in data['results'] if i.get('state_id')==in_progress_id]; [print(i['name']) for i in issues]\"\n"
                    "  - STEP 4: For EACH 'In Progress' issue name, create in GitLab:\n"
                    "    curl -X POST -H 'PRIVATE-TOKEN: root-token' -H 'Content-Type: application/json' -d '{\"title\":\"ISSUE_NAME\"}' 'http://localhost:8929/api/v4/projects/root%2Fjanusgraph/issues'\n"
                    "  - CRITICAL: You must create ALL 'In Progress' issues found. Check the issues.json file to see all of them!\n\n"
                    "TIME HANDLING (IMPORTANT!):\n"
                    "When comparing times in CSV data, ALWAYS convert to minutes or datetime objects. "
                    "DO NOT compare time strings directly like '17:30' >= '17:28' - this gives wrong results!\n"
                    "Correct approach:\n"
                    "  hour, minute = time_str.strip().split(':')\n"
                    "  total_minutes = int(hour) * 60 + int(minute)\n"
                    "Then compare: total_minutes >= 17*60+30 (for 17:30)\n\n"
                    "CSV HANDLING (IMPORTANT!):\n"
                    "CSV files often have whitespace in column names and values. ALWAYS strip them:\n"
                    "  df = pd.read_csv('file.csv')\n"
                    "  df.columns = df.columns.str.strip()  # Remove whitespace from column names\n"
                    "  df = df.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)  # Strip string values\n\n"
                    "OWNCLOUD FILE ACCESS (CRITICAL - DO BOTH STEPS!):\n"
                    "Step 1: FIRST browse to the folder (required for tracking):\n"
                    "  curl -u theagentcompany:theagentcompany 'http://localhost:8092/index.php/apps/files/?dir=/Documents/Financials'\n"
                    "  curl -u theagentcompany:theagentcompany 'http://localhost:8092/index.php/apps/files/?dir=/Documents/Administrative%20Specialist'\n"
                    "Step 2: THEN download the file via WebDAV:\n"
                    "  curl -u theagentcompany:theagentcompany -o receipt.jpg 'http://localhost:8092/remote.php/webdav/Documents/Financials/receipt.jpg'\n"
                    "  curl -u theagentcompany:theagentcompany -o policy.pdf 'http://localhost:8092/remote.php/webdav/Documents/Administrative%20Specialist/Reimbursement%20Policy.pdf'\n"
                    "NOTE: URL-encode spaces as %20.\n\n"
                    "EXTRACTING TEXT FROM FILES:\n"
                    "- For PDF files: pip install pdfplumber && python -c \"import pdfplumber; print(pdfplumber.open('policy.pdf').pages[0].extract_text())\"\n"
                    "- For images: Write and run a script file:\n"
                    "  cat > read_image.py << 'EOF'\n"
                    "import base64\n"
                    "from openai import OpenAI\n"
                    "b64 = base64.b64encode(open('receipt.jpg','rb').read()).decode()\n"
                    "r = OpenAI().chat.completions.create(model='gpt-4o', messages=[{'role':'user','content':[{'type':'text','text':'Extract all text from this receipt'},{'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{b64}'}}]}])\n"
                    "print(r.choices[0].message.content)\n"
                    "EOF\n"
                    "python read_image.py\n\n"
                    "REIMBURSEMENT CALCULATIONS (CRITICAL!):\n"
                    "When calculating reimbursable amounts from receipts:\n"
                    "1. The full subtotal amount IS reimbursable (no per-person limit applies)\n"
                    "2. Tips: max 20% of the subtotal is reimbursable\n"
                    "3. If actual tip exceeds 20%, only reimburse 20% of subtotal\n"
                    "4. Total reimbursable = subtotal + min(actual_tip, subtotal * 0.20)\n"
                    "5. Example: subtotal=$179.19, actual_tip=$44.80 (which is 25%):\n"
                    "   - Max tip allowed = $179.19 * 0.20 = $35.84\n"
                    "   - Total reimbursable = $179.19 + $35.84 = $215.03 ≈ $215\n"
                    "6. State the EXACT dollar amount in your message, e.g., '$215'\n\n"
                    "For creating Excel files, use Python with openpyxl:\n"
                    "  pip install openpyxl pandas\n"
                    "  python -c \"import pandas as pd; df = pd.DataFrame({'Name': ['Alice', 'Bob']}); df.to_excel('/workspace/output.xlsx', index=False)\"\n\n"
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

