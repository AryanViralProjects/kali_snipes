import json
import websockets
import asyncio
from agents.base_agent import BaseAgent
from common.messaging import publish_message, NEW_POOL_QUEUE
import dontshare as d
from config import RAYDIUM_LP_V4, USDC_CA
from termcolor import cprint
import requests

def get_helius_wss_url():
    """Convert Helius HTTP RPC URL to WebSocket URL"""
    http_url = d.rpc_url
    if "helius-rpc.com" in http_url:
        if "?api-key=" in http_url:
            api_key = http_url.split("?api-key=")[1]
            wss_url = f"wss://mainnet.helius-rpc.com/?api-key={api_key}"
        else:
            wss_url = http_url.replace("https://", "wss://")
        return wss_url
    else:
        cprint("⚠️ Kali: Unable to convert RPC URL to WebSocket. Please check your Helius RPC URL.", 'red')
        return None

class SpeedAgent(BaseAgent):
    async def run(self):
        await self.initialize()
        await self.listen_for_new_pools()

    async def listen_for_new_pools(self):
        wss_url = get_helius_wss_url()
        if not wss_url:
            return

        request = {
            "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
            "params": [{"mentions": [RAYDIUM_LP_V4]}, {"commitment": "processed"}]
        }
        while True:
            try:
                async with websockets.connect(wss_url) as websocket:
                    await websocket.send(json.dumps(request))
                    cprint("👂 SpeedAgent: Listening for new pools...", 'cyan')
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        if self.is_new_pool(data):
                            base_mint, quote_mint, signature = await self.extract_mints(data)
                            if base_mint and quote_mint and signature:
                                pool_event = {
                                    "type": "NewPoolDetected",
                                    "base_mint": base_mint,
                                    "quote_mint": quote_mint,
                                    "signature": signature
                                }
                                await publish_message(self.channel, NEW_POOL_QUEUE, pool_event)
            except Exception as e:
                cprint(f"SpeedAgent Error: {e}", 'red')
                await asyncio.sleep(5) # Reconnect after 5 seconds

    def is_new_pool(self, data):
        if data.get("method") == "logsNotification":
            logs = data.get("params", {}).get("result", {}).get("value", {}).get("logs", [])
            pool_creation_patterns = ["InitializeAccount3", "InitializeAccount", "initialize2"]
            for pattern in pool_creation_patterns:
                for log in logs:
                    if "Program log: Instruction:" in log and pattern in log:
                        return True
        return False

    async def extract_mints(self, data):
        signature = data.get("params", {}).get("result", {}).get("value", {}).get("signature")
        if not signature:
            return None, None, None

        max_retries = 5
        retry_delay = 0.5
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
                            "commitment": "confirmed"
                        }
                    ]
                }
                async with asyncio.timeout(15):
                    response = requests.post(d.rpc_url, json=payload)
                    if response.status_code == 200:
                        tx_data = response.json()
                        if 'result' in tx_data and tx_data['result']:
                            transaction = tx_data['result']
                            if 'meta' in transaction and 'postTokenBalances' in transaction['meta']:
                                for balance in transaction['meta']['postTokenBalances']:
                                    mint = balance.get('mint')
                                    if mint and mint != USDC_CA and mint != "So11111111111111111111111111111111111111112":
                                        return mint, USDC_CA, signature
            except Exception as e:
                cprint(f"SpeedAgent: Error extracting mints (attempt {attempt + 1}): {e}", 'yellow')
                await asyncio.sleep(retry_delay)
                retry_delay *= 1.5
        return None, None, None
