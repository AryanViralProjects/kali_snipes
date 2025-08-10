"""
Sell utilities for closing positions
"""

from termcolor import cprint
from config import *
import dontshare as d
import time
import requests
import json
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from common.token_utils import get_position, ask_bid, get_decimals, round_down

def market_sell(QUOTE_TOKEN, amount, slippage=SLIPPAGE):
    """Execute a market sell order via Jupiter"""
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
    """This function closes the position in full"""
    
    # Get current balance
    balance = get_position(token_mint_address)
    
    # Get current price of token 
    price = ask_bid(token_mint_address)
    
    usd_value = balance * price
    
    tp = SELL_AT_MULTIPLE * USDC_SIZE
    sell_size = balance 
    # Round to 2 decimals
    sell_size = round_down(sell_size, 2)
    decimals = get_decimals(token_mint_address)
    
    sell_size = int(sell_size * 10 **decimals)
    
    while usd_value > 0:
        # Log this mint address to closed positions file
        with open(CLOSED_POSITIONS_TXT, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
            if token_mint_address not in lines:
                with open(CLOSED_POSITIONS_TXT, 'a') as f:
                    f.write(token_mint_address + '\n')
        
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
        
        balance = get_position(token_mint_address)
        price = ask_bid(token_mint_address)
        usd_value = balance * price
        tp = SELL_AT_MULTIPLE * USDC_SIZE
        sell_size = balance 
        
        # Round downwards to 2 decimals
        sell_size = round_down(sell_size, 2)
        decimals = get_decimals(token_mint_address)
        sell_size = int(sell_size * 10 **decimals)