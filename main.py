import typer
import asyncio
import sys, os
from src.green_agent import start_green_agent
from src.launcher import test_send_message
from src.white_agent import start_white_agent
# from src.launcher import launch_evaluation

sys.path.append(os.path.join(os.path.dirname(__file__), "external/tac"))
app = typer.Typer(help="Agentified TheAgentCompany - Standardized agent assessment framework", no_args_is_help=True)


@app.command()
def green():
    """Start the green agent (assessment manager)."""
    start_green_agent()


@app.command()
def run():
    """Run the green agent (used by controller)."""
    start_green_agent()


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

if __name__ == "__main__":
    app()