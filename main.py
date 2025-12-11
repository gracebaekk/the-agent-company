import typer
import asyncio
import sys, os
from src.green_agent import start_green_agent
from src.launcher import test_send_message, launch_evaluation
from src.white_agent import start_white_agent
# from src.launcher import launch_evaluation

sys.path.append(os.path.join(os.path.dirname(__file__), "external/tac"))
app = typer.Typer(help="Agentified TheAgentCompany - Standardized agent assessment framework", no_args_is_help=True)


@app.command()
def green():
    """Start the green agent (assessment manager)."""
    start_green_agent()


@app.command()
def run(port: int = None):
    """Run the agent based on ROLE environment variable (used by controller)."""
    role = os.getenv("ROLE", "green")
    # If port is provided (by agentbeats), use it; otherwise use environment variables
    # AGENT_PORT is set by agentbeats when it spawns the agent process
    if port is None:
        port = int(os.getenv("AGENT_PORT") or os.getenv("PORT") or 0)
    if role == "white":
        start_white_agent(port=port if port > 0 else None)
    else:
        start_green_agent(port=port if port > 0 else None)


@app.command()
def test(
    url: str = typer.Option("http://localhost:9001", help="URL of the agent to test"),
    message: str = typer.Option("Hello! This is a test message.", help="Message to send")
):
    """Test sending a message to an agent."""
    asyncio.run(test_send_message(url, message))


@app.command()
def white():
    """Start the white agent (target being tested)."""
    start_white_agent()


@app.command()
def launch():
    """Launch the complete evaluation workflow."""
    asyncio.run(launch_evaluation())


if __name__ == "__main__":
    app()