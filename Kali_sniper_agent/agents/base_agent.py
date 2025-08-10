import asyncio
from common.messaging import get_rabbitmq_connection

class BaseAgent:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def initialize(self):
        """Initializes the RabbitMQ connection and channel."""
        self.connection = await get_rabbitmq_connection()
        self.channel = await self.connection.channel()
        print(f"✅ {self.__class__.__name__} initialized.")

    async def run(self):
        """A placeholder for the agent's main logic loop."""
        raise NotImplementedError

    async def close(self):
        """Closes the RabbitMQ connection."""
        if self.connection:
            await self.connection.close()