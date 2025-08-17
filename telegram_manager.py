import asyncio
import telegram
import dontshare as d
from termcolor import cprint

def send_telegram_alert(message: str):
    """
    Sends a formatted message to your Telegram account via the bot.
    Handles missing credentials gracefully.
    """
    try:
        bot_token = getattr(d, 'telegram_bot_token', None)
        chat_id = getattr(d, 'telegram_chat_id', None)

        if not bot_token or not chat_id:
            # This check prevents crashes if credentials aren't set.
            # The bot will still run, just without alerts.
            cprint("⚠️ Telegram alerts disabled: Credentials not found in dontshare.py", 'yellow')
            return

        # Create and run async function
        async def send_message():
            bot = telegram.Bot(token=bot_token)
            # Send the message using MarkdownV2 for rich formatting.
            # Note: MarkdownV2 requires special characters like '.', '-', '(', ')' to be escaped with a '\'.
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='MarkdownV2'
            )
        
        # Run the async function
        asyncio.run(send_message())
        cprint(f"✅ Telegram alert sent successfully!", 'green')

    except Exception as e:
        cprint(f"❌ Failed to send Telegram alert: {e}", 'red')
        # Log the problematic message for debugging
        cprint(f"   -> Failed message content: {message}", 'yellow')