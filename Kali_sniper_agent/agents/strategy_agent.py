import asyncio
from agents.base_agent import BaseAgent
from common.messaging import consume_messages, VETTED_TOKENS_QUEUE
import json
import aio_pika
from termcolor import cprint
import dontshare as d
from config import *
from solders.keypair import Keypair
from solana.rpc.api import Client
from common.strategy_utils import advanced_pnl_management
from common.state import record_new_position, load_position_states
from common.sell_utils import kill_switch, market_sell
import requests
from common.utils import create_keypair_from_key
import base64
from solders.transaction import VersionedTransaction
from solana.rpc.types import TxOpts, Commitment

def get_token_overview(address):
    try:
        API_KEY = d.birdeye
        url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
        headers = {"X-API-KEY": API_KEY}
        response = requests.get(url, headers=headers, timeout=8)
        if response.ok:
            json_response = response.json()
            data = json_response.get('data', {})
            if data and 'liquidity' in data:
                if data['liquidity'] is None:
                    data['liquidity'] = 0
            return data or {}
        else:
            cprint(f"⚠️ Kali: Error fetching overview for {address[-6:]}: {response.status_code}", 'yellow')
            return {}
    except Exception as e:
        cprint(f"⚠️ Kali: Exception in get_token_overview: {e}", 'yellow')
        return {}

def calculate_dynamic_position_size(token_address, liquidity):
    try:
        if not ENABLE_DYNAMIC_SIZING:
            return USDC_SIZE
        if liquidity <= 0:
            return USDC_MIN_BUY_SIZE
        target_size = liquidity * USDC_BUY_TARGET_PERCENT_OF_LP
        actual_size = max(USDC_MIN_BUY_SIZE, min(target_size, USDC_MAX_BUY_SIZE))
        return actual_size
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error calculating dynamic size: {e}", 'red')
        return USDC_MIN_BUY_SIZE

def market_buy_fast(token_to_buy, usdc_amount_in_lamports, keypair, http_client):
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    try:
        quote_url = (
            f"https://quote-api.jup.ag/v6/quote?"
            f"inputMint={usdc_mint}"
            f"&outputMint={token_to_buy}"
            f"&amount={usdc_amount_in_lamports}"
            f"&slippageBps=3000"
            f"&onlyDirectRoutes=false"
            f"&maxAccounts=64"
            f"&platformFeeBps=0"
        )
        quote_response = requests.get(quote_url, timeout=10).json()
        if 'error' in quote_response:
            cprint(f"🚨 Kali Speed Engine: Quote error for {token_to_buy[-6:]}: {quote_response.get('error')}", 'red')
            return None
        if not quote_response.get('outAmount'):
            cprint(f"🚨 Kali Speed Engine: Invalid quote response - no output amount", 'red')
            return None
        swap_url = 'https://quote-api.jup.ag/v6/swap'
        swap_payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(keypair.pubkey()),
            "wrapAndUnwrapSol": True,
            "prioritizationFeeLamports": 100000,
            "dynamicComputeUnitLimit": True,
            "skipUserAccountsRpcCalls": False,
            "restrictIntermediateTokens": False,
            "useSharedAccounts": False,
            "asLegacyTransaction": False,
        }
        swap_response = requests.post(swap_url, json=swap_payload, timeout=10).json()
        if 'swapTransaction' not in swap_response:
            error_msg = swap_response.get('error', 'No swap transaction')
            cprint(f"🚨 Kali Speed Engine: Swap error for {token_to_buy[-6:]}: {error_msg}", 'red')
            return None
        swap_tx_b64 = swap_response['swapTransaction']
        raw_tx = base64.b64decode(swap_tx_b64)
        versioned_tx = VersionedTransaction.from_bytes(raw_tx)
        signed_tx = VersionedTransaction(versioned_tx.message, [keypair])
        opts = TxOpts(
            skip_preflight=False,
            preflight_commitment=Commitment("confirmed"),
            max_retries=1
        )
        try:
            tx_receipt = http_client.send_raw_transaction(bytes(signed_tx), opts=opts)
            tx_signature = tx_receipt.value
            cprint(f"✅ Kali Speed Engine: Fast buy SUCCESS! TX: https://solscan.io/tx/{str(tx_signature)}", 'green', attrs=['bold'])
            return str(tx_signature)
        except Exception as tx_error:
            error_str = str(tx_error)
            cprint(f"❌ Kali Speed Engine: Transaction failed for {token_to_buy[-6:]}: {error_str}", 'red')
            
            # Analyze specific error patterns
            if "0x1788" in error_str or "6024" in error_str:
                cprint(f"💡 Error 0x1788: AMM calculation issue - Pool may be too new or illiquid", 'yellow')
                cprint(f"   Retrying with legacy transaction...", 'yellow')
                # Try again with legacy transaction
                swap_payload["asLegacyTransaction"] = True
                swap_payload["useSharedAccounts"] = False
                retry_response = requests.post(swap_url, json=swap_payload, timeout=10).json()
                if 'swapTransaction' in retry_response:
                    retry_tx = base64.b64decode(retry_response['swapTransaction'])
                    retry_versioned = VersionedTransaction.from_bytes(retry_tx)
                    retry_signed = VersionedTransaction(retry_versioned.message, [keypair])
                    try:
                        retry_receipt = http_client.send_raw_transaction(bytes(retry_signed), opts=opts)
                        cprint(f"✅ Retry successful! TX: {retry_receipt.value}", 'green')
                        return str(retry_receipt.value)
                    except:
                        pass
            elif "0x1789" in error_str or "6025" in error_str:
                cprint(f"💡 Error 0x1789: Slippage tolerance exceeded", 'yellow')
            elif "insufficient" in error_str.lower():
                cprint(f"💡 Insufficient funds detected", 'yellow')
            return None
    except Exception as e:
        cprint(f"❌ Kali Speed Engine: Fast buy error for {token_to_buy[-6:]}: {e}", 'red')
        return None

async def market_sell_fast(token_to_sell, amount, keypair, http_client):
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    try:
        # Get decimals
        token_overview = get_token_overview(token_to_sell)
        decimals = token_overview.get('decimals', 6)
        amount_in_lamports = int(amount * (10**decimals))

        quote_url = (
            f"https://quote-api.jup.ag/v6/quote?"
            f"inputMint={token_to_sell}"
            f"&outputMint={usdc_mint}"
            f"&amount={amount_in_lamports}"
            f"&slippageBps=3000"
            f"&onlyDirectRoutes=false"
            f"&maxAccounts=64"
            f"&platformFeeBps=0"
        )
        quote_response = requests.get(quote_url, timeout=10).json()
        if 'error' in quote_response:
            cprint(f"🚨 Kali Speed Engine: Quote error for {token_to_sell[-6:]}: {quote_response.get('error')}", 'red')
            return None
        if not quote_response.get('outAmount'):
            cprint(f"🚨 Kali Speed Engine: Invalid quote response - no output amount", 'red')
            return None
        swap_url = 'https://quote-api.jup.ag/v6/swap'
        swap_payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(keypair.pubkey()),
            "wrapAndUnwrapSol": True,
            "prioritizationFeeLamports": 100000,
            "dynamicComputeUnitLimit": True,
            "skipUserAccountsRpcCalls": False,
            "restrictIntermediateTokens": False,
            "useSharedAccounts": False,
            "asLegacyTransaction": False,
        }
        swap_response = requests.post(swap_url, json=swap_payload, timeout=10).json()
        if 'swapTransaction' not in swap_response:
            error_msg = swap_response.get('error', 'No swap transaction')
            cprint(f"🚨 Kali Speed Engine: Swap error for {token_to_sell[-6:]}: {error_msg}", 'red')
            return None
        swap_tx_b64 = swap_response['swapTransaction']
        raw_tx = base64.b64decode(swap_tx_b64)
        versioned_tx = VersionedTransaction.from_bytes(raw_tx)
        signed_tx = VersionedTransaction(versioned_tx.message, [keypair])
        opts = TxOpts(
            skip_preflight=False,
            preflight_commitment=Commitment("confirmed"),
            max_retries=1
        )
        tx_receipt = http_client.send_raw_transaction(bytes(signed_tx), opts=opts)
        return str(tx_receipt.value)
    except Exception as e:
        cprint(f"❌ Kali Speed Engine: Fast sell error for {token_to_sell[-6:]}: {e}", 'red')
        return None

class StrategyAgent(BaseAgent):
    async def run(self):
        await self.initialize()
        snipe_task = asyncio.create_task(self.listen_for_buys())
        pnl_task = asyncio.create_task(self.manage_positions())
        await asyncio.gather(snipe_task, pnl_task)

    async def listen_for_buys(self):
        await consume_messages(self.channel, VETTED_TOKENS_QUEUE, self.execute_snipe)

    async def execute_snipe(self, message: aio_pika.IncomingMessage):
        async with message.process():
            open_positions = load_position_states()
            if len(open_positions) >= MAX_POSITIONS:
                cprint(f"🔒 StrategyAgent: Max positions ({MAX_POSITIONS}) reached. Skipping snipe.", 'yellow')
                return

            data = json.loads(message.body.decode())
            token_to_buy = data["mint"]
            cprint(f"📈 StrategyAgent: Received approved token {token_to_buy[-6:]}", 'green')
            try:
                token_overview = get_token_overview(token_to_buy)
                liquidity = 0
                if token_overview and isinstance(token_overview, dict):
                    liquidity = token_overview.get('liquidity', 0)
                    if liquidity is None or not isinstance(liquidity, (int, float)):
                        liquidity = 0
                if liquidity > 0:
                    dynamic_size = calculate_dynamic_position_size(token_to_buy, liquidity)
                    usdc_amount_lamports = int(dynamic_size * 1000000)
                    keypair = create_keypair_from_key(d.sol_key)
                    http_client = Client(d.rpc_url)
                    success = market_buy_fast(token_to_buy, usdc_amount_lamports, keypair, http_client)
                    if success:
                        record_new_position(token_to_buy, dynamic_size, liquidity)
                        cprint(f"📈 StrategyAgent: Successfully sniped {token_to_buy[-6:]}", 'green')
                else:
                    cprint(f"⚠️ StrategyAgent: No liquidity data for {token_to_buy[-6:]}, using fallback size", 'yellow')
                    dynamic_size = USDC_SIZE
                    usdc_amount_lamports = int(USDC_SIZE * 1000000)
                    keypair = create_keypair_from_key(d.sol_key)
                    http_client = Client(d.rpc_url)
                    success = market_buy_fast(token_to_buy, usdc_amount_lamports, keypair, http_client)
                    if success:
                        record_new_position(token_to_buy, dynamic_size, 0)
                        cprint(f"📈 StrategyAgent: Successfully sniped {token_to_buy[-6:]}", 'green')
            except Exception as e:
                cprint(f"❌ StrategyAgent: Error in snipe execution: {e}", 'red')

    async def manage_positions(self):
        while True:
            cprint("📊 StrategyAgent: Running PNL management cycle...", 'blue')
            try:
                advanced_pnl_management()
            except Exception as e:
                cprint(f"❌ StrategyAgent: Error in PNL management: {e}", 'red')
            await asyncio.sleep(30)