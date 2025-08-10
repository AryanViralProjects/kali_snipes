"""
Token utility functions for price, balance, and decimals
"""

import requests
import json
import base64
import math
import time
import pandas as pd
from termcolor import cprint
import dontshare as d
from config import MY_SOLANA_ADDERESS

def ask_bid(token_mint_address):
    """Returns the price of a token"""
    API_KEY = d.birdeye
    
    url = f"https://public-api.birdeye.so/defi/price?address={token_mint_address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        json_response = response.json()
        if 'data' in json_response and 'value' in json_response['data']:
            return json_response['data']['value']
        else:
            return 0
    else:
        return 0

def get_decimals(token_mint_address):
    """Get token decimals from Solana"""
    url = "https://api.mainnet-beta.solana.com/"
    headers = {"Content-Type": "application/json"}

    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [
            token_mint_address,
            {"encoding": "jsonParsed"}
        ]
    })

    response = requests.post(url, headers=headers, data=payload)
    
    try:
        account_info = response.json()
        if 'result' in account_info and account_info['result'] is not None:
            parsed_data = account_info['result']['value']['data']['parsed']['info']
            decimals = parsed_data['decimals']
            return decimals
        else:
            print(f"No account info found for {token_mint_address}")
            return None
    except KeyError as e:
        print(f"Error extracting decimals: {e}")
        return None

def round_down(value, decimals):
    """Round down to specified decimals"""
    factor = 10 ** decimals
    return math.floor(value * factor) / factor

def fetch_wallet_token_single(address, token_mint_address):
    """Fetch balance of a single token"""
    from solana.rpc.api import Client
    
    solana_client = Client("https://api.mainnet-beta.solana.com/")
    response = solana_client.get_token_accounts_by_owner_json_parsed(
        address, 
        {"mint": token_mint_address}
    )
    
    data = []
    if response.value:
        for account in response.value:
            token_info = account.account.data.parsed['info']
            mint_address = token_info['mint']
            amount = float(token_info['tokenAmount']['uiAmount'])
            data.append({
                'Mint Address': mint_address,
                'Amount': amount
            })
    
    df = pd.DataFrame(data)
    return df

def get_position(token_mint_address):
    """
    Fetches the balance of a specific token given its mint address.
    Returns the balance if found, otherwise 0.
    """
    dataframe = fetch_wallet_token_single(MY_SOLANA_ADDERESS, token_mint_address)
    
    if dataframe.empty:
        return 0
    
    dataframe['Mint Address'] = dataframe['Mint Address'].astype(str)
    
    if dataframe['Mint Address'].isin([token_mint_address]).any():
        balance = dataframe.loc[dataframe['Mint Address'] == token_mint_address, 'Amount'].iloc[0]
        return balance
    else:
        return 0