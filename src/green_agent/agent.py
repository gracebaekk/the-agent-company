import os
import tomllib
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import EventQueue
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message


def load_card():
    folder = __file__.rsplit("/", 1)[0]
    path = f"{folder}/green_agent.toml"
    with open(path, "rb") as f:
        return tomllib.load(f)


class GreenAgentExecutor(AgentExecutor):
    async def handle_message(self, context: RequestContext, event_queue: EventQueue):
        # Forward to execute method
        return await self.execute(context, event_queue)
    
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        message = context.get_user_input()
        print("Green agent received:", message)

        await event_queue.enqueue_event(
            new_agent_text_message("Hello from the green agent!")
        )

    async def cancel(self, context, event_queue):
        pass


def start_green_agent(host=None, port=None):
    # Use environment variables if provided, otherwise use defaults
    host = host or os.getenv("HOST", "localhost")
    port = port or int(os.getenv("AGENT_PORT", "9001"))
    
    card_dict = load_card()
    card_dict["url"] = f"http://{host}:{port}"

    card = AgentCard(**card_dict)

    handler = DefaultRequestHandler(
        agent_executor=GreenAgentExecutor(),
        task_store=InMemoryTaskStore()
    )

    app = A2AStarletteApplication(agent_card=card, http_handler=handler).build()
    print("=== ROUTES ===")
    for route in app.routes:
        print("•", route)
    print("================")

    print("Starting green agent at:", f"http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
