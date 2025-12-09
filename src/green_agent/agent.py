import os
import json
import tomllib
import uvicorn
import asyncio
from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import EventQueue
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message

from .evaluation.evaluator import TACEvaluator, parse_evaluation_request
from .evaluation.task_selector import parse_task_config


def load_card():
    folder = __file__.rsplit("/", 1)[0]
    path = f"{folder}/green_agent.toml"
    with open(path, "rb") as f:
        return tomllib.load(f)


class GreenAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        message = context.get_user_input()
        print("Green agent received:", message)
        
        try:
            # Parse the evaluation request
            parsed = parse_evaluation_request(message)
            white_agent_url = parsed.get("white_agent_url")
            eval_config = parsed.get("config", {})
            
            if not white_agent_url:
                await event_queue.enqueue_event(
                    new_agent_text_message(
                        "Error: Could not find white_agent_url in the request. "
                        "Please provide the white agent URL in <white_agent_url> tags."
                    )
                )
                return
            
            # Send initial acknowledgment
            await event_queue.enqueue_event(
                new_agent_text_message(
                    f"Starting evaluation of white agent at {white_agent_url}...\n"
                    f"Parsing evaluation configuration..."
                )
            )
            
            # Parse task configuration
            task_selector = parse_task_config(eval_config)
            selected_tasks = task_selector.select_tasks()
            
            await event_queue.enqueue_event(
                new_agent_text_message(
                    f"Selected {len(selected_tasks)} tasks for evaluation:\n"
                    + "\n".join(f"  - {task}" for task in selected_tasks)
                )
            )
            
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
            
            # Run evaluation
            await event_queue.enqueue_event(
                new_agent_text_message("Starting task evaluations...")
            )
            
            results = await evaluator.evaluate_tasks(
                task_selector,
                context_id=context.context_id,
            )
            
            # Format results for response
            summary = results.get("summary", {})
            response_text = self._format_results(summary, results.get("tasks", []))
            
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
        lines = [
            "\n" + "="*60,
            "EVALUATION RESULTS",
            "="*60,
            "",
            f"Total Tasks: {summary.get('total_tasks', 0)}",
            f"Completed: {summary.get('completed', 0)}",
            f"Failed: {summary.get('failed', 0)}",
            "",
            f"Overall Score: {summary.get('total_score', 0)}/{summary.get('total_possible', 0)}",
            f"Score Percentage: {summary.get('overall_score', 0.0)*100:.1f}%",
            "",
            "Task Details:",
            "-"*60,
        ]
        
        for task in tasks:
            task_name = task.get("task_name", "unknown")
            status = task.get("status", "unknown")
            elapsed = task.get("elapsed_time", 0)
            
            if status == "completed":
                eval_result = task.get("evaluation", {})
                final_score = eval_result.get("final_score", {})
                score = final_score.get("result", 0)
                total = final_score.get("total", 0)
                lines.append(
                    f"  ✓ {task_name}: {score}/{total} ({elapsed:.1f}s)"
                )
            elif status == "failed":
                error = task.get("error", "Unknown error")
                lines.append(
                    f"  ✗ {task_name}: FAILED - {error} ({elapsed:.1f}s)"
                )
            else:
                lines.append(f"  ? {task_name}: {status}")
        
        lines.append("="*60)
        
        return "\n".join(lines)

    async def cancel(self, context, event_queue):
        pass


def start_green_agent(host=None, port=None):
    # Use environment variables if provided, otherwise use defaults
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("AGENT_PORT", "9001"))
    
    card_dict = load_card()
    
    # Determine the agent URL based on HTTPS_ENABLED and CLOUDRUN_HOST
    https_enabled = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
    cloudrun_host = os.getenv("CLOUDRUN_HOST")
    
    if cloudrun_host:
        # Use Cloudflare tunnel domain
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
    print("Starting green agent at:", f"http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
