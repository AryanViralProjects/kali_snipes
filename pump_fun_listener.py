# pump_fun_listener.py - Kali Speed Engine: Real-Time Pump.fun Detection
import asyncio
import json
import websockets
from termcolor import cprint
import dontshare as d
from raydium_listener import trigger_fast_snipe, get_helius_wss_url, get_transaction_details

# pump.fun Program ID
PUMP_FUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

async def process_new_pump_fun_token(signature):
    """
    Process a new token creation signature from pump.fun.
    The logic to extract token addresses from pump.fun transactions is different
    from Raydium, but we can use the same get_transaction_details as a starting point.
    """
    cprint(f"🔥 Kali Speed Engine: Processing new pump.fun signature: {signature}", 'magenta', attrs=['bold'])

    # get_transaction_details is generic enough to work here for extracting the new mint.
    # pump.fun 'create' transactions will clearly show the new mint address.
    base_token, _ = await get_transaction_details(signature)

    if base_token:
        cprint(f"💎 Kali Speed Engine: NEW PUMP.FUN TOKEN DETECTED!", 'white', 'on_magenta', attrs=['bold'])
        cprint(f"   Token Address: {base_token}", 'magenta')
        cprint(f"   Transaction: https://solscan.io/tx/{signature}", 'cyan')

        # Trigger the same fast sniping logic
        await trigger_fast_snipe(base_token, signature)
    else:
        cprint(f"⚠️ Kali Speed Engine: Could not extract token address from pump.fun tx {signature}", 'yellow')


async def listen_for_pump_fun():
    """
    Main WebSocket listener for pump.fun.
    Connects to Helius and listens for new token creations.
    """
    wss_url = get_helius_wss_url()
    if not wss_url:
        cprint("❌ pump.fun Listener: Cannot start without a valid WSS URL.", 'red')
        return

    cprint("🚀 Kali Speed Engine: Connecting to Helius for PUMP.FUN...", 'magenta', attrs=['bold'])

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [
            {"mentions": [PUMP_FUN_PROGRAM_ID]},
            {"commitment": "processed"}
        ]
    }

    while True:
        try:
            async with websockets.connect(wss_url) as websocket:
                await websocket.send(json.dumps(request))
                cprint("✅ Kali Speed Engine: Connected and subscribed to PUMP.FUN logs!", 'magenta', attrs=['bold'])

                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        if data.get("method") == "logsNotification":
                            logs = data.get("params", {}).get("result", {}).get("value", {}).get("logs", [])
                            
                            # pump.fun creation is often associated with 'Create' and 'Buy' instructions
                            if any("Instruction: Create" in log for log in logs):
                                signature = data.get("params", {}).get("result", {}).get("value", {}).get("signature")
                                if signature:
                                    # Use create_task to process without blocking the listener
                                    asyncio.create_task(process_new_pump_fun_token(signature))

                    except websockets.exceptions.ConnectionClosed:
                        cprint("🔄 pump.fun Listener: Connection closed, reconnecting...", 'yellow')
                        break # Break inner loop to trigger reconnection
                    except Exception as e:
                        cprint(f"⚠️ pump.fun Listener: Error processing message: {e}", 'yellow')
                        continue

        except Exception as e:
            cprint(f"❌ pump.fun Listener: WebSocket error: {e}. Retrying in 10 seconds...", 'red')
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(listen_for_pump_fun())
