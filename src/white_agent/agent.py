"""White agent implementation - the target agent being tested."""

import os
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
    """Executor for the white agent that handles user requests."""
    
    def __init__(self):
        self.ctx_id_to_messages = {}
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent's task fulfillment logic."""
        # Parse the task
        user_input = context.get_user_input()
        
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = []
        
        messages = self.ctx_id_to_messages[context.context_id]
        messages.append({
            "role": "user",
            "content": user_input,
        })
        
        # Get model and provider from environment variables, with defaults
        model = os.getenv("AGENT_MODEL", "openai/gpt-4o")
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
        
        response = completion(
            messages=messages,
            model=model,
            custom_llm_provider=provider,
            temperature=0.0,
            api_key=api_key,
        )
        
        next_message = response.choices[0].message.model_dump()  # type: ignore
        messages.append({
            "role": "assistant",
            "content": next_message["content"],
        })
        
        await event_queue.enqueue_event(
            new_agent_text_message(
                next_message["content"],
                context_id=context.context_id
            )
        )
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the current execution."""
        pass


def start_white_agent(agent_name="general_white_agent", host=None, port=None):
    """Start the white agent server."""
    # Use environment variables if provided, otherwise use defaults
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("AGENT_PORT", "9002"))
    
    print("Starting white agent...")
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

