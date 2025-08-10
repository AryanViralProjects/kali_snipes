from agents.base_agent import BaseAgent
from common.messaging import consume_messages, publish_message, NEW_POOL_QUEUE, VETTED_TOKENS_QUEUE
import json
import aio_pika
import dontshare as d
from config import *
from termcolor import cprint
import requests
import time
import asyncio

# Copied from nice_funcs.py
def pre_trade_token_vetting(token_address, birdeye_api_key, helius_rpc_url):
    cprint(f"🔬 Kali Intelligence: Vetting token {token_address[-6:]}", 'yellow', attrs=['bold'])
    max_retries = 8
    retry_delay = 5.0
    for attempt in range(max_retries):
        try:
            sec_url = f"https://public-api.birdeye.so/defi/token_security?address={token_address}"
            sec_headers = {"X-API-KEY": birdeye_api_key}
            sec_response = requests.get(sec_url, headers=sec_headers, timeout=8)
            if sec_response.status_code == 200:
                break
            elif sec_response.status_code in [555, 404, 500, 502, 503]:
                if attempt < max_retries - 1:
                    cprint(f"   ⏳ Token data not ready (Code: {sec_response.status_code}), retrying in {retry_delay}s... (attempt {attempt + 1})", 'yellow')
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                else:
                    cprint(f"   🚨 VETTING FAILED: Birdeye security API error after {max_retries} attempts (Code: {sec_response.status_code})", 'red')
                    return False
            else:
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
    security_data = sec_response.json().get('data', {})
    if not security_data:
        cprint("   🚨 VETTING FAILED: No security data returned from Birdeye", 'red')
        return False
    if REJECT_FAKE_TOKENS and security_data.get('fakeToken'):
        cprint("   🚨 VETTING FAILED: FAKE TOKEN - Scam/imitation detected", 'red')
        return False
    if not security_data.get('ownershipRenounced', False):
        if REJECT_NON_RENOUNCED_OWNERSHIP:
            cprint("   🚨 VETTING FAILED: OWNERSHIP NOT RENOUNCED - Owner can change parameters", 'red')
            return False
        else:
            cprint("   ⚠️ WARNING: OWNERSHIP NOT RENOUNCED - Owner retains control (RISK ACCEPTED)", 'red')
    if REJECT_HONEYPOTS and security_data.get('honeypot'):
        cprint("   🚨 VETTING FAILED: HONEYPOT - Buyers cannot sell", 'red')
        return False
    if REJECT_FREEZABLE_TOKENS and security_data.get('freezable'):
        cprint("   🚨 VETTING FAILED: FREEZABLE - Can freeze token transfers", 'red')
        return False
    if REJECT_FREEZABLE_TOKENS and security_data.get('freezeAuthority') is not None:
        cprint("   🚨 VETTING FAILED: FREEZE AUTHORITY EXISTS", 'red')
        return False
    if REJECT_TOKEN_2022 and security_data.get('isToken2022'):
        cprint("   🚨 VETTING FAILED: TOKEN 2022 PROGRAM - Experimental standard", 'red')
        return False
    if REJECT_MINTABLE_TOKENS and security_data.get('mintable'):
        cprint("   🚨 VETTING FAILED: MINTABLE - Can create infinite supply", 'red')
        return False
    if security_data.get('mutableMetadata'):
        if REJECT_MUTABLE_METADATA:
            cprint("   🚨 VETTING FAILED: MUTABLE METADATA - Can change name/logo", 'red')
            return False
        else:
            cprint("   ⚠️ INFO: MUTABLE METADATA detected - Token can change name/logo (allowed)", 'yellow')
    if REJECT_TRANSFER_FEES and security_data.get('transferFees'):
        cprint("   🚨 VETTING FAILED: TRANSFER FEES - Charges fees on transfers", 'red')
        return False
    buy_tax = security_data.get('buyTax', 0)
    if buy_tax is not None and isinstance(buy_tax, (int, float)) and buy_tax > MAX_BUY_TAX:
        cprint(f"   🚨 VETTING FAILED: BUY TAX {buy_tax:.1%} > {MAX_BUY_TAX:.1%}", 'red')
        return False
    sell_tax = security_data.get('sellTax', 0)
    if sell_tax is not None and isinstance(sell_tax, (int, float)) and sell_tax > MAX_SELL_TAX:
        cprint(f"   🚨 VETTING FAILED: SELL TAX {sell_tax:.1%} > {MAX_SELL_TAX:.1%}", 'red')
        return False
    owner_pct = security_data.get('ownerPercentage', 0)
    if owner_pct is not None and isinstance(owner_pct, (int, float)) and owner_pct > MAX_OWNER_PERCENTAGE:
        cprint(f"   🚨 VETTING FAILED: OWNER HOLDS {owner_pct:.1%} > {MAX_OWNER_PERCENTAGE:.1%}", 'red')
        return False
    ua_pct = security_data.get('updateAuthorityPercentage', 0)
    if ua_pct is not None and isinstance(ua_pct, (int, float)) and ua_pct > MAX_UPDATE_AUTHORITY_PERCENTAGE:
        cprint(f"   🚨 VETTING FAILED: UPDATE AUTHORITY HOLDS {ua_pct:.1%} > {MAX_UPDATE_AUTHORITY_PERCENTAGE:.1%}", 'red')
        return False
    top_10_pct = security_data.get('top10HolderPercent', 1.0)
    if top_10_pct is not None and isinstance(top_10_pct, (int, float)) and top_10_pct > MAX_TOP10_HOLDER_PERCENT:
        cprint(f"   🚨 VETTING FAILED: TOP 10 HOLDERS {top_10_pct:.1%} > {MAX_TOP10_HOLDER_PERCENT:.1%}", 'red')
        return False
    if security_data.get('mutableInfo'):
        if not ALLOW_MUTABLE_INFO:
            cprint("   ⚠️ VETTING FAILED: MUTABLE INFO - Token info can be changed", 'yellow')
            return False
        else:
            cprint("   ℹ️ INFO: MUTABLE INFO detected - Additional token info can be changed (allowed)", 'cyan')
    cprint("   ✅ ALL SECURITY CHECKS PASSED", 'green')
    max_retries_overview = 8
    retry_delay_overview = 5.0
    for attempt in range(max_retries_overview):
        try:
            overview_url = f"https://public-api.birdeye.so/defi/token_overview?address={token_address}"
            overview_headers = {"X-API-KEY": birdeye_api_key}
            overview_response = requests.get(overview_url, headers=overview_headers, timeout=8)
            if overview_response.status_code == 200:
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
    overview_data = overview_response.json().get('data', {})
    if not overview_data:
        cprint("   🚨 VETTING FAILED: No overview data returned from Birdeye", 'red')
        return False
    liquidity = overview_data.get('liquidity', 0)
    market_cap = overview_data.get('mc', 0)
    if liquidity is None:
        liquidity = 0
    if market_cap is None:
        market_cap = 0
    if isinstance(liquidity, (int, float)) and liquidity < MIN_LIQUIDITY:
        cprint(f"   🚨 VETTING FAILED: Insufficient liquidity (${liquidity:,.2f} < ${MIN_LIQUIDITY:,.2f})", 'red')
        return False
    if isinstance(market_cap, (int, float)) and market_cap > MAX_MARKET_CAP:
        cprint(f"   🚨 VETTING FAILED: Market cap too high (${market_cap:,.2f} > ${MAX_MARKET_CAP:,.2f})", 'red')
        return False
    cprint(f"   ✅ Market checks passed (Liquidity: ${liquidity:,.0f}, MC: ${market_cap:,.0f})", 'green')
    try:
        creation_time = overview_data.get('creation_time') or overview_data.get('createdAt')
        if creation_time:
            import time
            current_time = time.time()
            if isinstance(creation_time, str):
                from datetime import datetime
                try:
                    creation_timestamp = datetime.fromisoformat(creation_time.replace('Z', '+00:00')).timestamp()
                except:
                    try:
                        creation_timestamp = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
                    except:
                        creation_timestamp = None
            else:
                creation_timestamp = creation_time
            if creation_timestamp:
                token_age_hours = (current_time - creation_timestamp) / 3600
                from config import MAX_TOKEN_AGE_HOURS
                if token_age_hours > MAX_TOKEN_AGE_HOURS:
                    cprint(f"   🚨 VETTING FAILED: Token too old ({token_age_hours:.1f}h > {MAX_TOKEN_AGE_HOURS}h)", 'red')
                    return False
                else:
                    cprint(f"   ✅ Token age check passed: {token_age_hours:.1f}h old", 'green')
            else:
                if liquidity > 1000000 or market_cap > 1000000:
                    cprint(f"   🚨 VETTING FAILED: High liquidity/MC suggests old token (Liq: ${liquidity:,.0f}, MC: ${market_cap:,.0f})", 'red')
                    return False
                cprint("   🚨 VETTING FAILED: Could not verify token age (strict mode)", 'red')
                return False
        else:
            if liquidity > 100000 or market_cap > 100000:
                cprint(f"   🚨 VETTING FAILED: No age data + high metrics = likely old (Liq: ${liquidity:,.0f}, MC: ${market_cap:,.0f})", 'red')
                return False
            elif liquidity < 50000:
                cprint(f"   ⚠️ WARNING: No age data but low liquidity (${liquidity:,.0f}) - likely new token, proceeding", 'yellow')
            else:
                cprint(f"   🚨 VETTING FAILED: No age data with moderate liquidity (${liquidity:,.0f}) - too risky", 'red')
                return False
    except Exception as age_error:
        cprint(f"   🚨 VETTING FAILED: Error checking token age: {age_error} (strict mode)", 'red')
        return False
    deployer = get_deployer_address(token_address, birdeye_api_key)
    if check_deployer_blacklist(deployer):
        return False
    if deployer:
        cprint(f"   ✅ Deployer check passed: {deployer[-6:]}", 'green')
    else:
        cprint("   ⚠️ Could not verify deployer (proceeding anyway)", 'yellow')
    cprint(f"   🎯 INTELLIGENCE VETTING PASSED: Token {token_address[-6:]} approved for trading!", 'white', 'on_green', attrs=['bold'])
    return True

def get_deployer_address(token_address, birdeye_api_key):
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
    if not deployer_address:
        return False
    try:
        import os
        blacklist_file = './data/deployer_blacklist.txt'
        if not os.path.exists(blacklist_file):
            with open(blacklist_file, 'w') as f:
                f.write("# Deployer wallet blacklist - one address per line\n")
                f.write("# Format: wallet_address,reason\n")
            return False
        with open(blacklist_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    blacklisted_address = line.split(',')[0].strip()
                    if deployer_address == blacklisted_address:
                        reason = line.split(',')[1].strip() if ',' in line else "blacklisted deployer"
                        cprint(f"   🚨 VETTING FAILED: Deployer {deployer_address[-6:]} is blacklisted ({reason})", 'red', attrs=['bold'])
                        return True
    except Exception as e:
        cprint(f"   ⚠️ Error checking deployer blacklist: {e}", 'yellow')
        return False
    return False

class IntelligenceAgent(BaseAgent):
    async def run(self):
        await self.initialize()
        await consume_messages(self.channel, NEW_POOL_QUEUE, self.process_pool_event)

    async def process_pool_event(self, message: aio_pika.IncomingMessage):
        async with message.process():
            data = json.loads(message.body.decode())
            token_to_vet = data["base_mint"]
            is_safe = pre_trade_token_vetting(token_to_vet, d.birdeye, d.rpc_url)
            if is_safe:
                approval_event = {
                    "type": "TokenApproved",
                    "mint": token_to_vet,
                    "signature": data["signature"]
                }
                await publish_message(self.channel, VETTED_TOKENS_QUEUE, approval_event)