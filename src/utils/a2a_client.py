import asyncio
import httpx
import uuid
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams, Message, Part, TextPart, Role


async def wait_agent_ready(
    agent_url: str,
    max_attempts: int = 30,
    delay: float = 1.0,
    timeout: float = 5.0
) -> bool:
    """
    Wait for an agent to be ready by checking its agent card endpoint.
    
    Args:
        agent_url: The base URL of the agent
        max_attempts: Maximum number of attempts to check
        delay: Delay between attempts in seconds
        timeout: HTTP request timeout in seconds
    
    Returns:
        True if agent is ready, False otherwise
    """
    agent_card_url = f"{agent_url.rstrip('/')}/.well-known/agent-card.json"
    
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(agent_card_url)
                if response.status_code == 200:
                    print(f"✓ Agent ready at {agent_url}")
                    return True
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"Waiting for agent at {agent_url}... (attempt {attempt + 1}/{max_attempts})")
            else:
                print(f"✗ Agent not ready: {e}")
        
        if attempt < max_attempts - 1:
            await asyncio.sleep(delay)
    
    return False


async def send_message_to_agent(url, message, context_id=None, timeout=300.0):
    """
    Send a message to an A2A agent.
    
    Args:
        url: Agent URL
        message: Message text
        context_id: Optional context ID
        timeout: Request timeout in seconds (default 5 minutes for evaluations)
    """
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        client = A2AClient(httpx_client=httpx_client, url=url)
        
        # Create a user message
        user_message = Message(
            message_id=str(uuid.uuid4()),
            parts=[Part(root=TextPart(text=message))],
            role=Role.user
        )
        
        # Create MessageSendParams
        params = MessageSendParams(message=user_message)
        
        # Create the request
        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            params=params,
            context_id=context_id
        )
        
        return await client.send_message(request)