# raydium_listener.py - Kali Speed Engine: Real-Time Pool Detection
import asyncio
import json
import time
import websockets
import requests
import base64
import os
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
    Enhanced with retry logic for ultra-fast detection
    """
    max_retries = 5
    retry_delay = 0.5  # Start with 500ms delay
    
    for attempt in range(max_retries):
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    signature,
                    {
                        "encoding": "jsonParsed",
                        "maxSupportedTransactionVersion": 0,
                        "commitment": "confirmed"  # Wait for confirmed status
                    }
                ]
            }
            
            response = requests.post(d.rpc_url, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if transaction is found and confirmed
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
                    
                    # Also check preTokenBalances for newly created tokens
                    if not base_token and 'meta' in transaction and 'preTokenBalances' in transaction['meta']:
                        # Look for tokens that appear in post but not in pre (newly created)
                        pre_mints = set()
                        post_mints = set()
                        
                        for balance in transaction['meta']['preTokenBalances']:
                            mint = balance.get('mint')
                            if mint:
                                pre_mints.add(mint)
                        
                        for balance in transaction['meta']['postTokenBalances']:
                            mint = balance.get('mint')
                            if mint:
                                post_mints.add(mint)
                        
                        # Find newly created tokens
                        new_tokens = post_mints - pre_mints
                        for token in new_tokens:
                            if token != USDC_CA and token != "So11111111111111111111111111111111111111112":
                                base_token = token
                                quote_token = USDC_CA
                                break
                    
                    if base_token:
                        cprint(f"✅ Kali Speed Engine: Token extracted on attempt {attempt + 1}", 'green')
                        return base_token, quote_token
                    else:
                        cprint(f"⚠️ Kali Speed Engine: No new token found in transaction (attempt {attempt + 1})", 'yellow')
                
                elif 'error' in data:
                    cprint(f"⚠️ Kali Speed Engine: RPC Error: {data['error']}", 'yellow')
                else:
                    cprint(f"⚠️ Kali Speed Engine: Transaction not found yet (attempt {attempt + 1})", 'yellow')
            else:
                cprint(f"⚠️ Kali Speed Engine: HTTP {response.status_code} (attempt {attempt + 1})", 'yellow')
                
        except Exception as e:
            cprint(f"⚠️ Kali Speed Engine: Error on attempt {attempt + 1}: {e}", 'yellow')
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
            retry_delay *= 1.5  # Increase delay each retry
    
    cprint(f"❌ Kali Speed Engine: Failed to extract tokens after {max_retries} attempts", 'red')
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
    🧠 INTELLIGENCE-POWERED FAST SNIPE: Now with SEQUENTIAL MODE
    """
    cprint(f"⚡ Kali Speed Engine: INTELLIGENCE SNIPE INITIATED for {token_address[-6:]}", 'white', 'on_red', attrs=['bold'])
    
    try:
        # === NEW: SEQUENTIAL MODE CHECK ===
        if ENABLE_SEQUENTIAL_MODE:
            if n.has_active_positions():
                position_count = n.get_active_position_count()
                cprint(f"🔒 Kali Sequential Mode: Skipping snipe - {position_count} active position(s)", 'yellow', attrs=['bold'])
                cprint(f"   Waiting for current position to close before new trades", 'cyan')
                
                # Log skipped opportunity for analysis
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open(SEQUENTIAL_SKIPPED_LOG, 'a') as f:
                    f.write(f'{timestamp},{token_address},{signature},SKIPPED_ACTIVE_POSITION\n')
                return
            
            # Clean up any closed positions before proceeding
            n.clean_closed_positions()
        
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
        
        # Ensure we have valid liquidity data (never None)
        liquidity = 0
        if token_overview and isinstance(token_overview, dict):
            liquidity = token_overview.get('liquidity', 0)
            # Double-check liquidity is a valid number
            if liquidity is None or not isinstance(liquidity, (int, float)):
                liquidity = 0
        
        # === FIXED SIZE STRATEGY: Always use $3 trades ===
        fixed_size = USDC_SIZE  # Always $3 as configured
        usdc_amount_lamports = int(fixed_size * 1000000)  # Convert to lamports
        
        cprint(f"💰 Kali Speed Strategy: Fixed sizing applied", 'white', 'on_cyan', attrs=['bold'])
        cprint(f"   Fixed trade size: ${fixed_size:.2f} USDC", 'cyan')
        if liquidity > 0:
            cprint(f"   Token liquidity: ${liquidity:,.0f}", 'cyan')
        
        # Import required modules for fast execution
        from solders.keypair import Keypair
        from solana.rpc.api import Client
        
        # Initialize keypair and client for ultra-fast execution
        keypair = n.create_keypair_from_key(d.sol_key)
        http_client = Client(d.rpc_url)
        
        # Execute the ultra-fast market buy
        success = n.market_buy_fast(token_address, usdc_amount_lamports, keypair, http_client)
        
        if success:
            cprint(f"✅ Kali Speed + Strategy Engine: FIXED FAST SNIPE SUCCESSFUL! 🚀", 'white', 'on_green', attrs=['bold'])
            cprint(f"💎 Token: {token_address[-6:]} | Size: ${fixed_size:.2f} | TX: {success[:8]}...", 'green', attrs=['bold'])
            
            # === STRATEGY: RECORD POSITION FOR TIERED MANAGEMENT ===
            cprint(f"📝 DEBUG: Calling record_new_position for {token_address[-6:]}", 'yellow')
            try:
                n.record_new_position(token_address, fixed_size, liquidity)
                cprint(f"✅ DEBUG: Position recording completed for {token_address[-6:]}", 'green')
            except Exception as record_error:
                cprint(f"❌ DEBUG: Failed to record position: {record_error}", 'red')
            
            # Add to closed positions to prevent re-entry
            with open(CLOSED_POSITIONS_TXT, 'a') as f:
                f.write(f'{token_address}\n')
                
            # Log the successful snipe with fixed size info
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open('./data/speed_engine_snipes.txt', 'a') as f:
                f.write(f'{timestamp},{token_address},{signature},SUCCESS,${fixed_size:.2f},${liquidity:.0f}\n')
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

                # Enhanced connection monitoring with keepalive
                last_ping = time.time()
                ping_interval = 30  # Send ping every 30 seconds
                
                while True:
                    try:
                        # Send periodic pings to keep connection alive
                        current_time = time.time()
                        if current_time - last_ping > ping_interval:
                            try:
                                await websocket.ping()
                                last_ping = current_time
                                cprint("📡 Kali Speed Engine: Keepalive ping sent", 'blue')
                            except Exception as ping_error:
                                cprint(f"⚠️ Kali Speed Engine: Ping failed: {ping_error}", 'yellow')
                                break
                        
                        # Wait for message with timeout to check for pings
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        except asyncio.TimeoutError:
                            # No message received, continue to check ping timing
                            continue
                            
                        data = json.loads(message)

                        # Check if it's a log notification
                        if data.get("method") == "logsNotification":
                            logs = data.get("params", {}).get("result", {}).get("value", {}).get("logs", [])
                            
                            # 🎯 FIXED: Look for ACTUAL Raydium pool creation patterns
                            # Based on live analysis of 2500+ transactions
                            pool_creation_patterns = [
                                "InitializeAccount3",    # Most common new pool pattern (65% of pools)
                                "InitializeAccount",     # Alternative pool pattern (35% of pools)
                                "initialize2",           # Legacy pattern (0% but kept for compatibility)
                            ]
                            
                            # Check for any of the valid pool creation patterns
                            is_pool_creation = False
                            for pattern in pool_creation_patterns:
                                for log in logs:
                                    if "Program log: Instruction:" in log and pattern in log:
                                        is_pool_creation = True
                                        break
                                if is_pool_creation:
                                    break
                            
                            if is_pool_creation:
                                signature = data.get("params", {}).get("result", {}).get("value", {}).get("signature")
                                
                                if signature:
                                    # Additional validation: Check if we already processed this signature
                                    processed_signatures_file = './data/processed_signatures.txt'
                                    try:
                                        # Load already processed signatures
                                        if os.path.exists(processed_signatures_file):
                                            with open(processed_signatures_file, 'r') as f:
                                                processed_signatures = set(line.strip() for line in f.readlines())
                                        else:
                                            processed_signatures = set()
                                        
                                        # Skip if already processed
                                        if signature in processed_signatures:
                                            cprint(f"⚠️ Kali Speed Engine: Signature {signature[:8]}... already processed, skipping", 'yellow')
                                            continue
                                        
                                        # Add to processed list
                                        with open(processed_signatures_file, 'a') as f:
                                            f.write(f"{signature}\n")
                                            
                                    except Exception as sig_error:
                                        cprint(f"⚠️ Kali Speed Engine: Error managing signature tracking: {sig_error}", 'yellow')
                                    
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