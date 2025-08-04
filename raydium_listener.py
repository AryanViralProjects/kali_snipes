# raydium_listener.py - Kali Speed Engine: Real-Time Pool Detection
import asyncio
import json
import websockets
import requests
import base64
from termcolor import cprint
from datetime import datetime
import dontshare as d
import nice_funcs as n
from config import *

# Raydium Liquidity Pool V4 program ID
RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

# Convert Helius HTTP RPC to WebSocket URL
def get_helius_wss_url():
    """Convert Helius HTTP RPC URL to WebSocket URL"""
    http_url = d.rpc_url
    if "helius-rpc.com" in http_url:
        # Extract the API key from the HTTP URL
        if "?api-key=" in http_url:
            api_key = http_url.split("?api-key=")[1]
            wss_url = f"wss://mainnet.helius-rpc.com/?api-key={api_key}"
        else:
            # Fallback if URL structure is different
            wss_url = http_url.replace("https://", "wss://")
        return wss_url
    else:
        cprint("⚠️ Kali: Unable to convert RPC URL to WebSocket. Please check your Helius RPC URL.", 'red')
        return None

async def get_transaction_details(signature):
    """
    Fetch transaction details from signature and extract token addresses
    """
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        }
        
        response = requests.post(d.rpc_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'result' in data and data['result']:
                transaction = data['result']
                
                # Look for token accounts in the transaction
                base_token = None
                quote_token = None
                
                # Parse the transaction for new token mints
                if 'meta' in transaction and 'postTokenBalances' in transaction['meta']:
                    for balance in transaction['meta']['postTokenBalances']:
                        mint = balance.get('mint')
                        if mint and mint != USDC_CA and mint != "So11111111111111111111111111111111111111112":
                            base_token = mint
                            quote_token = USDC_CA  # Assume pairing with USDC
                            break
                
                return base_token, quote_token
                
    except Exception as e:
        cprint(f"❌ Kali Speed Engine: Error fetching transaction details: {e}", 'red')
        
    return None, None

async def process_new_pool(signature):
    """
    Process new pool detection and trigger fast trading logic
    """
    cprint(f"🔥 Kali Speed Engine: Processing new pool signature: {signature}", 'yellow', attrs=['bold'])
    
    # Get transaction details to extract token addresses
    base_token, quote_token = await get_transaction_details(signature)
    
    if base_token and quote_token:
        cprint(f"💎 Kali Speed Engine: NEW TOKEN DETECTED!", 'white', 'on_green', attrs=['bold'])
        cprint(f"   Base Token: {base_token}", 'green')
        cprint(f"   Quote Token: {quote_token}", 'green')
        cprint(f"   Transaction: https://solscan.io/tx/{signature}", 'cyan')
        
        # Trigger ULTRA-FAST trading sequence
        await trigger_fast_snipe(base_token, signature)
    else:
        cprint(f"⚠️ Kali Speed Engine: Could not extract token addresses from {signature}", 'yellow')

async def trigger_fast_snipe(token_address, signature):
    """
    🧠 INTELLIGENCE-POWERED FAST SNIPE: Combines speed with advanced vetting
    """
    cprint(f"⚡ Kali Speed Engine: INTELLIGENCE SNIPE INITIATED for {token_address[-6:]}", 'white', 'on_red', attrs=['bold'])
    
    try:
        # === INTELLIGENCE ENGINE VETTING ===
        cprint(f"🧠 Kali Intelligence: Running comprehensive vetting pipeline...", 'white', 'on_blue', attrs=['bold'])
        
        # Run the comprehensive intelligence vetting
        is_safe = n.pre_trade_token_vetting(token_address, d.birdeye, d.rpc_url)
        
        if not is_safe:
            cprint(f"🚫 Kali Intelligence: Token {token_address[-6:]} REJECTED by intelligence engine", 'red', attrs=['bold'])
            
            # Log rejected tokens for analysis
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open('./data/intelligence_rejections.txt', 'a') as f:
                f.write(f'{timestamp},{token_address},{signature},INTELLIGENCE_REJECTED\n')
            return
        
        # === INTELLIGENCE APPROVED - EXECUTE DYNAMIC ULTRA-FAST BUY ===
        cprint(f"🎯 Kali Intelligence: Token {token_address[-6:]} APPROVED! Executing DYNAMIC ULTRA-FAST BUY", 'white', 'on_green', attrs=['bold'])
        
        # === DYNAMIC STRATEGY: GET LIQUIDITY FOR OPTIMAL SIZING ===
        cprint(f"📊 Kali Speed + Strategy: Fetching liquidity for dynamic sizing...", 'cyan')
        token_overview = n.get_token_overview(token_address)
        
        if token_overview and token_overview.get('liquidity', 0) > 0:
            liquidity = token_overview.get('liquidity', 0)
            dynamic_size = n.calculate_dynamic_position_size(token_address, liquidity)
            usdc_amount_lamports = int(dynamic_size * 1000000)  # Convert to lamports
            
            cprint(f"⚡ Kali Speed Strategy: Dynamic sizing applied", 'white', 'on_cyan', attrs=['bold'])
            cprint(f"   Liquidity: ${liquidity:,.0f} → Size: ${dynamic_size:.2f} USDC", 'cyan')
        else:
            cprint(f"⚠️ Kali Speed Strategy: No liquidity data, using fallback size", 'yellow')
            dynamic_size = USDC_SIZE
            usdc_amount_lamports = int(USDC_SIZE * 1000000)  # Fallback to fixed size
            liquidity = 0
        
        # Import required modules for fast execution
        from solders.keypair import Keypair
        from solana.rpc.api import Client
        
        # Initialize keypair and client for ultra-fast execution
        keypair = Keypair.from_base58_string(d.sol_key)
        http_client = Client(d.rpc_url)
        
        # Execute the ultra-fast market buy
        success = n.market_buy_fast(token_address, usdc_amount_lamports, keypair, http_client)
        
        if success:
            cprint(f"✅ Kali Speed + Strategy Engine: DYNAMIC FAST SNIPE SUCCESSFUL! 🚀", 'white', 'on_green', attrs=['bold'])
            cprint(f"💎 Token: {token_address[-6:]} | Size: ${dynamic_size:.2f} | TX: {success[:8]}...", 'green', attrs=['bold'])
            
            # === DYNAMIC STRATEGY: RECORD POSITION FOR TIERED MANAGEMENT ===
            n.record_new_position(token_address, dynamic_size, liquidity)
            
            # Add to closed positions to prevent re-entry
            with open(CLOSED_POSITIONS_TXT, 'a') as f:
                f.write(f'{token_address}\n')
                
            # Log the successful snipe with dynamic size info
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open('./data/speed_engine_snipes.txt', 'a') as f:
                f.write(f'{timestamp},{token_address},{signature},SUCCESS,${dynamic_size:.2f},${liquidity:.0f}\n')
        else:
            cprint(f"❌ Kali Speed Engine: Fast snipe failed for {token_address[-6:]}", 'red')
            
    except Exception as e:
        cprint(f"❌ Kali Speed Engine: Error in fast snipe: {e}", 'red')

async def listen_for_new_pools():
    """
    Main WebSocket listener - connects to Helius and listens for new Raydium pools
    """
    wss_url = get_helius_wss_url()
    if not wss_url:
        return
        
    cprint("🚀 Kali Speed Engine: Connecting to Helius WebSocket...", 'cyan', attrs=['bold'])
    
    # WebSocket subscription request for Raydium program logs
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [
            {"mentions": [RAYDIUM_LP_V4]},
            {"commitment": "processed"}  # Use 'processed' for fastest detection
        ]
    }

    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with websockets.connect(wss_url) as websocket:
                await websocket.send(json.dumps(request))
                cprint("✅ Kali Speed Engine: Connected and subscribed to Raydium logs!", 'green', attrs=['bold'])
                cprint("🔍 Kali Speed Engine: Monitoring for new pool creations...", 'cyan')
                
                retry_count = 0  # Reset retry count on successful connection

                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        # Check if it's a log notification
                        if data.get("method") == "logsNotification":
                            logs = data.get("params", {}).get("result", {}).get("value", {}).get("logs", [])
                            
                            # Look for "initialize2" instruction which indicates new pool creation
                            if any("initialize2" in log for log in logs):
                                signature = data.get("params", {}).get("result", {}).get("value", {}).get("signature")
                                
                                if signature:
                                    cprint(f"🔥 NEW RAYDIUM POOL DETECTED! Signature: {signature}", 'yellow', attrs=['bold'])
                                    
                                    # Process immediately without waiting
                                    asyncio.create_task(process_new_pool(signature))

                    except websockets.exceptions.ConnectionClosed:
                        cprint("🔄 Kali Speed Engine: Connection closed, attempting to reconnect...", 'yellow')
                        break
                    except json.JSONDecodeError as e:
                        cprint(f"⚠️ Kali Speed Engine: JSON decode error: {e}", 'yellow')
                        continue
                    except Exception as e:
                        cprint(f"⚠️ Kali Speed Engine: Message processing error: {e}", 'yellow')
                        continue

        except websockets.exceptions.InvalidURI:
            cprint("❌ Kali Speed Engine: Invalid WebSocket URI. Check your Helius RPC configuration.", 'red')
            break
        except websockets.exceptions.WebSocketException as e:
            retry_count += 1
            cprint(f"🔄 Kali Speed Engine: WebSocket error (attempt {retry_count}/{max_retries}): {e}", 'yellow')
            await asyncio.sleep(5 * retry_count)  # Exponential backoff
        except Exception as e:
            retry_count += 1
            cprint(f"❌ Kali Speed Engine: Unexpected error (attempt {retry_count}/{max_retries}): {e}", 'red')
            await asyncio.sleep(5 * retry_count)

    cprint("❌ Kali Speed Engine: Max retries reached. WebSocket listener stopped.", 'red')

def start_speed_engine():
    """
    Start the Speed Engine WebSocket listener
    """
    cprint("🚀 KALI SPEED ENGINE STARTING...", 'white', 'on_blue', attrs=['bold'])
    cprint("⚡ Transitioning from minutes to MILLISECONDS!", 'white', 'on_blue', attrs=['bold'])
    
    try:
        asyncio.run(listen_for_new_pools())
    except KeyboardInterrupt:
        cprint("\n⏹️ Kali Speed Engine: Shutting down gracefully...", 'yellow')
    except Exception as e:
        cprint(f"❌ Kali Speed Engine: Fatal error: {e}", 'red')

if __name__ == "__main__":
    start_speed_engine()