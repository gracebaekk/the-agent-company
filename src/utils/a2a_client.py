import httpx
import uuid
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams, Message, Part, TextPart, Role

async def send_message_to_agent(url, message, context_id=None):
    """Send a message to an A2A agent."""
    async with httpx.AsyncClient() as httpx_client:
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