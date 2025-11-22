import asyncio
from src.utils.a2a_client import send_message_to_agent

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

async def main():
    # Test with a simple message
    await test_send_message()

if __name__ == "__main__":
    asyncio.run(main())
