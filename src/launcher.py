"""Launcher module - initiates and coordinates the evaluation process."""

import asyncio
import json
import multiprocessing
from src.green_agent import start_green_agent
from src.white_agent import start_white_agent
from src.utils.a2a_client import send_message_to_agent, wait_agent_ready


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
        "task_subset": "beginner",
        "max_tasks": 1
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
        # Use longer timeout for evaluation (30 minutes)
        # Docker evaluation can take 5-10 minutes per task, plus processing time
        response = await send_message_to_agent(green_url, task_text, timeout=1800.0)
        
        # Extract and print response
        print("\n" + "=" * 60)
        print("GREEN AGENT RESPONSE:")
        print("=" * 60)
        
        if hasattr(response, 'result') and hasattr(response.result, 'parts'):
            full_text = []
            for part in response.result.parts:
                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                    full_text.append(part.root.text)
            
            complete_response = '\n'.join(full_text)
            print(complete_response)
            
            # Save results to file
            output_file = 'evaluation_results.txt'
            with open(output_file, 'w') as f:
                f.write(complete_response)
            print(f"\n✓ Results saved to: {output_file}")
        else:
            print(response)
        
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
