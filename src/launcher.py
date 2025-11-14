import asyncio
from src.utils.a2a_client import send_message_to_agent

async def main():
    print("Sending test message...")
    response = await send_message_to_agent(
        "http://localhost:9001",
        "Hello <json>{\"test\": 1}</json>"
    )
    print("Response:", response)

if __name__ == "__main__":
    asyncio.run(main())
