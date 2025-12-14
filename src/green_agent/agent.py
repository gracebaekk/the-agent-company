import os
import json
import tomllib
import uvicorn
import asyncio
from starlette.routing import Route
from starlette.responses import HTMLResponse, RedirectResponse
from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import EventQueue
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message

from .evaluation.evaluator import TACEvaluator
from .evaluation.task_selector import parse_task_config
import re


def load_card():
    folder = __file__.rsplit("/", 1)[0]
    path = f"{folder}/green_agent.toml"
    with open(path, "rb") as f:
        return tomllib.load(f)


class GreenAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        message = context.get_user_input()
        print("Green agent received:", message)
        print(f"Message length: {len(message)} characters")
        
        try:
            # Extract white_agent_url from message
            url_match = re.search(r'<white_agent_url>\s*(.*?)\s*</white_agent_url>', message, re.DOTALL)
            white_agent_url = url_match.group(1).strip() if url_match else ""
            
            # Read evaluation config from JSON file
            config_file_path = os.getenv("EVALUATION_CONFIG_FILE", "evaluation_config.json")
            eval_config = {}
            
            try:
                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f:
                        eval_config = json.load(f)
                        print(f"Loaded evaluation config from {config_file_path}")
                else:
                    print(f"ERROR: Config file {config_file_path} not found")
            except Exception as e:
                print(f"ERROR: Failed to read config file {config_file_path}: {e}")
                eval_config = {}
            
            if not white_agent_url:
                await event_queue.enqueue_event(
                    new_agent_text_message(
                        "Error: Could not find white_agent_url in the request. "
                        "Please provide the white agent URL in <white_agent_url> tags."
                    )
                )
                return
            
            # Check if task names are in config
            if not eval_config.get("task_names"):
                error_msg = (
                    f"ERROR: No task names found in evaluation config!\n\n"
                    f"Please create evaluation_config.json file with the following format:\n"
                    f'{{"task_names": ["task1", "task2", ...]}}\n\n'
                    f"Or set EVALUATION_CONFIG_FILE environment variable to point to your config file."
                )
                await event_queue.enqueue_event(
                    new_agent_text_message(error_msg)
                )
                print(f"ERROR: {error_msg}")
                return
            
            task_selector = parse_task_config(eval_config)
            selected_tasks = task_selector.select_tasks()
            
            if len(selected_tasks) == 0:
                error_msg = (
                    f"ERROR: No tasks found in evaluation configuration!\n\n"
                    f"Received config: {eval_config}\n"
                    f"Config keys: {list(eval_config.keys())}\n\n"
                    f"Expected format:\n"
                    f"<evaluation_config>\n"
                    f'{{"task_names": ["task1", "task2", ...]}}\n'
                    f"</evaluation_config>\n\n"
                    f"Please check that the evaluation request includes a valid <evaluation_config> section with task_names."
                )
                await event_queue.enqueue_event(
                    new_agent_text_message(error_msg)
                )
                print(f"ERROR: {error_msg}")
                return
            
            # Get server hostname and environment LLM config from environment
            server_hostname = os.getenv("SERVER_HOSTNAME", "localhost")
            env_llm_config = {
                "api_key": os.getenv("LITELLM_API_KEY"),
                "base_url": os.getenv("LITELLM_BASE_URL"),
                "model": os.getenv("LITELLM_MODEL", "openai/gpt-4o"),
            }
            
            # Create evaluator
            evaluator = TACEvaluator(
                white_agent_url=white_agent_url,
                server_hostname=server_hostname,
                env_llm_config=env_llm_config,
            )
            
            # Run evaluation (this may take a while)
            print(f"Starting evaluation of {len(selected_tasks)} tasks...")
            results = await evaluator.evaluate_tasks(
                task_selector,
                context_id=context.context_id,
            )
            
            # Format complete results message with all information
            summary = results.get("summary", {})
            response_text = self._format_results(summary, results.get("tasks", []))
            
            # Send single comprehensive message with all results
            await event_queue.enqueue_event(
                new_agent_text_message(response_text)
            )
            
        except Exception as e:
            error_msg = f"Error during evaluation: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            
            await event_queue.enqueue_event(
                new_agent_text_message(error_msg)
            )
    
    def _format_results(self, summary: dict, tasks: list) -> str:
        """Format evaluation results as a readable string."""
        # Format as single-line text since Agent Beats may not render \n properly
        # Use separators and clear formatting for readability
        result_lines = [
            "EVALUATION COMPLETE",
            f"Total: {summary.get('total_tasks', 0)} tasks | Completed: {summary.get('completed', 0)} | Failed: {summary.get('failed', 0)}",
        ]
        
        # Calculate percentage for each task and collect for average
        task_percentages = []
        task_details = []
        
        for task in tasks:
            task_name = task.get("task_name", "unknown")
            status = task.get("status", "unknown")
            elapsed = task.get("elapsed_time", 0)
            
            if status == "completed":
                eval_result = task.get("evaluation", {})
                final_score = eval_result.get("final_score", {})
                score = final_score.get("result", 0)
                total = final_score.get("total", 0)
                percentage = (score / total * 100) if total > 0 else 0.0
                task_percentages.append(percentage)
                task_details.append(f"{task_name}: {score}/{total} ({percentage:.1f}%)")
            elif status == "failed":
                error = task.get("error", "Unknown error")
                task_details.append(f"{task_name}: FAILED")
            else:
                task_details.append(f"{task_name}: {status}")
        
        if task_details:
            result_lines.append("Tasks: " + " | ".join(task_details))
        
        # Calculate and display average percentage
        if task_percentages:
            avg_percentage = sum(task_percentages) / len(task_percentages)
            result_lines.append(
                f"Average: {avg_percentage:.1f}% | Overall: {summary.get('total_score', 0)}/{summary.get('total_possible', 0)} ({summary.get('overall_score', 0.0)*100:.1f}%)"
            )
        else:
            result_lines.append("No completed tasks")
        
        # Join with spaces - Agent Beats may not render newlines
        return " | ".join(result_lines)

    async def cancel(self, context, event_queue):
        pass


def start_green_agent(host=None, port=None, add_info_route=False):
    # Use environment variables if provided, otherwise use defaults
    host = host or os.getenv("HOST", "0.0.0.0")
    # Prioritize port argument (from agentbeats), then AGENT_PORT (set by agentbeats), then PORT (Cloud Run default), then default
    # AGENT_PORT is set by agentbeats when it spawns the agent process
    port = port or int(os.getenv("AGENT_PORT") or os.getenv("PORT") or "9001")
    
    card_dict = load_card()
    
    # Determine the agent URL
    # Priority: AGENT_URL (set by agentbeats) > CLOUDRUN_HOST > local host:port
    agent_url = os.getenv("AGENT_URL")
    if agent_url:
        # Use AGENT_URL if set (agentbeats sets this to /to_agent/{agent_id})
        card_dict["url"] = agent_url
    else:
        # Fall back to CLOUDRUN_HOST or local host:port
        https_enabled = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
        cloudrun_host = os.getenv("CLOUDRUN_HOST")
        
        if cloudrun_host:
            protocol = "https" if https_enabled else "http"
            card_dict["url"] = f"{protocol}://{cloudrun_host}"
        else:
            # Use local host and port
            protocol = "https" if https_enabled else "http"
            card_dict["url"] = f"{protocol}://{host}:{port}"

    card = AgentCard(**card_dict)

    handler = DefaultRequestHandler(
        agent_executor=GreenAgentExecutor(),
        task_store=InMemoryTaskStore()
    )

    app = A2AStarletteApplication(agent_card=card, http_handler=handler).build()
    
    # Add /info route if requested (for controller-like behavior)
    # Only add when NOT using agentbeats (agentbeats sets AGENT_URL with /to_agent/ path)
    # When using agentbeats, the controller handles routing, so we don't need these routes
    if add_info_route:
        is_agentbeats = os.getenv("AGENT_URL", "").startswith("http") and "/to_agent/" in os.getenv("AGENT_URL", "")
        if not is_agentbeats:
            async def info_endpoint(request):
                """Controller info endpoint."""
                return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Green Agent Controller</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        h1 {{ color: #333; }}
                        .info {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                        .endpoint {{ margin: 10px 0; }}
                        code {{ background: #e8e8e8; padding: 2px 6px; border-radius: 3px; }}
                    </style>
                </head>
                <body>
                    <h1>Green Agent Controller</h1>
                    <div class="info">
                        <h2>Agent Information</h2>
                        <div class="endpoint"><strong>Name:</strong> {card.name}</div>
                        <div class="endpoint"><strong>Description:</strong> {card.description}</div>
                        <div class="endpoint"><strong>Version:</strong> {card.version}</div>
                        <div class="endpoint"><strong>URL:</strong> <code>{card.url}</code></div>
                        
                        <h2>Endpoints</h2>
                        <div class="endpoint"><strong>POST /</strong> - A2A JSON-RPC endpoint</div>
                        <div class="endpoint"><strong>GET /info</strong> - This page</div>
                        <div class="endpoint"><strong>GET /.well-known/agent-card.json</strong> - Agent card</div>
                    </div>
                </body>
                </html>
                """)
            
            async def root_get_handler(request):
                """Redirect GET / to /info."""
                return RedirectResponse(url="/info")
            
            # Add routes to the existing app
            # A2A app already handles POST /, we just add GET routes
            # Insert at the beginning so they take precedence
            app.routes.insert(0, Route("/info", info_endpoint, methods=["GET"]))
            app.routes.insert(1, Route("/", root_get_handler, methods=["GET"]))
            print("  POST / → A2A JSON-RPC handler")
            print("  GET /info → Controller info")
    
    print("Starting green agent at:", f"http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


