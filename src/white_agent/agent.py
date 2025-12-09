"""White agent implementation - the target agent being tested."""

import os
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
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

# Try to import Playwright, but make it optional
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not available. Browser automation will be disabled.")


def prepare_white_agent_card(url):
    """Prepare the agent card for the white agent."""
    skill = AgentSkill(
        id="task_fulfillment",
        name="Task Fulfillment",
        description="Handles user requests and completes tasks using TheAgentCompany framework with tool-calling capabilities",
        tags=["general", "the-agent-company", "tool-calling"],
        examples=[],
    )
    
    card = AgentCard(
        name="agent_company_white_agent",
        description="White agent for TheAgentCompany evaluation with tool-calling support",
        url=url,
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(message=True, task=False, streaming=False),
        skills=[skill],
    )
    
    return card


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get tool definitions for function calling."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_bash",
                "description": "Execute a bash command in the workspace. Use this to run shell commands, navigate directories, read files, download files, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute"
                        },
                        "thought": {
                            "type": "string",
                            "description": "Brief explanation of why you're running this command"
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser",
                "description": "Interact with a web browser to navigate websites, click elements, fill forms, etc. Use this for tasks involving web interfaces like RocketChat, GitLab, OwnCloud, Plane, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "browser_actions": {
                            "type": "string",
                            "description": "Browser actions in browsergym format. Examples: goto('url'), click('selector'), fill('selector', 'text'), etc."
                        },
                        "thought": {
                            "type": "string",
                            "description": "Brief explanation of what you're trying to do in the browser"
                        }
                    },
                    "required": ["browser_actions"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "file_editor",
                "description": "Create, read, or edit files. Use this to create new files, modify existing files, or read file contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The file operation: 'create', 'read', 'edit', or 'delete'",
                            "enum": ["create", "read", "edit", "delete"]
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to the file"
                        },
                        "file_text": {
                            "type": "string",
                            "description": "File content (for create/edit operations)"
                        },
                        "thought": {
                            "type": "string",
                            "description": "Brief explanation of what you're doing with the file"
                        }
                    },
                    "required": ["command", "path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "finish",
                "description": "Call this when you have completed the task. Provide a summary of what was accomplished.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "outputs": {
                            "type": "object",
                            "description": "Any outputs or results from the task"
                        },
                        "thought": {
                            "type": "string",
                            "description": "Summary of task completion"
                        }
                    },
                    "required": ["thought"]
                }
            }
        }
    ]
    return tools


class ToolExecutor:
    """Executes tools called by the agent."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    async def initialize_browser(self):
        """Initialize browser if Playwright is available."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
        return True
    
    async def execute_bash(self, command: str, thought: Optional[str] = None) -> Dict[str, Any]:
        """Execute a bash command asynchronously."""
        try:
            print(f"[ToolExecutor] Executing bash command: {command}")
            cwd = "/workspace" if os.path.exists("/workspace") else os.getcwd()
            
            # Normalize URLs in command: replace the-agent-company.com with localhost
            # This allows White agent running on host to access Docker services
            if "the-agent-company.com" in command:
                command = command.replace("the-agent-company.com", "localhost")
                print(f"[ToolExecutor] Normalized command URL: {command}")
            
            # Add timeout to curl commands to prevent hanging
            if command.strip().startswith("curl"):
                # Extract timeout if already present
                if "--max-time" not in command and "--connect-timeout" not in command:
                    # Add reasonable timeout (30 seconds for network commands)
                    command = command.replace("curl ", "curl --max-time 30 --connect-timeout 10 ", 1)
                    print(f"[ToolExecutor] Added timeout to curl command: {command}")
            
            # Use async subprocess to avoid blocking
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for completion with timeout (shorter for network commands)
            timeout = 60.0 if "curl" in command else 300.0
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                exit_code = process.returncode
                
                return {
                    "success": True,
                    "exit_code": exit_code,
                    "stdout": stdout.decode('utf-8') if stdout else "",
                    "stderr": stderr.decode('utf-8') if stderr else "",
                    "command": command
                }
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": "Command timed out after 300 seconds",
                    "command": command
                }
        except Exception as e:
            print(f"[ToolExecutor] Error executing bash: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL: replace the-agent-company.com with localhost on host machine."""
        # On host machine, the-agent-company.com should map to localhost
        if "the-agent-company.com" in url:
            url = url.replace("the-agent-company.com", "localhost")
            print(f"[ToolExecutor] Normalized URL: {url}")
        return url
    
    async def browser_action(self, browser_actions: str, thought: Optional[str] = None) -> Dict[str, Any]:
        """Execute browser actions."""
        if not await self.initialize_browser():
            return {
                "success": False,
                "error": "Browser automation not available. Playwright is not installed."
            }
        
        try:
            # Parse browsergym-style actions
            # This is a simplified parser - in production, use browsergym library
            if browser_actions.startswith("goto("):
                url = browser_actions[5:-1].strip("'\"")
                url = self._normalize_url(url)  # Normalize URL for host access
                await self.page.goto(url)
                content = await self.page.content()
                return {
                    "success": True,
                    "url": self.page.url,
                    "content": content[:5000],  # Limit content size
                    "action": browser_actions
                }
            elif browser_actions.startswith("click("):
                selector = browser_actions[6:-1].strip("'\"")
                await self.page.click(selector)
                content = await self.page.content()
                return {
                    "success": True,
                    "url": self.page.url,
                    "content": content[:5000],
                    "action": browser_actions
                }
            elif browser_actions.startswith("fill("):
                # Parse fill('selector', 'text')
                parts = browser_actions[5:-1].split(",")
                selector = parts[0].strip().strip("'\"")
                text = parts[1].strip().strip("'\"") if len(parts) > 1 else ""
                await self.page.fill(selector, text)
                return {
                    "success": True,
                    "url": self.page.url,
                    "action": browser_actions
                }
            else:
                # Try to evaluate as Python code (simplified)
                # In production, use proper browsergym evaluation
                return {
                    "success": False,
                    "error": f"Unsupported browser action: {browser_actions}",
                    "action": browser_actions
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": browser_actions
            }
    
    async def file_editor(self, command: str, path: str, file_text: Optional[str] = None, thought: Optional[str] = None) -> Dict[str, Any]:
        """Edit files."""
        try:
            workspace_path = Path("/workspace" if os.path.exists("/workspace") else os.getcwd())
            file_path = workspace_path / path.lstrip("/")
            
            if command == "read":
                if not file_path.exists():
                    return {"success": False, "error": f"File not found: {path}"}
                content = file_path.read_text()
                return {"success": True, "content": content, "path": str(file_path)}
            
            elif command == "create":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_text or "")
                return {"success": True, "path": str(file_path), "message": "File created"}
            
            elif command == "edit":
                if not file_path.exists():
                    return {"success": False, "error": f"File not found: {path}"}
                file_path.write_text(file_text or "")
                return {"success": True, "path": str(file_path), "message": "File updated"}
            
            elif command == "delete":
                if not file_path.exists():
                    return {"success": False, "error": f"File not found: {path}"}
                file_path.unlink()
                return {"success": True, "path": str(file_path), "message": "File deleted"}
            
            else:
                return {"success": False, "error": f"Unknown command: {command}"}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
    
    async def finish(self, outputs: Optional[Dict[str, Any]] = None, thought: str = "") -> Dict[str, Any]:
        """Finish task execution."""
        return {
            "success": True,
            "message": "Task completed",
            "outputs": outputs or {},
            "thought": thought
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class GeneralWhiteAgentExecutor(AgentExecutor):
    """Executor for the white agent that handles user requests with tool-calling."""
    
    def __init__(self):
        self.ctx_id_to_messages = {}
        self.ctx_id_to_tool_executor = {}
    
    def _get_tool_executor(self, context_id: str) -> ToolExecutor:
        """Get or create tool executor for context."""
        if context_id not in self.ctx_id_to_tool_executor:
            self.ctx_id_to_tool_executor[context_id] = ToolExecutor()
        return self.ctx_id_to_tool_executor[context_id]
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent's task fulfillment logic with tool-calling."""
        user_input = context.get_user_input()
        context_id = context.context_id
        
        if context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context_id] = []
        
        messages = self.ctx_id_to_messages[context_id]
        messages.append({
            "role": "user",
            "content": user_input,
        })
        
        # Get model and provider from environment variables
        model = os.getenv("AGENT_MODEL", "openai/gpt-4o")
        provider = os.getenv("AGENT_PROVIDER", "openai")
        
        # Get API key
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
                new_agent_text_message(error_msg, context_id=context_id)
            )
            return
        
        # Get tool definitions
        tools = get_tool_definitions()
        tool_executor = self._get_tool_executor(context_id)
        
        # Send initial acknowledgment immediately to prevent timeout
        await event_queue.enqueue_event(
            new_agent_text_message(
                "I'll work on this task. Processing...",
                context_id=context_id
            )
        )
        
        # Main execution loop - handle tool calls
        max_iterations = 20
        iteration = 0
        
        try:
            while iteration < max_iterations:
                iteration += 1
                print(f"[White Agent] Iteration {iteration}/{max_iterations}")
                
                # Call LLM with tools
                print(f"[White Agent] Calling LLM with {len(messages)} messages...")
                response = completion(
                messages=messages,
                model=model,
                custom_llm_provider=provider,
                temperature=0.0,
                api_key=api_key,
                tools=tools,
                tool_choice="auto",
            )
            
                message = response.choices[0].message
                messages.append(message.model_dump())
                
                # Check if there are tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    print(f"[White Agent] Tool calls detected: {len(message.tool_calls)}")
                    # Execute tool calls
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        print(f"[White Agent] Executing tool: {function_name}")
                        
                        # Execute the tool
                        if function_name == "execute_bash":
                            result = await tool_executor.execute_bash(**function_args)
                        elif function_name == "browser":
                            result = await tool_executor.browser_action(**function_args)
                        elif function_name == "file_editor":
                            result = await tool_executor.file_editor(**function_args)
                        elif function_name == "finish":
                            result = await tool_executor.finish(**function_args)
                            # Task completed - send final response
                            final_message = f"Task completed: {result.get('thought', '')}"
                            if result.get('outputs'):
                                final_message += f"\nOutputs: {json.dumps(result.get('outputs'), indent=2)}"
                            
                            await event_queue.enqueue_event(
                                new_agent_text_message(
                                    final_message,
                                    context_id=context_id
                                )
                            )
                            return
                        else:
                            result = {"success": False, "error": f"Unknown tool: {function_name}"}
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result),
                        })
                        
                        # Don't send intermediate results - wait for final response
                        # This prevents "Queue is closed" errors
                else:
                    # No tool calls - final response
                    print(f"[White Agent] No tool calls, sending final response")
                    content = message.content or ""
                    if not content:
                        # If no content, create a summary of what was done
                        content = "Task execution completed."
                    
                    messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                    
                    # Send final response
                    await event_queue.enqueue_event(
                        new_agent_text_message(
                            content,
                            context_id=context_id
                        )
                    )
                    break
        except Exception as e:
            print(f"[White Agent] Error during execution: {e}")
            import traceback
            traceback.print_exc()
            await event_queue.enqueue_event(
                new_agent_text_message(
                    f"Error during task execution: {str(e)}",
                    context_id=context_id
                )
            )
        
        # If we've exhausted iterations, send a final message
        if iteration >= max_iterations:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "Task execution reached maximum iterations. Please check the results.",
                    context_id=context_id
                )
            )
        
        # Cleanup
        if context_id in self.ctx_id_to_tool_executor:
            await self.ctx_id_to_tool_executor[context_id].cleanup()
            del self.ctx_id_to_tool_executor[context_id]
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the current execution."""
        context_id = context.context_id
        if context_id in self.ctx_id_to_tool_executor:
            await self.ctx_id_to_tool_executor[context_id].cleanup()
            del self.ctx_id_to_tool_executor[context_id]


def start_white_agent(agent_name="general_white_agent", host=None, port=None):
    """Start the white agent server."""
    # Use environment variables if provided, otherwise use defaults
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("AGENT_PORT", "9002"))
    
    print("Starting white agent with tool-calling support...")
    url = f"http://{host}:{port}"
    card = prepare_white_agent_card(url)
    
    request_handler = DefaultRequestHandler(
        agent_executor=GeneralWhiteAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    app = A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler,
    )
    
    print(f"Starting white agent at: {url}")
    uvicorn.run(app.build(), host=host, port=port)
