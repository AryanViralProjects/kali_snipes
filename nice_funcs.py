import json 
import time 
import pandas as pd
import requests
import dontshare as d
from termcolor import cprint
from config import * 
import math
import ccxt 

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

    ''' gets the security check for a token based on birdeye info and returns it in json
    
    decide which to use as filters... 
    - top10HolderPercent > .3 ... be out... this can be a VARIABLE

    {
  "data": {
    "creatorAddress": "8LAnvxpF7kL1iUjDRjmP87xiuyCx4yX3ZRAoDCChKe1L",
    "creatorOwnerAddress": null,
    "ownerAddress": null,
    "ownerOfOwnerAddress": null,
    "creationTx": "48PniJegRijm7wcm8Ygzw9hDC6fysYrXRr5D1UUcuqUTS8B16Le7A8tvWFLoPYvNSaSyfiynhkz8WFfKJbmhwgcp",
    "creationTime": 1702086574,
    "creationSlot": 234822271,
    "mintTx": "48PniJegRijm7wcm8Ygzw9hDC6fysYrXRr5D1UUcuqUTS8B16Le7A8tvWFLoPYvNSaSyfiynhkz8WFfKJbmhwgcp",
    "mintTime": 1702086574,
    "mintSlot": 234822271,
    "creatorBalance": 22.053403028,
    "ownerBalance": null,
    "ownerPercentage": null,
    "creatorPercentage": 2.2054864219584144e-8,
    "metaplexUpdateAuthority": "8LAnvxpF7kL1iUjDRjmP87xiuyCx4yX3ZRAoDCChKe1L",
    "metaplexOwnerUpdateAuthority": null,
    "metaplexUpdateAuthorityBalance": 22.053403028,
    "metaplexUpdateAuthorityPercent": 2.2054864219584144e-8,
    "mutableMetadata": false,
    "top10HolderBalance": 937114842.9086457,
    "top10HolderPercent": 0.9371769332953355,
    "top10UserBalance": 937114842.9086457,
    "top10UserPercent": 0.9371769332953355,
    "isTrueToken": null,
    "totalSupply": 999933747.4232626,
    "preMarketHolder": [],
    "lockInfo": null,
    "freezeable": null,
    "freezeAuthority": null,
    "transferFeeEnable": null,
    "transferFeeData": null,
    "isToken2022": false,
    "nonTransferable": null
  },
  "success": true,
  "statusCode": 200
}

    '''

    API_KEY = d.birdeye

    url = f"https://public-api.birdeye.so/defi/token_security?address={address}"
    headers = {"X-API-KEY": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        security_data = response.json()  # Return the JSON response if the call is successful
        if security_data and 'data' in security_data:
            # In the context of this code, get('freezeable', False) serves to handle cases where the key 'freezeable' might not be present in the JSON data. 
            # Here's why False is used as the default:
            # Safe Default: Using False ensures that if the 'freezeable' key is absent, the code will not mistakenly consider the token to be freezeable. 
            # It assumes a non-freezeable state unless explicitly indicated otherwise.
            if security_data['data'].get('freezeable', False):  # Check if the token is freezeable
                print(f"* {address[-4:]} is freezeable. Dropping.")
                return None  # Return None to indicate the token should be dropped
        return security_data
    else:
        return None  # Return None if there's an error with the API call


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
    cprint(f'🌙 Kali: Opening position for token: {token_mint_address}', 'white', 'on_blue')

    # Check permanent blacklist first
    try:
        with open(PERMANENT_BLACKLIST, 'r') as f:
            blacklisted = [line.strip() for line in f.readlines()]
            if token_mint_address in blacklisted:
                cprint(f'⛔ Kali: Token {token_mint_address} is permanently blacklisted, skipping', 'white', 'on_red')
                return
    except FileNotFoundError:
        # If file doesn't exist yet, create it
        open(PERMANENT_BLACKLIST, 'a').close()

    # First check if we already have ANY position
    initial_balance = get_position(token_mint_address)
    if initial_balance > 0:
        cprint(f'⚠️ Kali: Already have position in {token_mint_address}, adding to closed positions', 'white', 'on_red')
        with open(CLOSED_POSITIONS_TXT, 'a') as f:
            f.write(f'{token_mint_address}\n')
        return

    # Check closed positions before attempting to open
    with open(CLOSED_POSITIONS_TXT, 'r') as f:
        closed_positions = [line.strip() for line in f.readlines()]
        if token_mint_address in closed_positions:
            cprint(f'⚠️ Kali: Token {token_mint_address} in closed positions, skipping', 'white', 'on_red')
            return

    buying_df = pd.read_csv(READY_TO_BUY_CSV)
    if token_mint_address not in buying_df['address'].values:
        cprint(f'⚠️ Kali: Token {token_mint_address} not in buying list, skipping', 'white', 'on_red')
        return
    
    token_info = buying_df[buying_df['address'] == token_mint_address].to_dict(orient='records')[0]
    token_size = float(USDC_SIZE)
    
    price = ask_bid(token_mint_address)
    if not price:
        cprint(f'⚠️ Kali: Could not get price for {token_mint_address}, skipping', 'white', 'on_red')
        return

    try:
        size_needed = int(token_size * 10**6)  # Convert to USDC decimals
        size_needed = str(size_needed)

        # Try to open position
        for i in range(orders_per_open):
            cprint(f'🎯 Kali: Attempting order {i+1}/{orders_per_open} for {token_mint_address}', 'white', 'on_blue')
            
            # Check the return value from market_buy
            if not market_buy(token_mint_address, size_needed):
                cprint(f'❌ Kali: Market buy failed for {token_mint_address}, token may be blacklisted', 'white', 'on_red')
                return
                
            time.sleep(1)
            
            # Check if we got any position after the order
            current_balance = get_position(token_mint_address)
            if current_balance > 0:
                cprint(f'✅ Kali: Position opened! Balance: {current_balance}', 'white', 'on_green')
                # Immediately add to closed positions to prevent re-entry
                with open(CLOSED_POSITIONS_TXT, 'a') as f:
                    f.write(f'{token_mint_address}\n')
                return

    except Exception as e:
        cprint(f'❌ Kali: Order failed: {str(e)}', 'white', 'on_red')
        time.sleep(30)
        try:
            for i in range(orders_per_open):
                if not market_buy(token_mint_address, size_needed):
                    cprint(f'❌ Kali: Market buy failed on retry for {token_mint_address}', 'white', 'on_red')
                    return
                    
                time.sleep(1)
                
                # Check again after retry
                current_balance = get_position(token_mint_address)
                if current_balance > 0:
                    cprint(f'✅ Kali: Position opened on retry! Balance: {current_balance}', 'white', 'on_green')
                    with open(CLOSED_POSITIONS_TXT, 'a') as f:
                        f.write(f'{token_mint_address}\n')
                    return
                    
        except:
            cprint('❌ Kali: Order failed again, logging to closed positions', 'white', 'on_red')
            with open(CLOSED_POSITIONS_TXT, 'a') as f:
                f.write(f'{token_mint_address}\n')
            return

    # Final balance check
    final_balance = get_position(token_mint_address)
    if final_balance > 0:
        cprint(f'✅ Kali: Final position check - Balance: {final_balance}', 'white', 'on_green')
        with open(CLOSED_POSITIONS_TXT, 'a') as f:
            f.write(f'{token_mint_address}\n')
    else:
        cprint(f'❌ Kali: No position opened for {token_mint_address}', 'white', 'on_red')
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

