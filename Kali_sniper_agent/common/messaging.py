import asyncio
import json
import aio_pika
from termcolor import cprint

# Define the names of our queues
NEW_POOL_QUEUE = "new_pools"
VETTED_TOKENS_QUEUE = "vetted_tokens"

async def get_rabbitmq_connection():
    """Establishes a connection to the RabbitMQ server."""
    return await aio_pika.connect_robust("amqp://guest:guest@localhost/")

async def publish_message(channel: aio_pika.Channel, queue_name: str, message: dict):
    """Publishes a message to the specified queue."""
    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps(message).encode()),
        routing_key=queue_name,
    )
    cprint(f"📬 Sent message to '{queue_name}': {message}", 'green')

async def consume_messages(channel: aio_pika.Channel, queue_name: str, callback):
    """Consumes messages from a queue and calls the callback function."""
    queue = await channel.declare_queue(queue_name, durable=True)
    cprint(f"👂 Listening for messages on '{queue_name}'...", 'cyan')
    await queue.consume(callback)