from termcolor import cprint
from config import *
import dontshare as d
import pandas as pd
import requests
import time
import json
import base64
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.transaction import VersionedTransaction
from solana.rpc.types import TxOpts, Commitment
from common.state import *
from common.token_utils import get_position, ask_bid, get_decimals, round_down
from common.sell_utils import kill_switch, market_sell

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

def get_names_nosave(df):
    names = []
    usd_values = []
    for index, row in df.iterrows():
        token_mint_address = row['Mint Address']
        amount = row['Amount']
        token_data = get_token_overview(token_mint_address)
        token_name = token_data.get('name', f'Token-{token_mint_address[-6:]}')
        names.append(token_name)
        try:
            if token_data and 'price' in token_data:
                price = float(token_data.get('price', 0))
                usd_value = amount * price
            else:
                price = ask_bid(token_mint_address)
                if price and price > 0:
                    usd_value = amount * float(price)
                else:
                    usd_value = 0.0
            usd_values.append(round(usd_value, 2))
        except Exception as e:
            cprint(f"⚠️ Kali: Error calculating USD value for {token_name}: {e}", 'yellow')
            usd_values.append(0.0)
    if 'name' in df.columns:
        df['name'] = names
    else:
        df.insert(0, 'name', names)
    df['USD Value'] = usd_values
    df_display = df.drop(['Mint Address', 'Amount'], axis=1)
    return df_display

def fetch_wallet_holdings_og(address):
    df = pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])
    try:
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
                        if amount > 0:
                            holdings_data.append({
                                'Mint Address': mint_address,
                                'Amount': amount,
                                'USD Value': 0.0
                            })
                    except Exception as e:
                        continue
                if holdings_data:
                    df = pd.DataFrame(holdings_data)
                    df = df[df['Amount'] > 0]
    except Exception as e:
        cprint(f"❌ Kali: Error fetching wallet holdings: {str(e)}", 'white', 'on_red')
    exclude_addresses = ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111112']
    updated_dont_trade_list = [mint for mint in DO_NOT_TRADE_LIST if mint not in exclude_addresses]
    for mint in updated_dont_trade_list:
        df = df[df['Mint Address'] != mint]
    if not df.empty:
        df2 = get_names_nosave(df.copy())
        cprint(f'💰 Kali: Current Portfolio Value: ${round(df2["USD Value"].sum(),2)}', 'white', 'on_green')
    return df

def get_position(token_mint_address):
    dataframe = fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
    if dataframe.empty:
        return 0
    dataframe['Mint Address'] = dataframe['Mint Address'].astype(str)
    if dataframe['Mint Address'].isin([token_mint_address]).any():
        balance = dataframe.loc[dataframe['Mint Address'] == token_mint_address, 'Amount'].iloc[0]
        return balance
    else:
        return 0

def advanced_pnl_management():
    if not ENABLE_TIERED_EXITS:
        return
    cprint("📈 Kali Strategy Engine: Running Advanced PNL Management", 'white', 'on_blue', attrs=['bold'])
    try:
        open_positions_df = fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
        position_states = load_position_states()
        if open_positions_df.empty and not position_states:
            return
        wallet_mints = set(open_positions_df['Mint Address']) if not open_positions_df.empty else set()
        for mint in list(position_states.keys()):
            if mint not in wallet_mints:
                remove_position_state(mint)
                continue
        positions_processed = 0
        for mint, state in list(position_states.items()):
            if mint not in wallet_mints:
                continue
            positions_processed += 1
            position_row = open_positions_df[open_positions_df['Mint Address'] == mint].iloc[0]
            current_usd_value = position_row['USD Value']
            initial_investment = state['initial_investment_usdc']
            tiers_sold = state.get('tiers_sold', [])
            stop_loss_value = initial_investment * (1 + STOP_LOSS_PERCENTAGE)
            if current_usd_value < stop_loss_value:
                kill_switch(mint)
                remove_position_state(mint)
                continue
            for tier_index, tier in enumerate(SELL_TIERS):
                tier_profit_value = initial_investment * tier['profit_multiple']
                if current_usd_value >= tier_profit_value and tier_index not in tiers_sold:
                    success = execute_tiered_sell(mint, tier_index, current_usd_value)
                    if success:
                        if tier_index == len(SELL_TIERS) - 1:
                            kill_switch(mint)
                            remove_position_state(mint)
                            break
                    break
    except Exception as e:
        cprint(f"❌ Kali Strategy: Error in advanced PNL management: {e}", 'red')

def ask_bid(token_mint_address):
    API_KEY = d.birdeye
    url = f"https://public-api.birdeye.so/defi/price?address={token_mint_address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        json_response = response.json()
        if 'data' in json_response and 'value' in json_response['data']:
            return json_response['data']['value']
        else:
            return None
    else:
        return None