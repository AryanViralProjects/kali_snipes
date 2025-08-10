from solders.keypair import Keypair
from termcolor import cprint
import requests
import dontshare as d
from config import MY_SOLANA_ADDERESS, USDC_CA

def create_keypair_from_key(key_data):
    """
    🔑 KALI: Create keypair from various key formats
    Handles both base58 strings and comma-separated byte arrays
    """
    try:
        if ',' in str(key_data):
            byte_values = [int(x.strip()) for x in str(key_data).split(',')]
            return Keypair.from_bytes(bytes(byte_values))
        else:
            return Keypair.from_base58_string(key_data)
    except Exception as e:
        cprint(f"❌ Kali: Error creating keypair: {e}", 'red')
        raise

def get_sol_balance(wallet_address):
    try:
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
                sol_amount = data['result']['value'] / 1000000000
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

def get_usdc_balance(wallet_address):
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"mint": USDC_CA},
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
        return usdc_balance
    except Exception as e:
        cprint(f"⚠️ Kali: Error getting USDC balance: {e}", 'yellow')
        return 0.0