import typer
import asyncio
import sys, os
from src.green_agent import start_green_agent
from src.white_agent import start_white_agent
from src.launcher import test_send_message, launch_evaluation, launch_remote_evaluation


sys.path.append(os.path.join(os.path.dirname(__file__), "external/tac"))
app = typer.Typer(help="Agentified TheAgentCompany - Standardized agent assessment framework", no_args_is_help=True)


@app.command()
def green():
    """Start the green agent (assessment manager)."""
    start_green_agent()

@app.command()
def white():
    """Start the white agent (target being tested)."""
    start_white_agent()


@app.command()
def run():
    """Run the agent based on ROLE environment variable (used by controller)."""
    role = os.getenv("ROLE", "green")
    port = int(os.getenv("AGENT_PORT") or os.getenv("PORT") or 0)
    if role == "white":
        start_white_agent(port=port if port > 0 else None)
    else:
        # Check if running via agentbeats (agentbeats sets AGENT_URL with /to_agent/ path)
        # When using agentbeats, don't add info routes as agentbeats handles routing
        is_agentbeats = os.getenv("AGENT_URL", "").startswith("http") and "/to_agent/" in os.getenv("AGENT_URL", "")
        # Only add info routes when NOT using agentbeats (standalone mode)
        add_info_route = not is_agentbeats
        start_green_agent(port=port if port > 0 else None, add_info_route=add_info_route)


@app.command()
def test(
    url: str = typer.Option("http://localhost:9001", help="URL of the agent to test"),
    message: str = typer.Option("Hello! This is a test message.", help="Message to send")
):
    """Test sending a message to an agent."""
    asyncio.run(test_send_message(url, message))


@app.command()
def launch():
    """Launch the complete evaluation workflow."""
    asyncio.run(launch_evaluation())

@app.command()
def launch_remote(green_url: str, white_url: str):
    """Launch the complete evaluation workflow."""
    asyncio.run(launch_remote_evaluation(green_url, white_url))


if __name__ == "__main__":
    app()