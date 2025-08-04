import json 
import time 
import pandas as pd
import requests
import dontshare as d
from termcolor import cprint
from config import * 
import math
import ccxt
import base64
import json
import os
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc.types import TxOpts, Commitment 

def get_sol_balance(wallet_address):
    """
    Get SOL balance using Helius RPC (more reliable than Birdeye wallet endpoints)
    Returns tuple of (amount, usd_value) or (None, None) if failed
    """
    try:
        # Get SOL balance from Helius RPC
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address]
        }
        
        response = requests.post(d.rpc_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                sol_amount = data['result']['value'] / 1000000000  # Convert lamports to SOL
                
                # Get SOL price from Birdeye (this endpoint works with basic API)
                price_url = "https://public-api.birdeye.so/defi/price?address=So11111111111111111111111111111111111111112"
                price_headers = {"X-API-KEY": d.birdeye}
                price_response = requests.get(price_url, headers=price_headers)
                
                usd_value = None
                if price_response.status_code == 200:
                    price_data = price_response.json()
                    if price_data.get('success'):
                        sol_price = price_data.get('data', {}).get('value', 0)
                        usd_value = sol_amount * sol_price
                
                return sol_amount, usd_value
        
        return None, None
    except Exception as e:
        cprint(f"⚠️ Kali: Error getting SOL balance: {str(e)}", 'white', 'on_red')
        return None, None

def ask_bid(token_mint_address):

    ''' this returns the price '''

    API_KEY = d.birdeye
    
    url = f"https://public-api.birdeye.so/defi/price?address={token_mint_address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        json_response = response.json()  # Parse the JSON response
        if 'data' in json_response and 'value' in json_response['data']:
            return json_response['data']['value']  # Return the price value
        else:
            return "Price information not available"  # Return a message if 'data' or 'value' is missing
    else:
        return None  # Return None if there's an error with the API call

def security_check(address):
    '''
    Security check using upgraded Birdeye API
    Returns comprehensive security data including:
    - Freeze authority, top holder %, mutable metadata, token type
    '''

    API_KEY = d.birdeye

    url = f"https://public-api.birdeye.so/defi/token_security?address={address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        security_data = response.json()  # Return the JSON response if the call is successful
        if security_data and 'data' in security_data:
            # Check if the token is freezeable (has freeze authority)
            if security_data['data'].get('freezeable', False):
                print(f"* {address[-4:]} is freezeable. Dropping.")
                return None  # Return None to indicate the token should be dropped
        return security_data
    else:
        print(f"* {address[-4:]} security check failed (HTTP {response.status_code}). Dropping.")
        return None  # Return None if there's an error with the API call


def pre_trade_token_vetting(token_address, birdeye_api_key, helius_rpc_url):
    """
    🧠 KALI INTELLIGENCE ENGINE: Performs rapid, pre-trade analysis of a token.
    
    This function combines security checks, liquidity analysis, and deployer history
    to instantly filter out scams and low-quality tokens before execution.
    
    Returns True if the token passes all checks, False otherwise.
    """
    cprint(f"🔬 Kali Intelligence: Vetting token {token_address[-6:]}", 'yellow', attrs=['bold'])

    # === Birdeye Security Check ===
    try:
        sec_url = f"https://public-api.birdeye.so/defi/token_security?address={token_address}"
        sec_headers = {"X-API-KEY": birdeye_api_key}
        sec_response = requests.get(sec_url, headers=sec_headers, timeout=5)
        
        if sec_response.status_code != 200:
            cprint(f"   🚨 VETTING FAILED: Birdeye security API error (Code: {sec_response.status_code})", 'red')
            return False
            
        security_data = sec_response.json().get('data', {})
        if not security_data:
            cprint("   🚨 VETTING FAILED: No security data returned from Birdeye", 'red')
            return False

        # --- Critical Security Filters ---
        if security_data.get('isToken2022'):
            cprint("   🚨 VETTING FAILED: Token 2022 Program detected", 'red')
            return False

        if security_data.get('mutableMetadata'):
            cprint("   🚨 VETTING FAILED: Metadata is mutable", 'red')
            return False

        if security_data.get('freezeAuthority') is not None:
            cprint("   🚨 VETTING FAILED: Token is freezable", 'red')
            return False
        
        top_10_pct = security_data.get('top10HolderPercent', 1.0)
        if top_10_pct > MAX_TOP10_HOLDER_PERCENT:
            cprint(f"   🚨 VETTING FAILED: Top 10 holders have {top_10_pct:.2%} (>{MAX_TOP10_HOLDER_PERCENT:.1%})", 'red')
            return False
            
        cprint("   ✅ Security checks passed", 'green')
            
    except requests.exceptions.RequestException as e:
        cprint(f"   🚨 VETTING FAILED: Network error during security check: {e}", 'red')
        return False
        
    # === Birdeye Market Overview Check ===
    try:
        overview_url = f"https://public-api.birdeye.so/defi/token_overview?address={token_address}"
        overview_headers = {"X-API-KEY": birdeye_api_key}
        overview_response = requests.get(overview_url, headers=overview_headers, timeout=5)
        
        if overview_response.status_code != 200:
            cprint(f"   🚨 VETTING FAILED: Birdeye overview API error (Code: {overview_response.status_code})", 'red')
            return False
        
        overview_data = overview_response.json().get('data', {})
        if not overview_data:
            cprint("   🚨 VETTING FAILED: No overview data returned from Birdeye", 'red')
            return False
            
        liquidity = overview_data.get('liquidity', 0)
        market_cap = overview_data.get('mc', 0)
        
        # --- Market Quality Checks ---
        if liquidity < MIN_LIQUIDITY:
            cprint(f"   🚨 VETTING FAILED: Insufficient liquidity (${liquidity:,.2f} < ${MIN_LIQUIDITY:,.2f})", 'red')
            return False
            
        if market_cap > MAX_MARKET_CAP:
            cprint(f"   🚨 VETTING FAILED: Market cap too high (${market_cap:,.2f} > ${MAX_MARKET_CAP:,.2f})", 'red')
            return False

        cprint(f"   ✅ Market checks passed (Liquidity: ${liquidity:,.0f}, MC: ${market_cap:,.0f})", 'green')

    except requests.exceptions.RequestException as e:
        cprint(f"   🚨 VETTING FAILED: Network error during overview check: {e}", 'red')
        return False

    # === Deployer History Check ===
    deployer = get_deployer_address(token_address, birdeye_api_key)
    if check_deployer_blacklist(deployer):
        # The check_deployer_blacklist function already prints the reason
        return False

    if deployer:
        cprint(f"   ✅ Deployer check passed: {deployer[-6:]}", 'green')
    else:
        cprint("   ⚠️ Could not verify deployer (proceeding anyway)", 'yellow')

    cprint(f"   🎯 INTELLIGENCE VETTING PASSED: Token {token_address[-6:]} approved for trading!", 'white', 'on_green', attrs=['bold'])
    return True


def get_deployer_address(token_address, birdeye_api_key):
    """
    Gets the creator/deployer address of a token from Birdeye.
    Returns the deployer address or None if unavailable.
    """
    try:
        url = f"https://public-api.birdeye.so/defi/token_security?address={token_address}"
        headers = {"X-API-KEY": birdeye_api_key}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json().get('data', {})
            return data.get('creatorAddress') or data.get('deployer')
    except Exception as e:
        cprint(f"   ⚠️ Could not get deployer address: {e}", 'yellow')
    return None


def check_deployer_blacklist(deployer_address):
    """
    Checks if a deployer wallet is on the blacklist.
    Returns True if blacklisted, False otherwise.
    """
    if not deployer_address:
        return False  # Can't check a null address
        
    try:
        import os
        blacklist_file = './data/deployer_blacklist.txt'
        
        if not os.path.exists(blacklist_file):
            # Create empty blacklist file if it doesn't exist
            with open(blacklist_file, 'w') as f:
                f.write("# Deployer wallet blacklist - one address per line\n")
                f.write("# Format: wallet_address,reason\n")
            return False
        
        with open(blacklist_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Handle both formats: "address" or "address,reason"
                    blacklisted_address = line.split(',')[0].strip()
                    if deployer_address == blacklisted_address:
                        reason = line.split(',')[1].strip() if ',' in line else "blacklisted deployer"
                        cprint(f"   🚨 VETTING FAILED: Deployer {deployer_address[-6:]} is blacklisted ({reason})", 'red', attrs=['bold'])
                        return True
                        
    except Exception as e:
        cprint(f"   ⚠️ Error checking deployer blacklist: {e}", 'yellow')
        return False
        
    return False


def add_deployer_to_blacklist(deployer_address, reason="manual_add"):
    """
    Adds a deployer address to the blacklist with optional reason.
    """
    if not deployer_address:
        return
        
    try:
        import os
        blacklist_file = './data/deployer_blacklist.txt'
        
        # Check if already exists
        if check_deployer_blacklist(deployer_address):
            cprint(f"   ⚠️ Deployer {deployer_address[-6:]} already blacklisted", 'yellow')
            return
            
        # Create directory if it doesn't exist
        os.makedirs('./data', exist_ok=True)
        
        with open(blacklist_file, 'a') as f:
            f.write(f"{deployer_address},{reason}\n")
            
        cprint(f"   🚫 Added deployer {deployer_address[-6:]} to blacklist (reason: {reason})", 'red')
        
    except Exception as e:
        cprint(f"   ❌ Error adding deployer to blacklist: {e}", 'red')


def load_position_states():
    """
    🎯 KALI STRATEGY ENGINE: Loads the state of all open positions from JSON file.
    Returns dictionary with position states for tiered profit management.
    """
    try:
        if not os.path.exists(OPEN_POSITIONS_STATE_FILE):
            # Create empty state file if it doesn't exist
            os.makedirs('./data', exist_ok=True)
            with open(OPEN_POSITIONS_STATE_FILE, 'w') as f:
                json.dump({}, f, indent=4)
            return {}
            
        with open(OPEN_POSITIONS_STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        cprint(f"⚠️ Kali Strategy: Error loading position states: {e}", 'yellow')
        return {}


def save_position_states(states):
    """
    🎯 KALI STRATEGY ENGINE: Saves the state of all open positions to JSON file.
    """
    try:
        os.makedirs('./data', exist_ok=True)
        with open(OPEN_POSITIONS_STATE_FILE, 'w') as f:
            json.dump(states, f, indent=4)
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error saving position states: {e}", 'red')


def record_new_position(token_address, buy_size_usdc, liquidity=0):
    """
    🎯 KALI STRATEGY ENGINE: Records a new position in the state tracking system.
    Called immediately after a successful buy to enable tiered profit management.
    """
    try:
        states = load_position_states()
        
        if token_address not in states:
            states[token_address] = {
                "initial_investment_usdc": float(buy_size_usdc),
                "initial_liquidity": float(liquidity),
                "tiers_sold": [],  # List to track which profit tiers have been executed
                "entry_timestamp": time.time(),
                "total_sold_usdc": 0.0,  # Track total USDC received from sales
                "strategy_type": "tiered_dynamic"
            }
            save_position_states(states)
            
            cprint(f"📊 Kali Strategy: Position recorded - ${buy_size_usdc:.2f} into {token_address[-6:]}", 'white', 'on_green')
            cprint(f"   Entry LP: ${liquidity:,.0f} | Tiers: {len(SELL_TIERS)} levels", 'green')
        else:
            cprint(f"⚠️ Kali Strategy: Position {token_address[-6:]} already tracked", 'yellow')
            
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error recording position: {e}", 'red')


def update_position_tier_sold(token_address, tier_index, sell_amount_usdc):
    """
    🎯 KALI STRATEGY ENGINE: Records that a profit tier has been executed.
    """
    try:
        states = load_position_states()
        
        if token_address in states:
            if tier_index not in states[token_address]['tiers_sold']:
                states[token_address]['tiers_sold'].append(tier_index)
                states[token_address]['total_sold_usdc'] += float(sell_amount_usdc)
                save_position_states(states)
                
                tier_name = SELL_TIERS[tier_index]['name'] if tier_index < len(SELL_TIERS) else f"Tier {tier_index + 1}"
                cprint(f"💰 Kali Strategy: {tier_name} executed for {token_address[-6:]} (+${sell_amount_usdc:.2f})", 'white', 'on_green')
        else:
            cprint(f"⚠️ Kali Strategy: Position {token_address[-6:]} not found in tracking", 'yellow')
            
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error updating tier: {e}", 'red')


def remove_position_state(token_address):
    """
    🎯 KALI STRATEGY ENGINE: Removes a position's state upon full exit.
    Called when position is completely closed (stop-loss or final tier).
    """
    try:
        states = load_position_states()
        
        if token_address in states:
            # Log final performance before removal
            state = states[token_address]
            initial = state.get('initial_investment_usdc', 0)
            total_sold = state.get('total_sold_usdc', 0)
            tiers_executed = len(state.get('tiers_sold', []))
            
            profit_loss = total_sold - initial
            profit_percent = (profit_loss / initial * 100) if initial > 0 else 0
            
            cprint(f"📊 Kali Strategy: Closing {token_address[-6:]} | P&L: ${profit_loss:+.2f} ({profit_percent:+.1f}%)", 'white', 'on_blue')
            cprint(f"   Tiers executed: {tiers_executed}/{len(SELL_TIERS)} | Total sold: ${total_sold:.2f}", 'blue')
            
            del states[token_address]
            save_position_states(states)
        else:
            cprint(f"⚠️ Kali Strategy: Position {token_address[-6:]} not found for removal", 'yellow')
            
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error removing position state: {e}", 'red')


def get_position_performance_summary():
    """
    🎯 KALI STRATEGY ENGINE: Get summary of all tracked positions.
    """
    try:
        states = load_position_states()
        if not states:
            return "No positions currently tracked"
            
        summary = []
        total_invested = 0
        total_current_value = 0
        
        for token, state in states.items():
            initial = state.get('initial_investment_usdc', 0)
            sold = state.get('total_sold_usdc', 0)
            tiers = len(state.get('tiers_sold', []))
            
            total_invested += initial
            total_current_value += sold  # Simplified - would need current position value
            
            summary.append(f"{token[-6:]}: ${initial:.1f} → ${sold:.1f} ({tiers}/{len(SELL_TIERS)} tiers)")
            
        return f"Positions: {len(states)} | Invested: ${total_invested:.1f} | " + " | ".join(summary[:3])
        
    except Exception as e:
        return f"Error getting summary: {e}"


def calculate_dynamic_position_size(token_address, liquidity):
    """
    🎯 KALI STRATEGY ENGINE: Calculate optimal position size based on liquidity.
    Returns the USDC amount to spend based on dynamic sizing rules.
    """
    try:
        if not ENABLE_DYNAMIC_SIZING:
            cprint(f"📏 Kali Strategy: Dynamic sizing disabled, using fixed size ${USDC_SIZE}", 'cyan')
            return USDC_SIZE
            
        if liquidity <= 0:
            cprint(f"⚠️ Kali Strategy: Invalid liquidity ({liquidity}), using minimum size", 'yellow')
            return USDC_MIN_BUY_SIZE
            
        # Calculate target size as percentage of liquidity
        target_size = liquidity * USDC_BUY_TARGET_PERCENT_OF_LP
        
        # Clamp between min and max bounds
        actual_size = max(USDC_MIN_BUY_SIZE, min(target_size, USDC_MAX_BUY_SIZE))
        
        # Calculate what percentage of LP this represents
        lp_percentage = (actual_size / liquidity) * 100
        
        cprint(f"📏 Kali Strategy: Dynamic sizing for {token_address[-6:]}", 'white', 'on_cyan', attrs=['bold'])
        cprint(f"   Liquidity: ${liquidity:,.0f} | Target: ${target_size:.2f} | Actual: ${actual_size:.2f}", 'cyan')
        cprint(f"   LP Impact: {lp_percentage:.3f}% | Size factor: {actual_size/USDC_SIZE:.2f}x", 'cyan')
        
        return actual_size
        
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error calculating dynamic size: {e}", 'red')
        return USDC_MIN_BUY_SIZE


def execute_tiered_sell(token_address, tier_index, current_position_value):
    """
    🎯 KALI STRATEGY ENGINE: Execute a specific tier of the profit-taking strategy.
    Sells a portion of the current holdings based on the tier configuration.
    """
    try:
        if tier_index >= len(SELL_TIERS):
            cprint(f"⚠️ Kali Strategy: Invalid tier index {tier_index}", 'yellow')
            return False
            
        tier = SELL_TIERS[tier_index]
        tier_name = tier['name']
        sell_portion = tier['sell_portion']
        
        cprint(f"💰 Kali Strategy: Executing {tier_name} (Tier {tier_index + 1})", 'white', 'on_green', attrs=['bold'])
        cprint(f"   Selling {sell_portion * 100:.0f}% of current position", 'green')
        
        # Get current token balance
        current_balance = get_position(token_address)
        if current_balance <= 0:
            cprint(f"⚠️ Kali Strategy: No position found for {token_address[-6:]}", 'yellow')
            return False
            
        # Calculate amount to sell (portion of current balance)
        sell_amount = current_balance * sell_portion
        
        # Get token decimals and convert to proper format
        decimals = get_decimals(token_address)
        sell_amount_lamports = int(sell_amount * (10 ** decimals))
        
        cprint(f"📊 Kali Strategy: Tier details for {token_address[-6:]}", 'cyan')
        cprint(f"   Current balance: {current_balance:.4f} tokens", 'cyan')
        cprint(f"   Selling: {sell_amount:.4f} tokens ({sell_amount_lamports:,} lamports)", 'cyan')
        cprint(f"   Position value: ${current_position_value:.2f}", 'cyan')
        
        # Execute the market sell
        try:
            market_sell(token_address, sell_amount_lamports)
            
            # Calculate estimated USDC received (approximate)
            price = ask_bid(token_address)
            estimated_usdc = sell_amount * price if price else 0
            
            # Record the tier execution
            update_position_tier_sold(token_address, tier_index, estimated_usdc)
            
            cprint(f"✅ Kali Strategy: {tier_name} executed successfully!", 'white', 'on_green', attrs=['bold'])
            cprint(f"   Estimated USDC received: ${estimated_usdc:.2f}", 'green')
            
            return True
            
        except Exception as sell_error:
            cprint(f"❌ Kali Strategy: Tier sell execution failed: {sell_error}", 'red')
            return False
            
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error in tiered sell: {e}", 'red')
        return False


def advanced_pnl_management():
    """
    🎯 KALI STRATEGY ENGINE: Advanced PNL management with tiered exits and tight stop-losses.
    
    This replaces the old simple PNL system with sophisticated profit-taking:
    - Dynamic stop-losses (-25% instead of -60%)
    - Multi-tier profit taking (2x, 5x, 11x multipliers)
    - Position state tracking
    - Intelligent exit strategies
    """
    if not ENABLE_TIERED_EXITS:
        cprint("📈 Kali Strategy: Tiered exits disabled, using legacy PNL", 'cyan')
        return
        
    cprint("📈 Kali Strategy Engine: Running Advanced PNL Management", 'white', 'on_blue', attrs=['bold'])
    
    try:
        # Get current wallet holdings
        open_positions_df = fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
        position_states = load_position_states()
        
        if open_positions_df.empty and not position_states:
            cprint("📊 Kali Strategy: No positions to manage", 'cyan')
            return
            
        # Create wallet mints set for quick lookup
        wallet_mints = set(open_positions_df['Mint Address']) if not open_positions_df.empty else set()
        
        # Clean up state for positions no longer in wallet
        for mint in list(position_states.keys()):
            if mint not in wallet_mints:
                cprint(f'👻 Kali Strategy: Position {mint[-6:]} no longer in wallet, removing from tracking', 'yellow')
                remove_position_state(mint)
                continue
                
        # Process each tracked position
        positions_processed = 0
        for mint, state in list(position_states.items()):
            if mint not in wallet_mints:
                continue
                
            positions_processed += 1
            
            # Get current position data
            position_row = open_positions_df[open_positions_df['Mint Address'] == mint].iloc[0]
            current_usd_value = position_row['USD Value']
            initial_investment = state['initial_investment_usdc']
            tiers_sold = state.get('tiers_sold', [])
            
            cprint(f"\n🔍 Kali Strategy: Analyzing {mint[-6:]} (${current_usd_value:.2f})", 'white', 'on_cyan')
            
            # === 1. STOP-LOSS CHECK (HIGHEST PRIORITY) ===
            stop_loss_value = initial_investment * (1 + STOP_LOSS_PERCENTAGE)
            
            if current_usd_value < stop_loss_value:
                cprint(f'🚨 Kali Strategy: STOP-LOSS triggered for {mint[-6:]}!', 'white', 'on_red', attrs=['bold'])
                cprint(f'   Value: ${current_usd_value:.2f} < SL: ${stop_loss_value:.2f}', 'red')
                cprint(f'   Loss: ${current_usd_value - initial_investment:.2f} ({((current_usd_value / initial_investment - 1) * 100):+.1f}%)', 'red')
                
                # Execute full exit
                kill_switch(mint)
                remove_position_state(mint)
                continue
                
            # === 2. TIERED TAKE-PROFIT CHECK ===
            for tier_index, tier in enumerate(SELL_TIERS):
                tier_profit_value = initial_investment * tier['profit_multiple']
                tier_name = tier['name']
                
                # Check if we hit this tier and haven't sold it yet
                if current_usd_value >= tier_profit_value and tier_index not in tiers_sold:
                    profit_percent = ((current_usd_value / initial_investment) - 1) * 100
                    
                    cprint(f'🎯 Kali Strategy: {tier_name} HIT for {mint[-6:]}!', 'white', 'on_green', attrs=['bold'])
                    cprint(f'   Value: ${current_usd_value:.2f} > Target: ${tier_profit_value:.2f}', 'green')
                    cprint(f'   Profit: ${current_usd_value - initial_investment:.2f} ({profit_percent:+.1f}%)', 'green')
                    
                    # Execute the tier sell
                    success = execute_tiered_sell(mint, tier_index, current_usd_value)
                    
                    if success:
                        # Check if this was the final tier or if we should close remaining position
                        if tier_index == len(SELL_TIERS) - 1:  # Last tier
                            cprint(f'🏆 Kali Strategy: Final tier executed for {mint[-6:]}, closing remaining position', 'white', 'on_gold')
                            kill_switch(mint)  # Close remaining position
                            remove_position_state(mint)
                            break
                    else:
                        cprint(f'⚠️ Kali Strategy: Tier execution failed for {mint[-6:]}, will retry next cycle', 'yellow')
                        
                    # Only execute one tier per cycle per position
                    break
                    
        if positions_processed > 0:
            cprint(f"📊 Kali Strategy: Processed {positions_processed} positions", 'white', 'on_blue')
            # Show position summary
            summary = get_position_performance_summary()
            cprint(f"   {summary}", 'blue')
        else:
            cprint("📊 Kali Strategy: No tracked positions found", 'cyan')
            
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error in advanced PNL management: {e}", 'red')


def extract_urls(description):
    urls = {'twitter': None, 'website': None, 'telegram': None}
    if description and description != "[]":
        try:
            # Assuming the description is a string representation of a list of dicts
            links = json.loads(description.replace("'", '"'))
            for link in links:
                for key, value in link.items():
                    if 'twitter' in key or 'twitter.com' in value or 'x.com' in value:
                        urls['twitter'] = value
                    elif 'telegram' in key:
                        urls['telegram'] = value
                    elif 'website' in key:
                        # Assuming any other link that doesn't include 't.me' is a website
                        if 't.me' not in value:
                            urls['website'] = value
        except json.JSONDecodeError:
            print(f"Error decoding JSON from description: {description}")
    return urls


def get_token_overview(address):
    API_KEY = d.birdeye
    url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        json_response = response.json()
        return json_response['data']
    else:
        # Return empty dict if there's an error
        print(f"Error fetching data for address {address}: {response.status_code}")
        return {}
    

def get_names_nosave(df):
    names = []  # List to hold the collected names

    for index, row in df.iterrows():
        token_mint_address = row['Mint Address']
        token_data = get_token_overview(token_mint_address)
        
        # Extract the token name using the 'name' key from the token_data
        token_name = token_data.get('name', 'N/A')  # Use 'N/A' if name isn't provided
        #print(f'Name for {token_mint_address[-4:]}: {token_name}')
        names.append(token_name)
    
    # Check if 'name' column already exists, update it if it does, otherwise insert it
    if 'name' in df.columns:
        df['name'] = names  # Update existing 'name' column
    else:
        df.insert(0, 'name', names)  # Insert 'name' as the first column

    # drop the Mint_Address
    df.drop('Mint Address', axis=1, inplace=True)
    df.drop('Amount', axis=1, inplace=True)

    #print(df)
    
    return df

def get_names(df):
    names = []  # List to hold the collected names

    for index, row in df.iterrows():
        token_mint_address = row['address']
        token_data = get_token_overview(token_mint_address)
        time.sleep(2)
        
        # Extract the token name using the 'name' key from the token_data
        token_name = token_data.get('name', 'N/A')  # Use 'N/A' if name isn't provided
        cprint(f'🌙 Kali: Token {token_name} at address: {token_mint_address}', 'white', 'on_cyan')
        names.append(token_name)
    
    # Check if 'name' column already exists, update it if it does, otherwise insert it
    if 'name' in df.columns:
        df['name'] = names  # Update existing 'name' column
    else:
        df.insert(0, 'name', names)  # Insert 'name' as the first column

    # Save df to vibe_check.csv
    df.to_csv(READY_TO_BUY_CSV, index=False)
    
    return df

def fetch_wallet_holdings_og(address):
    """
    Get wallet holdings using Helius RPC instead of Birdeye wallet endpoints
    Returns DataFrame with token holdings
    """
    # Initialize an empty DataFrame
    df = pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])

    try:
        # Get token accounts using Helius RPC
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        
        response = requests.post(d.rpc_url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'value' in data['result']:
                token_accounts = data['result']['value']
                
                holdings_data = []
                for account in token_accounts:
                    try:
                        parsed_info = account['account']['data']['parsed']['info']
                        mint_address = parsed_info['mint']
                        amount = float(parsed_info['tokenAmount']['uiAmount'] or 0)
                        
                        if amount > 0:  # Only include tokens with positive balance
                            # For now, set USD value to 0 - we can add price lookup later if needed
                            holdings_data.append({
                                'Mint Address': mint_address,
                                'Amount': amount,
                                'USD Value': 0.0  # Will be updated with prices if needed
                            })
                    except Exception as e:
                        continue  # Skip malformed token accounts
                
                if holdings_data:
                    df = pd.DataFrame(holdings_data)
                    df = df[df['Amount'] > 0]  # Filter out zero balances
                else:
                    cprint("✅ Kali: Wallet has no token holdings (only SOL)", 'white', 'on_cyan')
            else:
                cprint("❌ Kali: No token accounts found", 'white', 'on_red')
        else:
            cprint(f"❌ Kali: Failed to retrieve token accounts: HTTP {response.status_code}", 'white', 'on_red')
            
    except Exception as e:
        cprint(f"❌ Kali: Error fetching wallet holdings: {str(e)}", 'white', 'on_red')

    # Addresses to exclude from the "do not trade list"
    exclude_addresses = ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111112']

    # Update the "do not trade list" by removing the excluded addresses
    updated_dont_trade_list = [mint for mint in DO_NOT_TRADE_LIST if mint not in exclude_addresses]

    # Filter the dataframe
    for mint in updated_dont_trade_list:
        df = df[df['Mint Address'] != mint]

    # Print the DataFrame if it's not empty
    if not df.empty:
        df2 = get_names_nosave(df.copy())
        print('')
        print(df2.head(20))
        cprint(f'💰 Kali: Current Portfolio Value: ${round(df2["USD Value"].sum(),2)}', 'white', 'on_green')
        print(' ')
        time.sleep(7)
    else:
        cprint("❌ Kali: No wallet holdings to display.", 'white', 'on_red')
        time.sleep(30)

    return df

def fetch_wallet_token_single(address, token_mint_address):
    
    df = fetch_wallet_holdings_og(address)

    # filter by token mint address
    df = df[df['Mint Address'] == token_mint_address]

    return df


def get_position(token_mint_address):
    """
    Fetches the balance of a specific token given its mint address from a DataFrame.

    Parameters:
    - dataframe: A pandas DataFrame containing token balances with columns ['Mint Address', 'Amount'].
    - token_mint_address: The mint address of the token to find the balance for.

    Returns:
    - The balance of the specified token if found, otherwise a message indicating the token is not in the wallet.
    """
    dataframe = fetch_wallet_token_single(MY_SOLANA_ADDERESS, token_mint_address)

    #dataframe = pd.read_csv('data/token_per_addy.csv')

    print('-----------------')
    #print(dataframe)

    #print(dataframe)

    # Check if the DataFrame is empty
    if dataframe.empty:
        print("The DataFrame is empty. No positions to show.")
        time.sleep(5)
        return 0  # Indicating no balance found

    # Ensure 'Mint Address' column is treated as string for reliable comparison
    dataframe['Mint Address'] = dataframe['Mint Address'].astype(str)

    # Check if the token mint address exists in the DataFrame
    if dataframe['Mint Address'].isin([token_mint_address]).any():
        # Get the balance for the specified token
        balance = dataframe.loc[dataframe['Mint Address'] == token_mint_address, 'Amount'].iloc[0]
        #print(f"Balance for {token_mint_address[-4:]} token: {balance}")
        return balance
    else:
        # If the token mint address is not found in the DataFrame, return a message indicating so
        print("Token mint address not found in the wallet.")
        return 0  # Indicating no balance found



def get_bal_birdeye(address):

    API_KEY = d.birdeye

    print(f'getting balance for {address}...')
    url = f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={address}"

    headers = {"x-chain": "solana", "X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)

    #print(response.text)
    json_response = response.json()
    #print(json_response['data'])

    # output to a json in data folder
    with open('data/bal_birdeye.json', 'w') as f:
        json.dump(json_response, f)



def round_down(value, decimals):
    factor = 10 ** decimals
    return math.floor(value * factor) / factor


def get_decimals(token_mint_address):
    import requests
    import base64
    import json
    # Solana Mainnet RPC endpoint
    url = "https://api.mainnet-beta.solana.com/"
    
    headers = {"Content-Type": "application/json"}

    # Request payload to fetch account information
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [
            token_mint_address,
            {
                "encoding": "jsonParsed"
            }
        ]
    })

    # Make the request to Solana RPC
    response = requests.post(url, headers=headers, data=payload)
    response_json = response.json()

    # Parse the response to extract the number of decimals
    decimals = response_json['result']['value']['data']['parsed']['info']['decimals']
    #print(f"Decimals for {token_mint_address[-4:]} token: {decimals}")

    return decimals


def market_buy(token, amount, slippage=SLIPPAGE):
    import requests
    import sys
    import json
    import base64
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    import time

    import dontshare as d 

    KEY = Keypair.from_base58_string(d.sol_key)
    QUOTE_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # usdc

    http_client = Client(d.rpc_url)

    quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}&slippageBps={SLIPPAGE}&restrictIntermediateTokens=true'
    swap_url = 'https://quote-api.jup.ag/v6/swap'
    
    # Initialize counter for swap transaction errors
    swap_error_count = 0
    max_retries = 50
    
    while True:
        try:
            quote = requests.get(quote_url).json()

            txRes = requests.post(swap_url,
                                  headers={"Content-Type": "application/json"},
                                  data=json.dumps({
                                      "quoteResponse": quote,
                                      "userPublicKey": str(KEY.pubkey()),
                                      "prioritizationFeeLamports": PRIORITY_FEE  # Hardcoded fee
                                  })).json()
                                  
            if 'swapTransaction' not in txRes:
                swap_error_count += 1
                cprint(f'🚨 Kali: SwapTransaction error #{swap_error_count}/50 for token {token[-4:]}', 'white', 'on_red')
                
                if swap_error_count >= max_retries:
                    cprint(f'💀 Kali: Blacklisting token {token[-4:]} after {max_retries} swap transaction errors!', 'white', 'on_red')
                    # Add to permanent blacklist
                    with open(PERMANENT_BLACKLIST, 'a') as f:
                        f.write(f'{token}\n')
                    # Add to closed positions to prevent future attempts
                    with open(CLOSED_POSITIONS_TXT, 'a') as f:
                        f.write(f'{token}\n')
                    return False
                    
                time.sleep(2)  # Wait before retry
                continue
                
            swapTx = base64.b64decode(txRes['swapTransaction'])
            tx1 = VersionedTransaction.from_bytes(swapTx)
            tx = VersionedTransaction(tx1.message, [KEY])
            txId = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
            cprint(f"🌟 Kali: Transaction successful! https://solscan.io/tx/{str(txId)}", 'white', 'on_green')
            return True
            
        except requests.exceptions.RequestException as e:
            cprint(f"🔄 Kali: Request failed: {e}", 'white', 'on_red')
            time.sleep(5)
        except Exception as e:
            cprint(f"⚠️ Kali: An error occurred: {e}", 'white', 'on_red')
            time.sleep(5)


def market_buy_fast(token_to_buy, usdc_amount_in_lamports, keypair, http_client):
    """
    KALI SPEED ENGINE: Ultra-fast market buy using Jupiter's v6 API with millisecond-level optimizations.
    
    :param token_to_buy: The mint address of the token you want to buy.
    :param usdc_amount_in_lamports: The amount of USDC to spend, in lamports (e.g., 5 USDC = 5 * 10**6).
    :param keypair: The solders.keypair.Keypair object for your wallet.
    :param http_client: The solana.rpc.api.Client object.
    :return: The transaction signature string if successful, else None.
    """
    
    # USDC Mint Address
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    try:
        cprint(f"⚡ Kali Speed Engine: FAST BUY initiated for {token_to_buy[-6:]}", 'white', 'on_blue', attrs=['bold'])
        
        # 1. Get the quote with optimized parameters
        quote_url = (
            f"https://quote-api.jup.ag/v6/quote?"
            f"inputMint={usdc_mint}"
            f"&outputMint={token_to_buy}"
            f"&amount={usdc_amount_in_lamports}"
            f"&slippageBps=1000"  # 10% slippage for speed (can be adjusted)
            f"&onlyDirectRoutes=true"  # Use only direct routes for speed
            f"&excludeDexes=Whirlpool,Raydium%20CLMM"  # Exclude slower DEXes
        )
        
        quote_response = requests.get(quote_url, timeout=5).json()
        
        if 'error' in quote_response:
            cprint(f"🚨 Kali Speed Engine: Quote error for {token_to_buy[-6:]}: {quote_response.get('error')}", 'red')
            return None

        # 2. Get the swap transaction with high priority
        swap_url = 'https://quote-api.jup.ag/v6/swap'
        swap_payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(keypair.pubkey()),
            "wrapAndUnwrapSol": True,
            # CRITICAL: High priority fee for fastest inclusion
            "prioritizationFeeLamports": 50000,  # Higher than normal for speed
            "dynamicComputeUnitLimit": True,  # Optimize compute units
            "skipUserAccountsRpcCalls": True  # Skip unnecessary RPC calls for speed
        }
        
        swap_response = requests.post(swap_url, json=swap_payload, timeout=5).json()
        
        if 'swapTransaction' not in swap_response:
            cprint(f"🚨 Kali Speed Engine: Swap error for {token_to_buy[-6:]}: {swap_response.get('error', 'No swap transaction')}", 'red')
            return None

        # 3. Deserialize, sign, and send with MAXIMUM SPEED settings
        swap_tx_b64 = swap_response['swapTransaction']
        raw_tx = base64.b64decode(swap_tx_b64)
        versioned_tx = VersionedTransaction.from_bytes(raw_tx)
        
        # Sign the transaction with your keypair
        signed_tx = VersionedTransaction(versioned_tx.message, [keypair])

        # CRITICAL: Ultra-fast transmission settings
        # - skip_preflight=True: No simulation, direct to validator
        # - processed commitment: Fastest confirmation level
        opts = TxOpts(
            skip_preflight=True, 
            preflight_commitment=Commitment("processed"),
            max_retries=0  # No retries for speed
        )
        
        cprint(f"🚀 Kali Speed Engine: Transmitting transaction for {token_to_buy[-6:]}", 'yellow', attrs=['bold'])
        
        # Send transaction with ultra-fast settings
        tx_receipt = http_client.send_raw_transaction(bytes(signed_tx), opts=opts)
        tx_signature = tx_receipt.value
        
        cprint(f"✅ Kali Speed Engine: ULTRA-FAST BUY SUCCESS! 🚀", 'white', 'on_green', attrs=['bold'])
        cprint(f"💎 Token: {token_to_buy[-6:]} | TX: https://solscan.io/tx/{str(tx_signature)}", 'green', attrs=['bold'])
        
        return str(tx_signature)

    except requests.exceptions.Timeout:
        cprint(f"⏰ Kali Speed Engine: Request timeout for {token_to_buy[-6:]}", 'red')
        return None
    except requests.exceptions.RequestException as e:
        cprint(f"🔄 Kali Speed Engine: Request failed for {token_to_buy[-6:]}: {e}", 'red')
        return None
    except Exception as e:
        cprint(f"❌ Kali Speed Engine: Fast buy error for {token_to_buy[-6:]}: {e}", 'red')
        return None


def market_sell(QUOTE_TOKEN, amount, slippage=SLIPPAGE):

    import requests
    import json
    import base64
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    import dontshare as d 

    KEY = Keypair.from_base58_string(d.sol_key)
    token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # usdc

    http_client = Client(d.rpc_url)
    quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}'

    # Fixed minimum slippage
    min_slippage = 50

    quote = requests.get(quote_url).json()
    print(quote)
    
    # Post request to swap with dynamic slippage
    txRes = requests.post('https://quote-api.jup.ag/v6/swap',
                          headers={"Content-Type": "application/json"},
                          data=json.dumps({
                              "quoteResponse": quote,
                              "userPublicKey": str(KEY.pubkey()),
                              "prioritizationFeeLamports": PRIORITY_FEE,
                              "dynamicSlippage": {"minBps": min_slippage, "maxBps": slippage},
                          })).json() 
    print(txRes)

    swapTx = base64.b64decode(txRes['swapTransaction'])
    print(swapTx)
    tx1 = VersionedTransaction.from_bytes(swapTx)
    print(tx1)
    tx = VersionedTransaction(tx1.message, [KEY])
    print(tx)
    txId = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
    print(f"https://solscan.io/tx/{str(txId)}")



def kill_switch(token_mint_address):

    ''' this function closes the position in full  '''

    # if time is on the 5 minute do the balance check, if not grab from data/current_position.csv
    balance = get_position(token_mint_address)

    # get current price of token 
    price = ask_bid(token_mint_address)

    usd_value = balance * price

    tp = SELL_AT_MULTIPLE * USDC_SIZE
    sell_size = balance 
    # round to 2 decimals
    sell_size = round_down(sell_size, 2)
    decimals = 0
    decimals = get_decimals(token_mint_address)
    #print(f'for {token_mint_address[-4:]} decimals is {decimals}')

    sell_size = int(sell_size * 10 **decimals)
    
    #print(f'bal: {balance} price: {price} usdVal: {usd_value} TP: {tp} sell size: {sell_size} decimals: {decimals}')

    while usd_value > 0:

        # log this mint address to a file and save as a new line, keep the old lines there, so it will continue to grow this file is called data/closed_positions.txt
        # only add it to the file if it's not already there
        with open(CLOSED_POSITIONS_TXT, 'r') as f:
            lines = [line.strip() for line in f.readlines()]  # Strip the newline character from each line
            if token_mint_address not in lines:  # Now the comparison should work as expected
                with open(CLOSED_POSITIONS_TXT, 'a') as f:
                    f.write(token_mint_address + '\n')

        #print(f'for {token_mint_address[-4:]} closing position cause exit all positions is set to {EXIT_ALL_POSITIONS} and value is {usd_value} and tp is {tp} so closing...')
        try:

            market_sell(token_mint_address, sell_size)
            cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_blue')
            time.sleep(1)
            market_sell(token_mint_address, sell_size)
            cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_blue')
            time.sleep(1)
            market_sell(token_mint_address, sell_size)
            cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_blue')
            time.sleep(15)
            
        except:
            cprint('order error.. trying again', 'white', 'on_red')
            # time.sleep(7)

        balance = get_position(token_mint_address)
        price = ask_bid(token_mint_address)
        usd_value = balance * price
        tp = SELL_AT_MULTIPLE * USDC_SIZE
        sell_size = balance 
        
        # down downwards to 2 decimals
        sell_size = round_down(sell_size, 2)
        
        decimals = 0
        decimals = get_decimals(token_mint_address)
        #print(f'xxxxxxxxx for {token_mint_address[-4:]} decimals is {decimals}')
        sell_size = int(sell_size * 10 **decimals)
        #print(f'balance is {balance} and usd_value is {usd_value} EXIT ALL POSITIONS TRUE and sell_size is {sell_size} decimals is {decimals}')


    else:
        print(f'for {token_mint_address[-4:]} value is {usd_value} ')
        #time.sleep(10)

    print('closing position in full...')


def close_all_positions():

    # get all positions
    open_positions = fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)

    # loop through all positions and close them getting the mint address from Mint Address column
    for index, row in open_positions.iterrows():
        token_mint_address = row['Mint Address']

        # Check if the current token mint address is the USDC contract address
        #cprint(f'this is the token mint address {token_mint_address} this is don not trade list {dont_trade_list}', 'white', 'on_magenta')
        if token_mint_address in DO_NOT_TRADE_LIST:
            #print(f'Skipping kill switch for USDC contract at {token_mint_address}')
            continue  # Skip the rest of the loop for this iteration

        print(f'Closing position for {token_mint_address}...')
        kill_switch(token_mint_address)

def pnl_close(token_mint_address):

    ''' this will check to see if price is > sell 1, sell 2, sell 3 and sell accordingly '''

    # if time is on the 5 minute do the balance check, if not grab from data/current_position.csv
    balance = get_position(token_mint_address)
    
    # save to data/current_position.csv w/ pandas

    # get current price of token 
    price = ask_bid(token_mint_address)

    try:
        usd_value = float(balance) * float(price)
    except:
        usd_value = 0

    tp = SELL_AT_MULTIPLE * USDC_SIZE
    sl = ((1+STOP_LOSS_PERCENTAGE) * USDC_SIZE)
    sell_size = balance * SELL_AMOUNT_PERCENTAGE
    decimals = 0
    decimals = get_decimals(token_mint_address)
    #print(f'for {token_mint_address[-4:]} decimals is {decimals}')

    sell_size = int(sell_size * 10 **decimals)
    
    #print(f'bal: {balance} price: {price} usdVal: {usd_value} TP: {tp} sell size: {sell_size} decimals: {decimals}')

    while usd_value > tp:

        # log this mint address to a file and save as a new line, keep the old lines there, so it will continue to grow this file is called data/closed_positions.txt
        # only add it to the file if it's not already there
        with open(CLOSED_POSITIONS_TXT, 'r') as f:
            lines = [line.strip() for line in f.readlines()]  # Strip the newline character from each line
            if token_mint_address not in lines:  # Now the comparison should work as expected
                with open(CLOSED_POSITIONS_TXT, 'a') as f:
                    f.write(token_mint_address + '\n')

        cprint(f'for {token_mint_address[-4:]} value is {usd_value} and tp is {tp} so closing...', 'white', 'on_green')
        try:

            market_sell(token_mint_address, sell_size)
            cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_green')
            time.sleep(1)
            market_sell(token_mint_address, sell_size)
            cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_green')
            time.sleep(1)
            market_sell(token_mint_address, sell_size)
            cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_green')
            time.sleep(15)
            
        except:
            cprint('order error.. trying again', 'white', 'on_red')
            # time.sleep(7)

        balance = get_position(token_mint_address)
        price = ask_bid(token_mint_address)
        usd_value = balance * price
        tp = SELL_AT_MULTIPLE * USDC_SIZE
        sell_size = balance * SELL_AMOUNT_PERCENTAGE

        sell_size = int(sell_size * 10 **decimals)
        print(f'USD Value is {usd_value} | TP is {tp} ')


    else:
        hi = 'hi'
        #time.sleep(10)


    if usd_value != 0:
        #print(f'for {token_mint_address[-4:]} value is {usd_value} and sl is {sl} so not closing...')

        while usd_value < sl and usd_value > 0:

            sell_size = balance 
            sell_size = int(sell_size * 10 **decimals)

            cprint(f'for {token_mint_address[-4:]} value is {usd_value} and sl is {sl} so closing as a loss...', 'white', 'on_blue')
            print(token_mint_address)
            # log this mint address to a file and save as a new line, keep the old lines there, so it will continue to grow this file is called data/closed_positions.txt
            # only add it to the file if it's not already there
            with open(CLOSED_POSITIONS_TXT, 'r') as f:
                lines = [line.strip() for line in f.readlines()]  # Strip the newline character from each line
                if token_mint_address not in lines:  # Now the comparison should work as expected
                    with open(CLOSED_POSITIONS_TXT, 'a') as f:
                        f.write(token_mint_address + '\n')

            #print(f'for {token_mint_address[-4:]} value is {usd_value} and tp is {tp} so closing...')
            try:

                market_sell(token_mint_address, sell_size)
                cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_blue')
                time.sleep(1)
                market_sell(token_mint_address, sell_size)
                cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_blue')
                time.sleep(1)
                market_sell(token_mint_address, sell_size)
                cprint(f'just made an order {token_mint_address[-4:]} selling {sell_size} ...', 'white', 'on_blue')
                time.sleep(15)
                
            except:
                cprint('order error.. trying again', 'white', 'on_red')
                # time.sleep(7)

            balance = get_position(token_mint_address)
            price = ask_bid(token_mint_address)
            usd_value = balance * price
            tp = SELL_AT_MULTIPLE * USDC_SIZE
            sl = ((1+STOP_LOSS_PERCENTAGE) * USDC_SIZE)
            sell_size = balance 

            sell_size = int(sell_size * 10 **decimals)
            print(f'balance is {balance} and price is {price} and usd_value is {usd_value} and tp is {tp} and sell_size is {sell_size} decimals is {decimals}')

            # break the loop if usd_value is 0
            if usd_value == 0:
                print(f'successfully closed {token_mint_address[-4:]} usd_value is {usd_value} so breaking loop...')
                break

        else:
            print(f'for {token_mint_address[-4:]} value is {usd_value} and tp is {tp} so not closing...')
            time.sleep(10)
    else:
        print(f'for {token_mint_address[-4:]} value is {usd_value} and tp is {tp} so not closing...')
        time.sleep(10)

def open_position(token_mint_address):
    cprint(f'🎯 Kali Strategy: Evaluating dynamic position for token: {token_mint_address[-6:]}', 'white', 'on_blue', attrs=['bold'])

    # Check permanent blacklist first
    try:
        with open(PERMANENT_BLACKLIST, 'r') as f:
            blacklisted = [line.strip() for line in f.readlines()]
            if token_mint_address in blacklisted:
                cprint(f'⛔ Kali: Token {token_mint_address[-6:]} is permanently blacklisted, skipping', 'white', 'on_red')
                return
    except FileNotFoundError:
        # If file doesn't exist yet, create it
        open(PERMANENT_BLACKLIST, 'a').close()

    # First check if we already have ANY position
    initial_balance = get_position(token_mint_address)
    if initial_balance > 0:
        cprint(f'⚠️ Kali: Already have position in {token_mint_address[-6:]}, adding to closed positions', 'white', 'on_red')
        with open(CLOSED_POSITIONS_TXT, 'a') as f:
            f.write(f'{token_mint_address}\n')
        return

    # Check closed positions before attempting to open
    with open(CLOSED_POSITIONS_TXT, 'r') as f:
        closed_positions = [line.strip() for line in f.readlines()]
        if token_mint_address in closed_positions:
            cprint(f'⚠️ Kali: Token {token_mint_address[-6:]} in closed positions, skipping', 'white', 'on_red')
            return

    # === DYNAMIC STRATEGY: GET TOKEN OVERVIEW FOR LIQUIDITY ===
    cprint(f'📊 Kali Strategy: Fetching liquidity data for dynamic sizing...', 'white', 'on_cyan')
    token_overview_data = get_token_overview(token_mint_address)
    if not token_overview_data:
        cprint(f'⚠️ Kali Strategy: Could not get token overview for {token_mint_address[-6:]}, skipping', 'white', 'on_red')
        return

    liquidity = token_overview_data.get('liquidity', 0)
    if liquidity == 0:
        cprint(f'⚠️ Kali Strategy: Token {token_mint_address[-6:]} has zero liquidity, skipping', 'white', 'on_red')
        return

    # === DYNAMIC STRATEGY: CALCULATE POSITION SIZE ===
    dynamic_buy_size = calculate_dynamic_position_size(token_mint_address, liquidity)
    
    price = ask_bid(token_mint_address)
    if not price:
        cprint(f'⚠️ Kali: Could not get price for {token_mint_address[-6:]}, skipping', 'white', 'on_red')
        return

    try:
        # Use dynamic size instead of fixed USDC_SIZE
        size_needed_lamports = int(dynamic_buy_size * 10**6)  # Convert USDC to lamports
        size_needed_str = str(size_needed_lamports)

        cprint(f'🚀 Kali Strategy: Executing dynamic position', 'white', 'on_green', attrs=['bold'])
        cprint(f'   Size: ${dynamic_buy_size:.2f} USDC ({size_needed_lamports:,} lamports)', 'green')

        # Try to open position with dynamic sizing
        execution_success = False
        for i in range(orders_per_open):
            cprint(f'🎯 Kali: Attempting order {i+1}/{orders_per_open} for {token_mint_address[-6:]}', 'white', 'on_blue')
            
            # Check the return value from market_buy
            if not market_buy(token_mint_address, size_needed_str):
                cprint(f'❌ Kali: Market buy failed for {token_mint_address[-6:]}, token may be blacklisted', 'white', 'on_red')
                return
                
            time.sleep(1)
            
            # Check if we got any position after the order
            current_balance = get_position(token_mint_address)
            if current_balance > 0:
                cprint(f'✅ Kali Strategy: Dynamic position opened! Balance: {current_balance}', 'white', 'on_green', attrs=['bold'])
                
                # === DYNAMIC STRATEGY: RECORD POSITION STATE FOR TIERED MANAGEMENT ===
                record_new_position(token_mint_address, dynamic_buy_size, liquidity)
                
                # Add to closed positions to prevent re-entry
                with open(CLOSED_POSITIONS_TXT, 'a') as f:
                    f.write(f'{token_mint_address}\n')
                
                execution_success = True
                break

        if execution_success:
            return

    except Exception as e:
        cprint(f'❌ Kali Strategy: Order failed: {str(e)}', 'white', 'on_red')
        time.sleep(30)
        try:
            for i in range(orders_per_open):
                if not market_buy(token_mint_address, size_needed_str):
                    cprint(f'❌ Kali: Market buy failed on retry for {token_mint_address[-6:]}', 'white', 'on_red')
                    return
                    
                time.sleep(1)
                
                # Check again after retry
                current_balance = get_position(token_mint_address)
                if current_balance > 0:
                    cprint(f'✅ Kali Strategy: Position opened on retry! Balance: {current_balance}', 'white', 'on_green')
                    
                    # Record position state even on retry
                    record_new_position(token_mint_address, dynamic_buy_size, liquidity)
                    
                    with open(CLOSED_POSITIONS_TXT, 'a') as f:
                        f.write(f'{token_mint_address}\n')
                    return
                    
        except:
            cprint('❌ Kali Strategy: Order failed again, logging to closed positions', 'white', 'on_red')
            with open(CLOSED_POSITIONS_TXT, 'a') as f:
                f.write(f'{token_mint_address}\n')
            return

    # Final balance check
    final_balance = get_position(token_mint_address)
    if final_balance > 0:
        cprint(f'✅ Kali Strategy: Final position check - Balance: {final_balance}', 'white', 'on_green')
        record_new_position(token_mint_address, dynamic_buy_size, liquidity)
        with open(CLOSED_POSITIONS_TXT, 'a') as f:
            f.write(f'{token_mint_address}\n')
    else:
        cprint(f'❌ Kali Strategy: No position opened for {token_mint_address[-6:]}', 'white', 'on_red')
        # Add to closed positions anyway to prevent retries
        with open(CLOSED_POSITIONS_TXT, 'a') as f:
            f.write(f'{token_mint_address}\n')

def is_price_below_41_sma(symbol='ETH/USD'):
    # Initialize the exchange
    exchange = ccxt.kraken()
    exchange.load_markets()

    # Fetch daily OHLCV data for the last 200 days
    daily_ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=200)
    df = pd.DataFrame(daily_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Calculate the 40-day SMA
    df['41_sma'] = df['close'].rolling(window=41).mean()

    # Check if the last daily close is below the 40-day SMA
    last_close = df.iloc[-2]['close']
    last_sma = df.iloc[-1]['41_sma']

    #print(df)
    print(f'Last close: {last_close}, Last 41-day SMA: {last_sma}')
    
    return last_close < last_sma

