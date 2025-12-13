"""Launcher module - initiates and coordinates the evaluation process."""

import asyncio
import json
import multiprocessing
import os
from pathlib import Path
from src.green_agent import start_green_agent
from src.white_agent import start_white_agent
from src.utils.a2a_client import send_message_to_agent, wait_agent_ready


def load_env_file():
    """Load .env file from project root."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Don't override existing environment variables (from terminal)
                    # Only set if not already set
                    if key not in os.environ:
                        # Skip placeholder values
                        if value not in ['your-openai-api-key-here', 'your_api_key', '']:
                            os.environ[key] = value


# Load environment variables at import time
load_env_file()


async def test_send_message(agent_url="http://localhost:9001", message="Hello from launcher!"):
    """Test sending a message to an agent."""
    print(f"Sending message to {agent_url}...")
    print(f"Message: {message}")
    print("-" * 50)
    
    try:
        response = await send_message_to_agent(
            agent_url,
            message
        )
        print("✅ Success! Response received:")
        # Extract the message text from the response
        if hasattr(response, 'result') and hasattr(response.result, 'parts'):
            message_text = ' '.join([
                part.root.text for part in response.result.parts 
                if hasattr(part, 'root') and hasattr(part.root, 'text')
            ])
            print(f"Agent replied: {message_text}")
        else:
            print(response)
        return response
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def launch_evaluation():
    """Launch the complete evaluation workflow."""
    # Start green agent
    print("Launching green agent...")
    green_address = ("localhost", 9001)
    green_url = f"http://{green_address[0]}:{green_address[1]}"
    
    p_green = multiprocessing.Process(
        target=start_green_agent,
        args=(green_address[0], green_address[1])
    )
    p_green.start()
    
    assert await wait_agent_ready(green_url), "Green agent not ready in time"
    print("Green agent is ready.")
    
    # Start white agent
    print("Launching white agent...")
    white_address = ("localhost", 9002)
    white_url = f"http://{white_address[0]}:{white_address[1]}"
    
    p_white = multiprocessing.Process(
        target=start_white_agent,
        args=("agent_company_white_agent", white_address[0], white_address[1])
    )
    p_white.start()
    
    assert await wait_agent_ready(white_url), "White agent not ready in time"
    print("White agent is ready.")

    # Send the task description to green agent
    print("Sending task description to green agent...")
    task_config = {
        "task_names": [
            "pm-create-channel-new-leader"
        ],
    }
    
    task_text = f"""
Your task is to begin an assessment of the white agent located at:

<white_agent_url>
{white_url}/
</white_agent_url>

Use the following evaluation configuration:

<evaluation_config>
{json.dumps(task_config, indent=2)}
</evaluation_config>
    """
    
    print("Task description:")
    print(task_text)
    print("Sending...")
    
    try:
        # 10 minute timeout - increased for complex tasks with Vision API
        response = await send_message_to_agent(green_url, task_text, timeout=600.0)
        
        # Extract and print response
        print("\n" + "=" * 60)
        print("GREEN AGENT RESPONSE:")
        print("=" * 60)
        
        # Extract response text
        full_text = []
        if hasattr(response, 'result') and hasattr(response.result, 'parts'):
            for part in response.result.parts:
                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                    full_text.append(part.root.text)
        
        if not full_text:
            # Fallback: convert response to string
            full_text = [str(response)]
        
        complete_response = '\n'.join(full_text)
        print(complete_response)
        
        # Save results to file (use absolute path to project root)
        project_root = Path(__file__).parent.parent
        output_file = project_root / 'evaluation_results.txt'
        try:
            with open(output_file, 'w') as f:
                f.write(complete_response)
            print(f"\n✓ Results saved to: {output_file}")
        except Exception as save_error:
            print(f"\n⚠️  Failed to save results to file: {save_error}")
            print(f"Response text (first 500 chars): {complete_response[:500]}")
        
        print("\n✓ Evaluation request completed!")
    except Exception as e:
        print(f"❌ Error sending task: {e}")
        import traceback
        traceback.print_exc()

    print("\nEvaluation complete. Terminating agents...")
    p_green.terminate()
    p_green.join()
    p_white.terminate()
    p_white.join()
    print("Agents terminated.")


async def main():
    """Main entry point for launcher."""
    # For testing, use test_send_message
    # For full evaluation, use launch_evaluation
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        await launch_evaluation()
    else:
        await test_send_message()


if __name__ == "__main__":
    asyncio.run(main())
