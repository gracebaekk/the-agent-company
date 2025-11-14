import typer
import asyncio
import sys, os
from src.green_agent import start_green_agent
# from src.white_agent import start_white_agent
# from src.launcher import launch_evaluation

sys.path.append(os.path.join(os.path.dirname(__file__), "external/tac"))
app = typer.Typer(help="Agentified TheAgentCompany - Standardized agent assessment framework", no_args_is_help=True)


@app.command()
def green():
    """Start the green agent (assessment manager)."""
    start_green_agent()


# @app.command()
# def white():
#     """Start the white agent (target being tested)."""
#     start_white_agent()


# @app.command()
# def launch():
#     """Launch the complete evaluation workflow."""
#     asyncio.run(launch_evaluation())


if __name__ == "__main__":
    app()