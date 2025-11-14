from a2a.client import A2AClient

client = A2AClient()

async def send_message_to_agent(url, message, context_id=None):
    return await client.send_message(
        agent_url=url,
        message=message,
        context_id=context_id
    )