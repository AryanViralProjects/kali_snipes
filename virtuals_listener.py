# virtuals_listener.py - Kali Speed Engine: Real-Time Virtuals.io Detection
import asyncio
import json
import websockets
from termcolor import cprint
import dontshare as d
from raydium_listener import trigger_fast_snipe, get_helius_wss_url, get_transaction_details

# NOTE: virtuals.io uses a factory pattern. This is a known, related program ID.
# You may need to do on-chain analysis on Solscan to find the most up-to-date
# factory or router address that signals a new agent token creation.
VIRTUALS_IO_PROGRAM_ID = "CJsL3g2VLd22TV1eMHS8r9n32Z3s1g6f3sBw6v8o8f9p" # Example: A known Virtuals Protocol address

async def process_new_virtuals_token(signature):
    """
    Process a new token creation signature from virtuals.io.
    """
    cprint(f"🔥 Kali Speed Engine: Processing new virtuals.io signature: {signature}", 'blue', attrs=['bold'])

    # The same generic transaction parser should work here as well.
    base_token, _ = await get_transaction_details(signature)

    if base_token:
        cprint(f"💎 Kali Speed Engine: NEW VIRTUALS.IO TOKEN DETECTED!", 'white', 'on_blue', attrs=['bold'])
        cprint(f"   Token Address: {base_token}", 'blue')
        cprint(f"   Transaction: https://solscan.io/tx/{signature}", 'cyan')

        # Trigger the same fast sniping logic
        await trigger_fast_snipe(base_token, signature)
    else:
        cprint(f"⚠️ Kali Speed Engine: Could not extract token address from virtuals.io tx {signature}", 'yellow')


async def listen_for_virtuals():
    """
    Main WebSocket listener for virtuals.io.
    """
    wss_url = get_helius_wss_url()
    if not wss_url:
        cprint("❌ virtuals.io Listener: Cannot start without a valid WSS URL.", 'red')
        return

    cprint("🚀 Kali Speed Engine: Connecting to Helius for VIRTUALS.IO...", 'blue', attrs=['bold'])

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [
            {"mentions": [VIRTUALS_IO_PROGRAM_ID]},
            {"commitment": "processed"}
        ]
    }

    while True:
        try:
            async with websockets.connect(wss_url) as websocket:
                await websocket.send(json.dumps(request))
                cprint("✅ Kali Speed Engine: Connected and subscribed to VIRTUALS.IO logs!", 'blue', attrs=['bold'])

                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        if data.get("method") == "logsNotification":
                            # The specific log message for a new agent token on virtuals.io
                            # needs to be identified by observing on-chain transactions.
                            # We'll use a generic check for now.
                            signature = data.get("params", {}).get("result", {}).get("value", {}).get("signature")
                            if signature:
                                # Use create_task to process without blocking the listener
                                asyncio.create_task(process_new_virtuals_token(signature))

                    except websockets.exceptions.ConnectionClosed:
                        cprint("🔄 virtuals.io Listener: Connection closed, reconnecting...", 'yellow')
                        break # Break inner loop to trigger reconnection
                    except Exception as e:
                        cprint(f"⚠️ virtuals.io Listener: Error processing message: {e}", 'yellow')
                        continue

        except Exception as e:
            cprint(f"❌ virtuals.io Listener: WebSocket error: {e}. Retrying in 10 seconds...", 'red')
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(listen_for_virtuals())
