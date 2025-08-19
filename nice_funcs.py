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

# Telegram alert import
from telegram_manager import send_telegram_alert 

def create_keypair_from_key(key_data):
    """
    🔑 KALI: Create keypair from various key formats
    Handles both base58 strings and comma-separated byte arrays
    """
    try:
        if ',' in str(key_data):
            # Handle comma-separated byte array format like "86,194,209,..."
            byte_values = [int(x.strip()) for x in str(key_data).split(',')]
            return Keypair.from_bytes(bytes(byte_values))
        else:
            # Handle base58 string format
            return Keypair.from_base58_string(key_data)
    except Exception as e:
        cprint(f"❌ Kali: Error creating keypair: {e}", 'red')
        raise

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


def _parse_datetime_from_text(text: str):
    """Best-effort parse of a datetime string returned by web search."""
    import re
    from datetime import datetime, timezone
    candidates = []
    # ISO 8601 with Z
    for m in re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
        try:
            dt = datetime.strptime(m, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            candidates.append(dt)
        except Exception:
            pass
    # 'YYYY-MM-DD HH:MM:SS UTC'
    for m in re.findall(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\s*UTC", text):
        try:
            clean = m.replace("T", " ").replace(" UTC", "")
            dt = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            candidates.append(dt)
        except Exception:
            pass
    # 'MM/DD/YYYY HH:MM:SS' (Birdeye style), assume UTC if timezone absent
    for m in re.findall(r"\b\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\b", text):
        try:
            dt = datetime.strptime(m, "%m/%d/%Y %H:%M:%S").replace(tzinfo=timezone.utc)
            candidates.append(dt)
        except Exception:
            pass
    # If we found any, return the earliest (creation)
    if candidates:
        candidates.sort()
        return candidates[0]
    return None


def _parse_relative_age_hours_from_text(text: str):
    """Parse relative age strings like 'Pair created 1h 8m ago' into hours."""
    import re
    total_hours = None
    # Patterns: '1h 8m ago', '2h ago', '45m ago'
    rel = re.search(r"(\d+)\s*h(?:ours?)?\s*(\d+)?\s*m?", text, re.IGNORECASE)
    if rel:
        hours = int(rel.group(1))
        minutes = int(rel.group(2)) if rel.group(2) else 0
        total_hours = hours + minutes/60.0
        return total_hours
    # Minutes-only
    relm = re.search(r"(\d+)\s*m(?:in(?:ute)?s?)?\s*ago", text, re.IGNORECASE)
    if relm:
        minutes = int(relm.group(1))
        return minutes/60.0
    return None


def get_token_age_hours_perplexity(
    token_mint_address: str,
    model: str = 'sonar',
    timeout: int = 12,
    source_preference: str = 'solscan',  # 'birdeye' | 'dexscreener' | 'solscan' | 'mixed'
    attempts: int = 1,
):
    """
    Uses Perplexity Sonar to find the token creation timestamp from a block explorer page
    and returns the token age in hours (float). Returns None if undetermined.
    """
    try:
        api_key = getattr(d, 'perplexity_key', None)
        if not api_key:
            cprint("Sarsa/Perplexity: Missing API key in dontshare.py (perplexity_key)", 'yellow')
            return None

        # base URLs
        solscan_url = f"https://solscan.io/token/{token_mint_address}"
        birdeye_url = f"https://birdeye.so/token/{token_mint_address}?chain=solana"
        dexscreener_url = f"https://dexscreener.com/solana/{token_mint_address}"

        def build_prompt(preference: str) -> str:
            sources = []
            if preference == 'birdeye':
                sources = [
                    f"Birdeye: {birdeye_url}",
                    f"Solscan: {solscan_url}",
                    f"Dexscreener: {dexscreener_url}",
                ]
            elif preference == 'dexscreener':
                sources = [
                    f"Dexscreener: {dexscreener_url}",
                    f"Solscan: {solscan_url}",
                    f"Birdeye: {birdeye_url}",
                ]
            elif preference == 'solscan':
                sources = [
                    f"Solscan: {solscan_url}",
                    f"Birdeye: {birdeye_url}",
                    f"Dexscreener: {dexscreener_url}",
                ]
            else:
                sources = [
                    f"Solscan: {solscan_url}",
                    f"Birdeye: {birdeye_url}",
                    f"Dexscreener: {dexscreener_url}",
                ]
            source_lines = "\n".join(sources)
            return (
                "You are checking the creation time of a Solana token by its mint address.\n"
                f"Mint: {token_mint_address}\n"
                "Visit these pages (in the given order of preference) and find the very first transaction (mint creation or pair creation).\n"
                f"{source_lines}\n"
                "Return ONLY the UTC timestamp as ISO 8601 (YYYY-MM-DDTHH:MM:SSZ). If you can only find relative time like 'Pair created 1h 8m ago', return exactly that phrase.\n"
                "If you cannot determine it, reply exactly with the word: unknown"
            )

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        preferences = [source_preference]
        if source_preference != 'birdeye':
            preferences.append('birdeye')
        if source_preference != 'dexscreener':
            preferences.append('dexscreener')
        if source_preference != 'solscan':
            preferences.append('solscan')

        # Try across preferences and attempts
        for pref in preferences:
            for _ in range(max(1, attempts)):
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": build_prompt(pref)}],
                    "temperature": 0.0,
                }
                resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=timeout)
                if not resp.ok:
                    continue
                data = resp.json()
                content = None
                try:
                    content = data['choices'][0]['message']['content']
                except Exception:
                    content = str(data)

                if not content:
                    continue
                if content.strip().lower() == 'unknown':
                    continue

                # Parse absolute time
                dt = _parse_datetime_from_text(content)
                if not dt:
                    dt = _parse_datetime_from_text(json.dumps(data))
                if dt:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    return (now - dt).total_seconds() / 3600.0

                # Parse relative age
                rel_hours = _parse_relative_age_hours_from_text(content)
                if rel_hours is None:
                    rel_hours = _parse_relative_age_hours_from_text(json.dumps(data))
                if rel_hours is not None:
                    return rel_hours

        # If all attempts exhausted
        return None

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        age_hours = (now - dt).total_seconds() / 3600.0
        return age_hours
    except Exception as e:
        cprint(f"Perplexity exception: {e}", 'yellow')
        return None

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

    # === Freshness Filter: ultra-fast 1m OHLCV + pressure gate ===
    fresh_overview_data = None
    try:
        if ENABLE_FRESHNESS_FILTER:
            # 1) Fetch a small 1m OHLCV window to count candles and evaluate early momentum
            time_to = int(time.time())
            time_from = time_to - (FRESH_INITIAL_WINDOW_MIN * 60)
            ohlcv_url = (
                f"https://public-api.birdeye.so/defi/ohlcv?address={token_address}"
                f"&type=1m&time_from={time_from}&time_to={time_to}"
            )
            ohlcv_headers = {"X-API-KEY": birdeye_api_key}
            ohlcv_resp = requests.get(ohlcv_url, headers=ohlcv_headers, timeout=6)
            if ohlcv_resp.ok:
                items = (ohlcv_resp.json() or {}).get('data', {}).get('items', [])
                num_candles = len(items)
                if num_candles > FRESH_MAX_1M_CANDLES:
                    cprint(
                        f"   🚫 Freshness: Too many 1m candles ({num_candles} > {FRESH_MAX_1M_CANDLES}) — old token",
                        'red'
                    )
                    return False

                if FRESH_ENABLE_MOMENTUM_CHECK and num_candles >= 1:
                    # Use first up to 5 candles for basic momentum/health checks
                    first_five = items[:5]
                    # Volume check (Birdeye OHLCV volume is in quote currency; treat as USD proxy)
                    total_vol_usd = 0.0
                    try:
                        for it in first_five:
                            v = it.get('v', 0) or 0
                            total_vol_usd += float(v)
                    except Exception:
                        total_vol_usd = 0.0

                    if total_vol_usd < FRESH_MIN_VOLUME_USD_FIRST5:
                        cprint(
                            f"   🚫 Freshness: Weak initial volume (${total_vol_usd:,.0f} < ${FRESH_MIN_VOLUME_USD_FIRST5:,.0f})",
                            'red'
                        )
                        return False

                    # Catastrophic dump check between candle 1 and 2 where available
                    if len(items) >= 2:
                        c1_high = (items[0].get('h') or 0)
                        c2_low = (items[1].get('l') or 0)
                        try:
                            c1_high = float(c1_high)
                            c2_low = float(c2_low)
                        except Exception:
                            c1_high = 0.0
                            c2_low = 0.0
                        if c1_high > 0 and c2_low < c1_high * FRESH_CATASTROPHIC_DUMP_RATIO:
                            cprint(
                                "   🚫 Freshness: Early catastrophic dump detected (c2_low < 20% of c1_high)",
                                'red'
                            )
                            return False

            # 2) Buy/Sell pressure proxy via overview (fast) unless we add a heavier unique-wallet call later
            if FRESH_ENABLE_PRESSURE_CHECK and FRESH_USE_OVERVIEW_COUNTS_AS_PROXY:
                ov_url = f"https://public-api.birdeye.so/defi/token_overview?address={token_address}"
                ov_headers = {"X-API-KEY": birdeye_api_key}
                ov_resp = requests.get(ov_url, headers=ov_headers, timeout=6)
                if ov_resp.ok:
                    ov = (ov_resp.json() or {}).get('data', {})
                    fresh_overview_data = ov
                    buy1h = float(ov.get('buy1h', 0) or 0)
                    sell1h = float(ov.get('sell1h', 0) or 0)
                    if sell1h <= 0 and buy1h > 0:
                        ratio = float('inf')
                    elif buy1h <= 0:
                        ratio = 0.0
                    else:
                        ratio = buy1h / max(sell1h, 1e-9)
                    if ratio < FRESH_MIN_BUY_SELL_RATIO:
                        cprint(
                            f"   🚫 Freshness: Weak buy/sell pressure (ratio {ratio:.2f} < {FRESH_MIN_BUY_SELL_RATIO:.2f})",
                            'red'
                        )
                        return False
                # If overview not ok, skip pressure check to avoid blocking fresh snipes on brand-new indexing
    except Exception as fresh_e:
        cprint(f"   ⚠️ Freshness check error (continuing): {fresh_e}", 'yellow')


    # === Birdeye Security Check ===
    max_retries = 8  # Increased to handle very new tokens
    retry_delay = 5.0  # Longer initial delay for better success rate
    
    for attempt in range(max_retries):
        try:
            sec_url = f"https://public-api.birdeye.so/defi/token_security?address={token_address}"
            sec_headers = {"X-API-KEY": birdeye_api_key}
            sec_response = requests.get(sec_url, headers=sec_headers, timeout=8)
            
            if sec_response.status_code == 200:
                # Success! Break out of retry loop
                break
            elif sec_response.status_code in [555, 404, 500, 502, 503]:
                # These codes suggest data not ready yet - retry
                if attempt < max_retries - 1:
                    cprint(f"   ⏳ Token data not ready (Code: {sec_response.status_code}), retrying in {retry_delay}s... (attempt {attempt + 1})", 'yellow')
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                    continue
                else:
                    cprint(f"   🚨 VETTING FAILED: Birdeye security API error after {max_retries} attempts (Code: {sec_response.status_code})", 'red')
                    return False
            else:
                # Other errors (rate limit, auth, etc.) - fail immediately
                cprint(f"   🚨 VETTING FAILED: Birdeye security API error (Code: {sec_response.status_code})", 'red')
                return False
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                cprint(f"   ⏳ Network error, retrying in {retry_delay}s... (attempt {attempt + 1}): {e}", 'yellow')
                time.sleep(retry_delay)
                retry_delay *= 1.5
                continue
            else:
                cprint(f"   🚨 VETTING FAILED: Network error after {max_retries} attempts: {e}", 'red')
                return False
    
    # Process the successful response
    security_data = sec_response.json().get('data', {})
    if not security_data:
        cprint("   🚨 VETTING FAILED: No security data returned from Birdeye", 'red')
        return False

    # === CRITICAL SEVERITY SECURITY FILTERS ===
    # Based on official Birdeye Security Documentation: https://docs.birdeye.so/docs/security
    
    # 1. Fake Token Check (Critical)
    if REJECT_FAKE_TOKENS and security_data.get('fakeToken'):
        cprint("   🚨 VETTING FAILED: FAKE TOKEN - Scam/imitation detected", 'red')
        return False
    
    # 2. Ownership Renounced Check (Critical) 
    if not security_data.get('ownershipRenounced', False):
        if REJECT_NON_RENOUNCED_OWNERSHIP:
            cprint("   🚨 VETTING FAILED: OWNERSHIP NOT RENOUNCED - Owner can change parameters", 'red')
            return False
        else:
            cprint("   ⚠️ WARNING: OWNERSHIP NOT RENOUNCED - Owner retains control (RISK ACCEPTED)", 'red')
    
    # 3. Honeypot Check (Critical)
    if REJECT_HONEYPOTS and security_data.get('honeypot'):
        cprint("   🚨 VETTING FAILED: HONEYPOT - Buyers cannot sell", 'red')
        return False
    
    # 4. Freezable Token Check (Critical)
    if REJECT_FREEZABLE_TOKENS and security_data.get('freezable'):
        cprint("   🚨 VETTING FAILED: FREEZABLE - Can freeze token transfers", 'red')
        return False
        
    # 5. Freeze Authority Check (Critical)
    if REJECT_FREEZABLE_TOKENS and security_data.get('freezeAuthority') is not None:
        cprint("   🚨 VETTING FAILED: FREEZE AUTHORITY EXISTS", 'red')
        return False
    
    # 6. Token 2022 Check (Critical)
    if REJECT_TOKEN_2022 and security_data.get('isToken2022'):
        cprint("   🚨 VETTING FAILED: TOKEN 2022 PROGRAM - Experimental standard", 'red')
        return False

    # === HIGH RISK SECURITY FILTERS ===
    
    # 7. Mintable Token Check (High Risk)
    if REJECT_MINTABLE_TOKENS and security_data.get('mintable'):
        cprint("   🚨 VETTING FAILED: MINTABLE - Can create infinite supply", 'red')
        return False
    
    # 8. Mutable Metadata Check (High Risk)
    if security_data.get('mutableMetadata'):
        if REJECT_MUTABLE_METADATA:
            cprint("   🚨 VETTING FAILED: MUTABLE METADATA - Can change name/logo", 'red')
            return False
        else:
            cprint("   ⚠️ INFO: MUTABLE METADATA detected - Token can change name/logo (allowed)", 'yellow')
    
    # 9. Transfer Fees Check (High Risk)
    if REJECT_TRANSFER_FEES and security_data.get('transferFees'):
        cprint("   🚨 VETTING FAILED: TRANSFER FEES - Charges fees on transfers", 'red')
        return False
    
    # 10. Buy Tax Check (High Risk)
    buy_tax = security_data.get('buyTax', 0)
    if buy_tax is not None and isinstance(buy_tax, (int, float)) and buy_tax > MAX_BUY_TAX:
        cprint(f"   🚨 VETTING FAILED: BUY TAX {buy_tax:.1%} > {MAX_BUY_TAX:.1%}", 'red')
        return False
    
    # 11. Sell Tax Check (High Risk)
    sell_tax = security_data.get('sellTax', 0)
    if sell_tax is not None and isinstance(sell_tax, (int, float)) and sell_tax > MAX_SELL_TAX:
        cprint(f"   🚨 VETTING FAILED: SELL TAX {sell_tax:.1%} > {MAX_SELL_TAX:.1%}", 'red')
        return False
    
    # 12. Owner Percentage Check (High Risk)
    owner_pct = security_data.get('ownerPercentage', 0)
    if owner_pct is not None and isinstance(owner_pct, (int, float)) and owner_pct > MAX_OWNER_PERCENTAGE:
        cprint(f"   🚨 VETTING FAILED: OWNER HOLDS {owner_pct:.1%} > {MAX_OWNER_PERCENTAGE:.1%}", 'red')
        return False
    
    # 13. Update Authority Percentage Check (High Risk)
    ua_pct = security_data.get('updateAuthorityPercentage', 0)
    if ua_pct is not None and isinstance(ua_pct, (int, float)) and ua_pct > MAX_UPDATE_AUTHORITY_PERCENTAGE:
        cprint(f"   🚨 VETTING FAILED: UPDATE AUTHORITY HOLDS {ua_pct:.1%} > {MAX_UPDATE_AUTHORITY_PERCENTAGE:.1%}", 'red')
        return False
    
    # 14. Top 10 Holders Check (High Risk)
    top_10_pct = security_data.get('top10HolderPercent', 1.0)
    if top_10_pct is not None and isinstance(top_10_pct, (int, float)) and top_10_pct > MAX_TOP10_HOLDER_PERCENT:
        cprint(f"   🚨 VETTING FAILED: TOP 10 HOLDERS {top_10_pct:.1%} > {MAX_TOP10_HOLDER_PERCENT:.1%}", 'red')
        return False

    # === MEDIUM RISK FILTERS ===
    
    # 15. Mutable Info Check (Medium Risk)
    if security_data.get('mutableInfo'):
        if not ALLOW_MUTABLE_INFO:
            cprint("   ⚠️ VETTING FAILED: MUTABLE INFO - Token info can be changed", 'yellow')
            return False
        else:
            cprint("   ℹ️ INFO: MUTABLE INFO detected - Additional token info can be changed (allowed)", 'cyan')
        
    cprint("   ✅ ALL SECURITY CHECKS PASSED", 'green')
        
    # === Birdeye Market Overview Check ===
    if fresh_overview_data is None:
        max_retries_overview = 8  # Increased to handle very new tokens
        retry_delay_overview = 5.0  # Longer initial delay for better success rate
        for attempt in range(max_retries_overview):
            try:
                overview_url = f"https://public-api.birdeye.so/defi/token_overview?address={token_address}"
                overview_headers = {"X-API-KEY": birdeye_api_key}
                overview_response = requests.get(overview_url, headers=overview_headers, timeout=8)
                if overview_response.status_code == 200:
                    fresh_overview_data = (overview_response.json() or {}).get('data', {})
                    break
                elif overview_response.status_code in [555, 404, 500, 502, 503]:
                    if attempt < max_retries_overview - 1:
                        cprint(f"   ⏳ Overview data not ready (Code: {overview_response.status_code}), retrying in {retry_delay_overview}s... (attempt {attempt + 1})", 'yellow')
                        time.sleep(retry_delay_overview)
                        retry_delay_overview *= 1.5
                        continue
                    else:
                        cprint(f"   🚨 VETTING FAILED: Birdeye overview API error after {max_retries_overview} attempts (Code: {overview_response.status_code})", 'red')
                        return False
                else:
                    cprint(f"   🚨 VETTING FAILED: Birdeye overview API error (Code: {overview_response.status_code})", 'red')
                    return False
            except requests.exceptions.RequestException as e:
                if attempt < max_retries_overview - 1:
                    cprint(f"   ⏳ Network error on overview, retrying in {retry_delay_overview}s... (attempt {attempt + 1}): {e}", 'yellow')
                    time.sleep(retry_delay_overview)
                    retry_delay_overview *= 1.5
                    continue
                else:
                    cprint(f"   🚨 VETTING FAILED: Network error during overview check after {max_retries_overview} attempts: {e}", 'red')
                    return False

    # Process the overview data (from freshness stage or retries)
    overview_data = fresh_overview_data or {}
    if not overview_data:
        cprint("   🚨 VETTING FAILED: No overview data returned from Birdeye", 'red')
        return False
        
    liquidity = overview_data.get('liquidity', 0)
    market_cap = overview_data.get('mc', 0)
    
    # Ensure values are never None
    if liquidity is None:
        liquidity = 0
    if market_cap is None:
        market_cap = 0
    
    # --- Market Quality Checks ---
    if isinstance(liquidity, (int, float)) and liquidity < MIN_LIQUIDITY:
        cprint(f"   🚨 VETTING FAILED: Insufficient liquidity (${liquidity:,.2f} < ${MIN_LIQUIDITY:,.2f})", 'red')
        return False
        
    if isinstance(market_cap, (int, float)) and market_cap > MAX_MARKET_CAP:
        cprint(f"   🚨 VETTING FAILED: Market cap too high (${market_cap:,.2f} > ${MAX_MARKET_CAP:,.2f})", 'red')
        return False

    cprint(f"   ✅ Market checks passed (Liquidity: ${liquidity:,.0f}, MC: ${market_cap:,.0f})", 'green')

    # === TOKEN AGE CHECK (Prevent trading old tokens) ===
    try:
        creation_time = overview_data.get('creation_time') or overview_data.get('createdAt')
        if creation_time:
            current_time = time.time()
            # Convert creation_time to timestamp if it's a string
            if isinstance(creation_time, str):
                from datetime import datetime
                try:
                    # Try parsing various date formats
                    creation_timestamp = datetime.fromisoformat(creation_time.replace('Z', '+00:00')).timestamp()
                except:
                    # If parsing fails, try other common formats
                    try:
                        creation_timestamp = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
                    except:
                        creation_timestamp = None
            else:
                creation_timestamp = creation_time
            
            if creation_timestamp:
                token_age_hours = (current_time - creation_timestamp) / 3600
                
                # Reject tokens older than configured limit
                try:
                    age_cap = MAX_TOKEN_AGE_HOURS
                except NameError:
                    from config import MAX_TOKEN_AGE_HOURS as age_cap  # fallback
                if token_age_hours > age_cap:
                    cprint(f"   🚨 VETTING FAILED: Token too old ({token_age_hours:.1f}h > {age_cap}h)", 'red')
                    return False
                else:
                    cprint(f"   ✅ Token age check passed: {token_age_hours:.1f}h old", 'green')
            else:
                # Fallback: compute age via RPC/Birdeye mixed method to avoid sniping old tokens
                fallback_age = get_token_age_hours_api(token_address, prefer='birdeye')
                try:
                    age_cap = MAX_TOKEN_AGE_HOURS
                except NameError:
                    from config import MAX_TOKEN_AGE_HOURS as age_cap
                if isinstance(fallback_age, (int, float)) and fallback_age > age_cap:
                    cprint(f"   🚨 VETTING FAILED: Token too old by fallback age ({fallback_age:.1f}h > {age_cap}h)", 'red')
                    return False
                # If fallback is unavailable, apply heuristic on very high liq/mc suggesting old token
                if fallback_age is None and (liquidity > 1_000_000 or market_cap > 1_000_000):
                    cprint(f"   🚨 VETTING FAILED: High liquidity/MC suggests old token (Liq: ${liquidity:,.0f}, MC: ${market_cap:,.0f})", 'red')
                    return False
                cprint("   ✅ Token age check: No reliable age but no old-token indicators", 'green')
        else:
            # NEW LOGIC: For Speed Engine detections, NO age data often means VERY NEW token
            # Check if this is a reasonable new token based on liquidity/MC
            # Before trusting heuristics, try the fallback fast age check
            fallback_age2 = get_token_age_hours_api(token_address, prefer='birdeye')
            try:
                age_cap2 = MAX_TOKEN_AGE_HOURS
            except NameError:
                from config import MAX_TOKEN_AGE_HOURS as age_cap2
            if isinstance(fallback_age2, (int, float)) and fallback_age2 > age_cap2:
                cprint(f"   🚨 VETTING FAILED: Token too old by fallback age ({fallback_age2:.1f}h > {age_cap2}h)", 'red')
                return False
            if fallback_age2 is None and (liquidity > 1_000_000 or market_cap > 1_000_000):
                cprint(f"   🚨 VETTING FAILED: High liquidity/MC without age data suggests old token (Liq: ${liquidity:,.0f}, MC: ${market_cap:,.0f})", 'red')
                return False
            # Low liquidity + no reliable age = likely very new; proceed
            cprint(f"   ✅ Token age check: No age data but low liquidity/MC - likely fresh token", 'green')
            cprint(f"   Liquidity: ${liquidity:,.0f}, MC: ${market_cap:,.0f} (proceeding)", 'cyan')
    except Exception as age_error:
        cprint(f"   ⚠️ Token age check error: {age_error} (proceeding anyway for new tokens)", 'yellow')

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


def get_token_creation_timestamp_birdeye(token_mint_address: str):
    """
    Try to fetch creation timestamp from Birdeye token_overview.
    Returns UNIX epoch seconds (float) or None.
    """
    try:
        API_KEY = d.birdeye
        url = f"https://public-api.birdeye.so/defi/token_overview?address={token_mint_address}"
        headers = {"X-API-KEY": API_KEY}
        r = requests.get(url, headers=headers, timeout=8)
        if not r.ok:
            return None
        data = r.json().get('data', {})
        creation = data.get('creation_time') or data.get('createdAt')
        if not creation:
            return None
        # createdAt may be ISO or epoch
        try:
            # epoch seconds
            if isinstance(creation, (int, float)):
                return float(creation)
            # ISO string
            from datetime import datetime, timezone
            # Normalize Z
            iso = str(creation).replace('Z', '+00:00')
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            return None
    except Exception:
        return None


def get_token_creation_timestamp_rpc(token_mint_address: str, max_pages: int = 20, page_limit: int = 100):
    """
    Use Helius RPC getSignaturesForAddress to find the oldest signature touching the mint address
    and return its blockTime as UNIX epoch seconds. Paginates up to max_pages.
    """
    try:
        before_sig = None
        oldest_time = None
        for _ in range(max_pages):
            params = [token_mint_address, {"limit": page_limit}]
            if before_sig:
                params[1]["before"] = before_sig
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": params,
            }
            resp = requests.post(d.rpc_url, json=payload, timeout=8)
            if not resp.ok:
                break
            arr = resp.json().get('result', [])
            if not arr:
                break
            # Update oldest
            for entry in arr:
                bt = entry.get('blockTime')
                if bt is not None:
                    if oldest_time is None or bt < oldest_time:
                        oldest_time = bt
            # Prepare next page
            before_sig = arr[-1].get('signature')
            if len(arr) < page_limit:
                break
        return float(oldest_time) if oldest_time is not None else None
    except Exception:
        return None


def get_token_age_hours_api(token_mint_address: str, prefer: str = 'birdeye'):
    """
    Reliable token age via APIs. Try Birdeye first, then fallback to RPC scan.
    Returns age hours (float) or None if undetermined.
    """
    from datetime import datetime, timezone
    # Order by preference
    sources = ['birdeye', 'rpc']
    if prefer == 'rpc':
        sources = ['rpc', 'birdeye']

    ts = None
    for src in sources:
        if src == 'birdeye':
            ts = get_token_creation_timestamp_birdeye(token_mint_address)
        elif src == 'rpc':
            ts = get_token_creation_timestamp_rpc(token_mint_address)
        if ts:
            break
    if not ts:
        return None
    now = datetime.now(timezone.utc).timestamp()
    age_hours = (now - float(ts)) / 3600.0
    return age_hours

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
        cprint(f"📝 Kali Strategy: Recording new position for {token_address[-6:]}", 'cyan')
        cprint(f"   Investment: ${buy_size_usdc:.2f}, Liquidity: ${liquidity:,.0f}", 'cyan')
        
        states = load_position_states()
        cprint(f"   Current tracked positions: {len(states)}", 'cyan')
        
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
            cprint(f"   Total positions now tracked: {len(states)}", 'green')
        else:
            cprint(f"⚠️ Kali Strategy: Position {token_address[-6:]} already tracked", 'yellow')
            
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error recording position: {e}", 'red')
        import traceback
        cprint(f"   Traceback: {traceback.format_exc()}", 'red')


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


#def calculate_dynamic_position_size(token_address, liquidity):
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


def has_active_positions():
    """
    🔒 KALI SEQUENTIAL MODE: Check if there are any active positions.
    Returns True if any positions are open, False otherwise.
    FIXED: Calculate USD values properly since raw data has 0 values.
    """
    try:
        # DIRECT CHECK: Look at actual wallet holdings
        holdings = fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
        
        if not holdings.empty:
            # Filter out USDC, SOL, and any DO_NOT_TRADE tokens
            try:
                with open(CLOSED_POSITIONS_TXT, 'r') as f:
                    closed_list = [line.strip() for line in f if line.strip()]
            except Exception:
                closed_list = []
            excluded_tokens = [USDC_CA, 'So11111111111111111111111111111111111111112'] + DO_NOT_TRADE_LIST + closed_list
            
            # Check each holding
            for _, row in holdings.iterrows():
                token_address = row['Mint Address']
                amount = row['Amount']
                
                # Skip excluded tokens
                if token_address in excluded_tokens:
                    continue
                
                # Skip if no amount
                if amount <= 0:
                    continue
                
                # Calculate USD value since it's 0 in raw data
                try:
                    price = ask_bid(token_address)
                    if price and price > 0:
                        usd_value = amount * float(price)
                        
                        # Skip very small holdings (dust)
                        if usd_value < 0.5:  # Less than $0.50
                            continue
                        
                        # We found an active position!
                        cprint(f"   📍 Active position detected: ${usd_value:.2f} of {token_address[-6:]}", 'cyan')
                        return True
                except:
                    # If we can't get price but have amount, assume it's a position
                    if amount > 0.001:  # More than dust amount
                        cprint(f"   📍 Active position detected: {amount:.4f} of {token_address[-6:]}", 'cyan')
                        return True
        
        return False
        
    except Exception as e:
        cprint(f"⚠️ Kali Sequential: Error checking positions: {e}", 'yellow')
        # If there's an error, assume we have positions to be safe
        return True

def get_active_position_count():
    """
    🔢 KALI SEQUENTIAL MODE: Returns the number of active positions.
    FIXED: Calculate USD values properly to count positions.
    """
    try:
        holdings = fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
        active_count = 0
        
        if not holdings.empty:
            # Filter out USDC, SOL, and any DO_NOT_TRADE tokens
            try:
                with open(CLOSED_POSITIONS_TXT, 'r') as f:
                    closed_list = [line.strip() for line in f if line.strip()]
            except Exception:
                closed_list = []
            excluded_tokens = [USDC_CA, 'So11111111111111111111111111111111111111112'] + DO_NOT_TRADE_LIST + closed_list
            
            for _, row in holdings.iterrows():
                token_address = row['Mint Address']
                amount = row['Amount']
                
                # Skip excluded tokens
                if token_address in excluded_tokens:
                    continue
                
                # Skip if no amount
                if amount <= 0:
                    continue
                
                # Calculate USD value
                try:
                    price = ask_bid(token_address)
                    if price and price > 0:
                        usd_value = amount * float(price)
                        if usd_value >= 0.5:  # More than $0.50
                            active_count += 1
                except:
                    # If we can't get price but have amount, count it
                    if amount > 0.001:
                        active_count += 1
                        
        return active_count
        
    except Exception as e:
        cprint(f"⚠️ Kali Sequential: Error counting positions: {e}", 'yellow')
        return 0

def wait_for_position_completion():
    """
    🕐 KALI SEQUENTIAL MODE: Blocks execution until all positions are closed.
    """
    import time
    
    while has_active_positions():
        position_count = get_active_position_count()
        cprint(f"⏳ Kali Sequential: Waiting for {position_count} position(s) to close...", 'yellow')
        cprint(f"   Position will close at profit target or stop loss", 'cyan')
        
        # Wait 30 seconds before checking again
        time.sleep(30)
    
    cprint("✅ Kali Sequential: All positions closed, ready for next snipe", 'green')

def clean_closed_positions():
    """
    🧹 KALI SEQUENTIAL MODE: Clean up fully closed positions from state file.
    FIXED: Only clean positions that are ACTUALLY closed (not in wallet).
    """
    try:
        states = load_position_states()
        if not states:
            return
            
        holdings = fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
        
        # Get list of tokens we actually hold
        held_tokens = []
        if not holdings.empty:
            held_tokens = holdings['Mint Address'].tolist()
        
        tokens_to_remove = []
        
        for token_address in states.keys():
            # Only remove if we DON'T hold this token anymore
            if token_address not in held_tokens:
                tokens_to_remove.append(token_address)
                cprint(f"🧹 Kali Sequential: Will clean {token_address[-6:]} (not in wallet)", 'cyan')
            else:
                # Keep it - we still hold this token
                token_row = holdings[holdings['Mint Address'] == token_address]
                if not token_row.empty:
                    value = token_row.iloc[0]['USD Value']
                    cprint(f"   📍 Keeping {token_address[-6:]} (still held: ${value:.2f})", 'green')
        
        # Remove only truly closed positions
        for token in tokens_to_remove:
            del states[token]
        
        if tokens_to_remove:
            save_position_states(states)
            cprint(f"🧹 Cleaned {len(tokens_to_remove)} closed position(s)", 'cyan')
        
    except Exception as e:
        cprint(f"⚠️ Kali Sequential: Error cleaning positions: {e}", 'yellow')

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
        current_balance = get_position_fast(token_address)
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
    """
    🎯 KALI: Get token overview data from Birdeye API.
    Returns dict with liquidity data or empty dict if error.
    """
    try:
        API_KEY = d.birdeye
        url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
        headers = {"X-API-KEY": API_KEY}
        response = requests.get(url, headers=headers, timeout=8)
        
        if response.ok:
            json_response = response.json()
            data = json_response.get('data', {})
            # Ensure liquidity is always a number, never None
            if data and 'liquidity' in data:
                if data['liquidity'] is None:
                    data['liquidity'] = 0
            return data or {}  # Return empty dict if data is None
        else:
            # Return empty dict if there's an error
            cprint(f"⚠️ Kali: Error fetching overview for {address[-6:]}: {response.status_code}", 'yellow')
            return {}
            
    except Exception as e:
        cprint(f"⚠️ Kali: Exception in get_token_overview: {e}", 'yellow')
        return {}
    

def get_names_nosave(df):
    """
    💰 KALI: Get token names AND calculate USD values for portfolio display
    """
    names = []
    usd_values = []

    for index, row in df.iterrows():
        token_mint_address = row['Mint Address']
        amount = row['Amount']
        
        # Get token overview data (contains name and price info)
        token_data = get_token_overview(token_mint_address)
        # Name keyword blocklist
        token_name_lower = str(token_data.get('name', '')).lower()
        if any(kw in token_name_lower for kw in NAME_BLOCKLIST_KEYWORDS):
            # Skip this row by setting zero value
            names.append(token_data.get('name', f'Token-{token_mint_address[-6:]}'))
            usd_values.append(0.0)
            continue
        
        # Extract token name
        token_name = token_data.get('name', f'Token-{token_mint_address[-6:]}')
        names.append(token_name)
        
        # Calculate USD value using Birdeye price
        try:
            # Try to get price from token overview first
            if token_data and 'price' in token_data:
                price = float(token_data.get('price', 0))
                usd_value = amount * price
            else:
                # Fallback: use ask_bid function for price
                price = ask_bid(token_mint_address)
                if price and price > 0:
                    usd_value = amount * float(price)
                else:
                    usd_value = 0.0
                    
            usd_values.append(round(usd_value, 2))
            
        except Exception as e:
            cprint(f"⚠️ Kali: Error calculating USD value for {token_name}: {e}", 'yellow')
            usd_values.append(0.0)
    
    # Update the dataframe with names and calculated USD values
    if 'name' in df.columns:
        df['name'] = names
    else:
        df.insert(0, 'name', names)
        
    # Update USD Value column with calculated values
    df['USD Value'] = usd_values
    
    return df
def passes_pump_momentum_filter(token_mint_address: str, birdeye_api_key: str) -> bool:
    """
    Fast 5-minute momentum screen using Birdeye OHLCV (1m) and overview.
    Returns True if the token shows strong pump characteristics.
    """
    if not ENABLE_PUMP_FILTER:
        return True
    try:
        # 1) Overview for liquidity, mc, top10 holders
        ov = get_token_overview(token_mint_address)
        liquidity = float(ov.get('liquidity', 0) or 0)
        mc = float(ov.get('mc', 0) or 0)
        top10 = ov.get('top10HolderPercent', None)
        wallets24h = int(ov.get('uniqueWallet24h', 0) or 0)
        trades1h = int((ov.get('buy1h', 0) or 0) + (ov.get('sell1h', 0) or 0))
        if liquidity < PUMP_MIN_LIQUIDITY:
            cprint(f"   🚫 Pump filter: Low liquidity (${liquidity:,.0f} < ${PUMP_MIN_LIQUIDITY:,.0f})", 'red')
            return False
        # Allow tokens with 0 market cap if they're very new (common for fresh tokens)
        if mc < PUMP_MIN_MARKET_CAP and mc > 0:
            cprint(f"   🚫 Pump filter: Low market cap (${mc:,.0f} < ${PUMP_MIN_MARKET_CAP:,.0f})", 'red')
            return False
        elif mc == 0:
            cprint("   ℹ️ Pump filter: Market cap not available (very new token), continuing evaluation", 'yellow')
        # Only enforce holder concentration if we have basic activity/holders context
        if top10 is not None:
            try:
                top10f = float(top10 or 0)
            except Exception:
                top10f = 1.0
            if wallets24h >= PUMP_HOLDER_CHECK_MIN_WALLETS or trades1h >= PUMP_HOLDER_CHECK_MIN_TRADES:
                if top10f > PUMP_MAX_TOP10_HOLDER_PERCENT:
                    cprint(f"   🚫 Pump filter: Concentrated holders ({top10f:.0%} > {PUMP_MAX_TOP10_HOLDER_PERCENT:.0%})", 'red')
                    return False
            else:
                cprint("   ℹ️ Pump filter: Skipping top holder check due to low wallets/trades (very fresh)", 'yellow')
        # 2) 5-minute OHLCV window (1m bars)
        import time as _t
        t_to = int(_t.time())
        t_from = t_to - 5 * 60
        url = (
            f"https://public-api.birdeye.so/defi/ohlcv?address={token_mint_address}"
            f"&type=1m&time_from={t_from}&time_to={t_to}"
        )
        headers = {"X-API-KEY": birdeye_api_key}
        resp = requests.get(url, headers=headers, timeout=6)
        items = []
        if resp.ok:
            items = (resp.json() or {}).get('data', {}).get('items', [])
        if len(items) < 2:
            cprint("   🚫 Pump filter: Not enough 1m candles", 'red')
            return False
        total_vol = 0.0
        greens = 0
        first_open = float(items[0].get('o', 0) or 0)
        last_close = float(items[-1].get('c', 0) or 0)
        for it in items[-5:]:
            o = float(it.get('o', 0) or 0)
            c = float(it.get('c', 0) or 0)
            v = float(it.get('v', 0) or 0)
            total_vol += v
            if c > o:
                greens += 1
        if total_vol < PUMP_MIN_VOL_5M_USD:
            cprint(f"   🚫 Pump filter: 5m volume low (${total_vol:,.0f} < ${PUMP_MIN_VOL_5M_USD:,.0f})", 'red')
            return False
        if greens < PUMP_MIN_GREEN_CANDLES_5M:
            cprint(f"   🚫 Pump filter: Only {greens} green candles in last 5 (< {PUMP_MIN_GREEN_CANDLES_5M})", 'red')
            return False
        if first_open > 0:
            change_pct = (last_close / first_open) - 1.0
            if change_pct < PUMP_MIN_PRICE_CHANGE_5M_PCT:
                cprint(f"   🚫 Pump filter: 5m change {change_pct:.1%} < {PUMP_MIN_PRICE_CHANGE_5M_PCT:.0%}", 'red')
                return False
        cprint(f"   ✅ Pump filter passed: Vol=${total_vol:,.0f}, greens={greens}/5", 'green')
        return True
    except Exception as e:
        cprint(f"   ⚠️ Pump filter error: {e}", 'yellow')
        return False

def get_names(df):
    names = []  # List to hold the collected names

    for index, row in df.iterrows():
        token_mint_address = row['address']
        token_data = get_token_overview(token_mint_address)
        # Skip if name matches blocklist
        tname = str(token_data.get('name', '')).lower()
        if any(kw in tname for kw in NAME_BLOCKLIST_KEYWORDS):
            continue
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

    # Addresses to exclude from the portfolio display
    exclude_from_portfolio = []

    # Filter out SOL and USDC from the dataframe
    if not df.empty:
        df = df[~df['Mint Address'].isin(exclude_from_portfolio)]

    # Filter the dataframe based on the DO_NOT_TRADE_LIST and CLOSED_POSITIONS list
    if not df.empty:
        try:
            with open(CLOSED_POSITIONS_TXT, 'r') as f:
                closed_list = [line.strip() for line in f if line.strip()]
        except Exception:
            closed_list = []
        df = df[~df['Mint Address'].isin(DO_NOT_TRADE_LIST)]
        if closed_list:
            df = df[~df['Mint Address'].isin(closed_list)]

    # Print the DataFrame if it's not empty
    if not df.empty:
        df_with_values = get_names_nosave(df.copy())
        print('')
        df_display = df_with_values.drop(['Mint Address', 'Amount'], axis=1)
        print(df_display.head(20))
        cprint(f'💰 Kali: Current Portfolio Value: ${round(df_with_values["USD Value"].sum(),2)}', 'white', 'on_green')
        print(' ')
        time.sleep(7)
        return df_with_values
    else:
        cprint("❌ Kali: No wallet holdings to display.", 'white', 'on_red')
        time.sleep(30)
        return df

def fetch_wallet_token_single(address, token_mint_address):
    
    df = fetch_wallet_holdings_og(address)

    # filter by token mint address
    df = df[df['Mint Address'] == token_mint_address]

    return df


def get_token_balance_quiet(owner_address: str, token_mint_address: str) -> float:
    """Fast balance lookup for a specific token mint using RPC with mint filter."""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                owner_address,
                {"mint": token_mint_address},
                {"encoding": "jsonParsed"}
            ]
        }
        resp = requests.post(d.rpc_url, json=payload, timeout=8)
        if resp.status_code != 200:
            return 0.0
        data = resp.json().get('result', {}).get('value', [])
        total = 0.0
        for acc in data:
            try:
                amt = float(acc['account']['data']['parsed']['info']['tokenAmount']['uiAmount'] or 0)
                total += amt
            except Exception:
                continue
        return total
    except Exception:
        return 0.0


def get_position_fast(token_mint_address: str, retries: int = 12, delay_seconds: float = 2.0) -> float:
    """Retrying fast balance checker that avoids verbose portfolio logs and sleeps.
    Returns the token uiAmount or 0.0 after retries."""
    for attempt in range(retries):
        bal = get_token_balance_quiet(MY_SOLANA_ADDERESS, token_mint_address)
        if bal > 0:
            return bal
        if attempt < retries - 1:
            time.sleep(delay_seconds)
    return 0.0

def get_position(token_mint_address):
    """
    Fetches the balance of a specific token given its mint address from a DataFrame.
    Retries a few times if the token is not found immediately.
    """
    max_retries = 5
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        dataframe = fetch_wallet_token_single(MY_SOLANA_ADDERESS, token_mint_address)

        if not dataframe.empty:
            # Ensure 'Mint Address' column is treated as string for reliable comparison
            dataframe['Mint Address'] = dataframe['Mint Address'].astype(str)
            if dataframe['Mint Address'].isin([token_mint_address]).any():
                balance = dataframe.loc[dataframe['Mint Address'] == token_mint_address, 'Amount'].iloc[0]
                return balance

        if attempt < max_retries - 1:
            cprint(f"Token {token_mint_address[-6:]} not found, retrying in {retry_delay}s...", 'yellow')
            time.sleep(retry_delay)
        else:
            cprint(f"Token {token_mint_address[-6:]} not found after {max_retries} attempts.", 'red')
            return 0



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

    # Support both base58 strings and comma-separated byte arrays
    KEY = create_keypair_from_key(d.sol_key)
    QUOTE_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # usdc

    http_client = Client(d.rpc_url)

    base_quote = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}'
    swap_url = 'https://quote-api.jup.ag/v6/swap'
    
    # Initialize counter for swap transaction errors
    swap_error_count = 0
    max_retries = 50
    
    # Dynamic slippage attempts: 1% -> 5%
    for attempt_slippage in DYNAMIC_SLIPPAGE_STEPS_BPS:
        try:
            quote_url = f"{base_quote}&slippageBps={attempt_slippage}&restrictIntermediateTokens=true"
            quote = requests.get(quote_url).json()

            txRes = requests.post(swap_url,
                                  headers={"Content-Type": "application/json"},
                                  data=json.dumps({
                                      "quoteResponse": quote,
                                      "userPublicKey": str(KEY.pubkey()),
                                      "prioritizationFeeLamports": PRIORITY_FEE  # Hardcoded fee
                                  })).json()
                                  
            if 'swapTransaction' not in txRes:
                cprint(f"⚠️ Kali: No swapTransaction at slippage {attempt_slippage}bps, trying higher...", 'yellow')
                time.sleep(1)
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
    # If we reach here, all slippage attempts failed
    cprint(f"💀 Kali: All dynamic slippage attempts failed for {token[-4:]}", 'white', 'on_red')
    with open(PERMANENT_BLACKLIST, 'a') as f:
        f.write(f'{token}\n')
    with open(CLOSED_POSITIONS_TXT, 'a') as f:
        f.write(f'{token}\n')
    return False


def market_buy_fast(token_to_buy, usdc_amount_in_lamports, keypair, http_client):
    """
    KALI SPEED ENGINE: Ultra-fast market buy using Jupiter's v6 API with millisecond-level optimizations.
    Enhanced with error 0x1788 fixes and account pre-validation.
    
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
        
        # PRE-VALIDATION: Check if we have sufficient USDC balance
        try:
            # Get USDC balance using RPC call
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    str(keypair.pubkey()),
                    {"mint": usdc_mint},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            response = requests.post(d.rpc_url, json=payload, timeout=5)
            usdc_balance = 0.0
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'value' in data['result'] and data['result']['value']:
                    for account in data['result']['value']:
                        parsed_info = account['account']['data']['parsed']['info']
                        usdc_balance = float(parsed_info['tokenAmount']['uiAmount'] or 0)
                        break
            
            required_usdc = usdc_amount_in_lamports / 1_000_000  # Convert to USDC (6 decimals)
            
            if usdc_balance < required_usdc:
                cprint(f"🚨 Kali Speed Engine: Insufficient USDC balance. Have: {usdc_balance:.2f}, Need: {required_usdc:.2f}", 'red')
                return None
                
            cprint(f"✅ Kali Speed Engine: USDC balance check passed: {usdc_balance:.2f} USDC", 'green')
        except Exception as balance_error:
            cprint(f"⚠️ Kali Speed Engine: Balance check failed, proceeding anyway: {balance_error}", 'yellow')
        
        # 1. Get the quote with enhanced parameters for volatile tokens
        quote_url = (
            f"https://quote-api.jup.ag/v6/quote?"
            f"inputMint={usdc_mint}"
            f"&outputMint={token_to_buy}"
            f"&amount={usdc_amount_in_lamports}"
            f"&slippageBps=3000"  # Increased to 30% for highly volatile new tokens
            f"&onlyDirectRoutes=false"  # Allow more routes for better execution
            f"&maxAccounts=64"  # Increase account limit for complex routes
            f"&platformFeeBps=0"  # No platform fees for speed
        )
        
        quote_response = requests.get(quote_url, timeout=10).json()
        
        if 'error' in quote_response:
            cprint(f"🚨 Kali Speed Engine: Quote error for {token_to_buy[-6:]}: {quote_response.get('error')}", 'red')
            return None
            
        # Validate quote response
        if not quote_response.get('outAmount'):
            cprint(f"🚨 Kali Speed Engine: Invalid quote response - no output amount", 'red')
            return None

        # 2. Get the swap transaction with enhanced parameters
        swap_url = 'https://quote-api.jup.ag/v6/swap'
        swap_payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(keypair.pubkey()),
            "wrapAndUnwrapSol": True,
            # ENHANCED: Higher priority fee and compute optimization
            "prioritizationFeeLamports": 100000,  # Doubled for better execution
            "dynamicComputeUnitLimit": True,  # Optimize compute units
            "skipUserAccountsRpcCalls": False,  # Enable for account validation
            # FIX: Disable shared accounts to avoid "Simple AMMs not supported" error
            "restrictIntermediateTokens": False,  # Allow more routing options
            "useSharedAccounts": False,  # Changed to False to fix AMM error
            "asLegacyTransaction": False,  # Use versioned transactions
        }
        
        swap_response = requests.post(swap_url, json=swap_payload, timeout=10).json()
        
        if 'swapTransaction' not in swap_response:
            error_msg = swap_response.get('error', 'No swap transaction')
            cprint(f"🚨 Kali Speed Engine: Swap error for {token_to_buy[-6:]}: {error_msg}", 'red')
            
            # Handle specific error cases
            if 'slippage' in str(error_msg).lower():
                cprint(f"💡 Kali Speed Engine: Slippage error detected - token too volatile", 'yellow')
            elif 'liquidity' in str(error_msg).lower():
                cprint(f"💡 Kali Speed Engine: Liquidity error detected - insufficient pool depth", 'yellow')
            elif 'route' in str(error_msg).lower():
                cprint(f"💡 Kali Speed Engine: Routing error detected - no valid path found", 'yellow')
                
            return None

        # 3. Deserialize, sign, and send with ENHANCED ERROR HANDLING
        swap_tx_b64 = swap_response['swapTransaction']
        
        cprint(f"🔍 DEBUG: Transaction string type: {type(swap_tx_b64)}", 'yellow')
        cprint(f"🔍 DEBUG: Transaction length: {len(swap_tx_b64)}", 'yellow')
        cprint(f"🔍 DEBUG: First 50 chars: {swap_tx_b64[:50]}", 'yellow')
        
        # Clean the base64 string (remove any commas or invalid characters)
        swap_tx_b64_clean = swap_tx_b64.replace(',', '').replace(' ', '').strip()
        
        try:
            cprint(f"🔍 DEBUG: Attempting base64 decode...", 'yellow')
            raw_tx = base64.b64decode(swap_tx_b64_clean)
            cprint(f"🔍 DEBUG: Base64 decode successful, raw_tx length: {len(raw_tx)}", 'green')
            
            cprint(f"🔍 DEBUG: Attempting VersionedTransaction.from_bytes...", 'yellow')
            versioned_tx = VersionedTransaction.from_bytes(raw_tx)
            cprint(f"🔍 DEBUG: VersionedTransaction created successfully", 'green')
            
        except Exception as decode_error:
            cprint(f"🚨 Kali Speed Engine: Transaction decode error for {token_to_buy[-6:]}: {decode_error}", 'red')
            cprint(f"   Error type: {type(decode_error).__name__}", 'red')
            cprint(f"   Raw swap transaction (first 100 chars): {swap_tx_b64[:100]}...", 'yellow')
            import traceback
            cprint(f"   Full traceback: {traceback.format_exc()}", 'red')
            return None
        
        # Sign the transaction with your keypair
        signed_tx = VersionedTransaction(versioned_tx.message, [keypair])

        # ENHANCED: Better transmission settings to avoid 0x1788 errors
        # Using confirmed commitment for better success rate vs pure speed
        opts = TxOpts(
            skip_preflight=False,  # Enable preflight for error detection
            preflight_commitment=Commitment("confirmed"),  # More reliable than processed
            max_retries=1  # Allow one retry for reliability
        )
        
        cprint(f"🚀 Kali Speed Engine: Transmitting transaction for {token_to_buy[-6:]}", 'yellow', attrs=['bold'])
        
        try:
            # Send transaction with enhanced error handling
            tx_receipt = http_client.send_raw_transaction(bytes(signed_tx), opts=opts)
            tx_signature = tx_receipt.value
            
            cprint(f"✅ Kali Speed Engine: ULTRA-FAST BUY SUCCESS! 🚀", 'white', 'on_green', attrs=['bold'])
            cprint(f"💎 Token: {token_to_buy[-6:]} | TX: https://solscan.io/tx/{str(tx_signature)}", 'green', attrs=['bold'])
            
            # --- ADD THIS BLOCK FOR TELEGRAM ALERT ---
            try:
                token_name = get_token_overview(token_to_buy).get('name', 'Unknown Token')
                buy_size_usd = usdc_amount_in_lamports / 1_000_000
                solscan_link = f"https://solscan.io/tx/{tx_signature}"
                
                # Escape special characters for MarkdownV2
                token_name_safe = token_name.replace('-', '\\-').replace('.', '\\.').replace('_', '\\_')
                
                message = (
                    f"*🔥 KALI SNIPE SUCCESS 🔥*\n\n"
                    f"*Token:* `{token_name_safe}`\n"
                    f"*Address:* `{token_to_buy}`\n"
                    f"*Action:* BUY\n"
                    f"*Size:* ${buy_size_usd:.2f} USD\n\n"
                    f"[View on Solscan]({solscan_link})"
                )
                send_telegram_alert(message)
            except Exception as alert_error:
                cprint(f"⚠️ Failed to format or send BUY Telegram alert: {alert_error}", 'yellow')
            # --- END OF TELEGRAM ALERT BLOCK ---
            
            return str(tx_signature)
            
        except Exception as tx_error:
            error_str = str(tx_error)
            cprint(f"🚨 Kali Speed Engine: Transaction failed for {token_to_buy[-6:]}: {error_str}", 'red')
            
            # Analyze specific error patterns
            if "0x1788" in error_str or "6024" in error_str:
                cprint(f"💡 Kali Speed Engine: Error 0x1788 detected - AMM calculation issue", 'yellow')
                cprint(f"   → Possible causes: Insufficient liquidity, invalid route, or account issues", 'yellow')
            elif "0x1789" in error_str or "6025" in error_str:
                cprint(f"💡 Kali Speed Engine: Error 0x1789 detected - Slippage tolerance exceeded", 'yellow')
                cprint(f"   → Try increasing slippage tolerance in config", 'yellow')
            elif "0x1771" in error_str:
                cprint(f"💡 Kali Speed Engine: Error 0x1771 detected - Output amount below minimum", 'yellow')
            elif "insufficient" in error_str.lower():
                cprint(f"💡 Kali Speed Engine: Insufficient funds detected", 'yellow')
            elif "blockhash" in error_str.lower():
                cprint(f"💡 Kali Speed Engine: Blockhash expired - transaction took too long", 'yellow')
            
            return None

    except requests.exceptions.Timeout:
        cprint(f"⏰ Kali Speed Engine: Request timeout for {token_to_buy[-6:]}", 'red')
        return None
    except requests.exceptions.RequestException as e:
        cprint(f"🔄 Kali Speed Engine: Request failed for {token_to_buy[-6:]}: {e}", 'red')
        return None
    except Exception as e:
        cprint(f"❌ Kali Speed Engine: Fast buy error for {token_to_buy[-6:]}: {e}", 'red')
        return None


def market_sell(QUOTE_TOKEN, amount, slippage=SELL_SLIPPAGE_BPS):
    """
    KALI: Sells a token using Jupiter's v6 API with dynamic slippage.
    """
    import requests
    import json
    import base64
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    import dontshare as d

    KEY = create_keypair_from_key(d.sol_key)
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    http_client = Client(d.rpc_url)
    
    # 1. Get quote (no slippage needed in the quote request itself)
    quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={usdc_mint}&amount={amount}&restrictIntermediateTokens=true'
    
    try:
        quote = requests.get(quote_url, timeout=10).json()
        if not quote.get('outAmount'):
             cprint(f"⚠️ Kali: Could not get quote for selling {QUOTE_TOKEN[-6:]}. The pool may be unstable.", 'yellow')
             return False

        # 2. Get the swap transaction with the dynamicSlippage parameter
        swap_url = 'https://quote-api.jup.ag/v6/swap'
        swap_payload = {
            "quoteResponse": quote,
            "userPublicKey": str(KEY.pubkey()),
            "wrapAndUnwrapSol": True,
            "prioritizationFeeLamports": PRIORITY_FEE,
            "dynamicSlippage": {"minBps": 100, "maxBps": slippage} # min 1%, max from config
        }
        
        txRes = requests.post(swap_url, headers={"Content-Type": "application/json"}, data=json.dumps(swap_payload), timeout=10).json()

        if 'swapTransaction' not in txRes:
            error_msg = txRes.get('error', 'Unknown error')
            cprint(f"💀 Kali: Sell failed for {QUOTE_TOKEN[-6:]}. Jupiter API error: {error_msg}", 'white', 'on_red')
            # Blacklist on sell failure to avoid getting stuck in a loop
            with open(PERMANENT_BLACKLIST, 'a') as f:
                f.write(f'{QUOTE_TOKEN}\n')
            with open(CLOSED_POSITIONS_TXT, 'a') as f:
                f.write(f'{QUOTE_TOKEN}\n')
            return False

        # 3. Deserialize, sign, and send the transaction
        swapTx = base64.b64decode(txRes['swapTransaction'])
        tx1 = VersionedTransaction.from_bytes(swapTx)
        tx = VersionedTransaction(tx1.message, [KEY])
        txId = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
        cprint(f"🌟 Kali: Sell transaction successful! https://solscan.io/tx/{str(txId)}", 'white', 'on_green')
        return True

    except Exception as e:
        cprint(f"⚠️ Kali: An unexpected error occurred during market sell: {e}", 'white', 'on_red')
        return False

    cprint(f"💀 Kali: All dynamic slippage attempts failed for {QUOTE_TOKEN[-4:]} -> USDC (variant)", 'white', 'on_red')
    with open(PERMANENT_BLACKLIST, 'a') as f:
        f.write(f'{QUOTE_TOKEN}\n')
    with open(CLOSED_POSITIONS_TXT, 'a') as f:
        f.write(f'{QUOTE_TOKEN}\n')
    return False


def market_sell(QUOTE_TOKEN, amount, slippage=SELL_SLIPPAGE_BPS):

    import requests
    import json
    import base64
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    import dontshare as d 

    # Support both base58 strings and comma-separated byte arrays
    KEY = create_keypair_from_key(d.sol_key)
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
    """Close the position in full, with dust tolerance and correct precision.
    Sells repeatedly until USD value <= DUST_USD_THRESHOLD or balance is zero.
    """
    max_attempts = 8
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        balance = get_position(token_mint_address)
        price = ask_bid(token_mint_address) or 0
        usd_value = (balance or 0) * (price or 0)
        if usd_value <= DUST_USD_THRESHOLD or (balance or 0) <= 0:
            break

        try:
            decimals = get_decimals(token_mint_address)
        except Exception:
            decimals = 6
        lamports = int((balance or 0) * (10 ** decimals))
        # Safety: leave 1 lamport to avoid rounding errors, but try to clear as much as possible
        lamports = max(1, lamports - 1)

        try:
            ok = market_sell(token_mint_address, lamports)
            if ok:
                cprint(f'just made an order {token_mint_address[-4:]} selling {lamports} ...', 'white', 'on_blue')
            time.sleep(2)
        except Exception as e:
            cprint(f'order error.. trying again: {e}', 'white', 'on_red')
            time.sleep(2)

    # Mark as closed to prevent re-entry
    try:
        with open(CLOSED_POSITIONS_TXT, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
        if token_mint_address not in lines:
            with open(CLOSED_POSITIONS_TXT, 'a') as f:
                f.write(token_mint_address + '\n')
    except Exception:
        pass
    print('closing position in full...')


def append_recent_exit(token_mint_address: str):
    """Record a recent full exit to a small file for cross-process cooldown guards."""
    try:
        os.makedirs('./data', exist_ok=True)
        with open('./data/recently_exited.txt', 'a') as f:
            f.write(f"{token_mint_address},{int(time.time())}\n")
    except Exception:
        pass


def is_recently_exited(token_mint_address: str, within_seconds: int = 180) -> bool:
    """Return True if this mint was fully exited within the last N seconds.
    Used by listeners to avoid immediate re-entry after exits.
    """
    try:
        path = './data/recently_exited.txt'
        if not os.path.exists(path):
            return False
        now = int(time.time())
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) != 2:
                    continue
                mint, ts = parts
                if mint == token_mint_address:
                    try:
                        if now - int(ts) <= within_seconds:
                            return True
                    except Exception:
                        continue
        return False
    except Exception:
        return False


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
            
        except Exception as e:
            cprint(f'order error.. trying again: {e}', 'white', 'on_red')

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

    # === FIXED SIZE STRATEGY: USE CONFIGURED USDC_SIZE ===
    # Using fixed $3 trades as per user configuration
    
    price = ask_bid(token_mint_address)
    if not price:
        cprint(f'⚠️ Kali: Could not get price for {token_mint_address[-6:]}, skipping', 'white', 'on_red')
        return

    try:
        # Use fixed USDC_SIZE for all trades
        fixed_buy_size = USDC_SIZE  # $3 as configured
        size_needed_lamports = int(fixed_buy_size * 10**6)  # Convert USDC to lamports
        size_needed_str = str(size_needed_lamports)

        cprint(f'🚀 Kali Strategy: Executing fixed position', 'white', 'on_green', attrs=['bold'])
        cprint(f'   Size: ${fixed_buy_size:.2f} USDC ({size_needed_lamports:,} lamports)', 'green')

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
                
                # === STRATEGY: RECORD POSITION STATE FOR TIERED MANAGEMENT ===
                record_new_position(token_mint_address, fixed_buy_size, liquidity)
                
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
                    record_new_position(token_mint_address, fixed_buy_size, liquidity)
                    
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
        record_new_position(token_mint_address, fixed_buy_size, liquidity)
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

