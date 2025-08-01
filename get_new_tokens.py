# this scans for new tokens on solana... 

import pandas as pd 
# openai_key
import datetime 
import dontshare as d # this is where the birdeye api key is stored named birdeye
import requests
import time , json, os
import pprint
import re as reggie
from termcolor import cprint
from config import *
import pandas_ta as ta
from datetime import datetime, timedelta
from nice_funcs import security_check  # Import the security_check function

def get_time_range():
    """Get time range for OHLCV data (10 days)"""
    now = datetime.now()
    ten_days_earlier = now - timedelta(days=10)
    time_to = int(now.timestamp())
    time_from = int(ten_days_earlier.timestamp())
    return time_from, time_to

def get_ohlcv_data(address):
    """Get OHLCV data from Birdeye API"""
    time_from, time_to = get_time_range()
    url = f"https://public-api.birdeye.so/defi/ohlcv?address={address}&type={TIMEFRAME}&time_from={time_from}&time_to={time_to}"
    
    headers = {"X-API-KEY": d.birdeye}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        cprint(f"🚨 Kali: Failed to get OHLCV data for {address}", 'red')
        return pd.DataFrame()
        
    json_response = response.json()
    items = json_response.get('data', {}).get('items', [])

    processed_data = [{
        'Datetime (UTC)': datetime.utcfromtimestamp(item['unixTime']).strftime('%Y-%m-%d %H:%M:%S'),
        'Open': item['o'],
        'High': item['h'],
        'Low': item['l'],
        'Close': item['c'],
        'Volume': item['v']
    } for item in items]

    df = pd.DataFrame(processed_data)
    
    if len(df) < 40:
        rows_to_add = 40 - len(df)
        first_row_replicated = pd.concat([df.iloc[0:1]] * rows_to_add, ignore_index=True)
        df = pd.concat([first_row_replicated, df], ignore_index=True)

    # Calculate technical indicators
    df['MA20'] = ta.sma(df['Close'], length=20)
    df['MA40'] = ta.sma(df['Close'], length=40)
    df['Price_above_MA20'] = df['Close'] > df['MA20']
    df['Price_above_MA40'] = df['Close'] > df['MA40']
    df['MA20_above_MA40'] = df['MA20'] > df['MA40']

    # Print OHLCV data head
    cprint("\n📊 Kali: Latest OHLCV Data for Token 🌙", 'cyan', attrs=['bold'])
    print("\nLast 5 candles:")
    print(df[['Datetime (UTC)', 'Open', 'High', 'Low', 'Close', 'Volume']].tail().to_string())
    print("\nTechnical Indicators:")
    print(f"MA20: {df['MA20'].iloc[-1]:.8f}")
    print(f"MA40: {df['MA40'].iloc[-1]:.8f}")
    print(f"Price Above MA20: {df['Price_above_MA20'].iloc[-1]}")
    print(f"Price Above MA40: {df['Price_above_MA40'].iloc[-1]}")
    print(f"MA20 Above MA40: {df['MA20_above_MA40'].iloc[-1]}")

    return df

def analyze_ohlcv_trend(ohlcv_df):
    """Analyze OHLCV trends and return analysis dict"""
    # Get price metrics
    highest_close = ohlcv_df['Close'].max()
    lowest_close = ohlcv_df['Close'].min()
    most_recent_close = ohlcv_df['Close'].iloc[-1]
    avg_close = (highest_close + lowest_close) / 2
    price_above_avg_close = most_recent_close > avg_close
    
    # Track higher highs/lows
    prev_high = ohlcv_df['High'].iloc[0]
    prev_low = ohlcv_df['Low'].iloc[0]
    higher_highs = True
    higher_lows = True
    
    for i in range(1, len(ohlcv_df)):
        current_high = ohlcv_df['High'].iloc[i]
        current_low = ohlcv_df['Low'].iloc[i]
        
        if current_high <= prev_high:
            higher_highs = False
        if current_low <= prev_low:
            higher_lows = False
            
        prev_high = current_high
        prev_low = current_low

    price_increase_from_launch = ohlcv_df['Close'].iloc[-1] > ohlcv_df['Open'].iloc[0]
    num_bars = len(ohlcv_df)

    return {
        'higher_highs': higher_highs,
        'higher_lows': higher_lows,
        'price_increase_from_launch': price_increase_from_launch,
        'MA20': ohlcv_df['MA20'].iloc[-1],
        'MA40': ohlcv_df['MA40'].iloc[-1],
        'Price_above_MA20': ohlcv_df['Price_above_MA20'].iloc[-1],
        'Price_above_MA40': ohlcv_df['Price_above_MA40'].iloc[-1],
        'MA20_above_MA40': ohlcv_df['MA20_above_MA40'].iloc[-1],
        'num_bars': num_bars,
        'price_above_avg_close': price_above_avg_close
    }

def check_ohlcv_conditions(ohlcv_df, trend_analysis, address):
    """Check if token passes OHLCV conditions"""
    # Check number of bars
    if trend_analysis['num_bars'] > max_amount_of_bars_before_dropping:
        cprint(f"🌙 Kali: Dropping {address} - Too many bars ({trend_analysis['num_bars']} > {max_amount_of_bars_before_dropping})", 'yellow')
        return False

    # Check price vs average close
    if only_keep_if_above_avg_close and not trend_analysis['price_above_avg_close']:
        cprint(f"🌙 Kali: Dropping {address} - Price below average close", 'yellow')
        return False

    # Check moving average conditions over last 30 bars
    if len(ohlcv_df) >= 30:
        conditions = [
            (ohlcv_df['Price_above_MA20'].tail(30).sum() / 30) > 0.5,
            (ohlcv_df['Price_above_MA40'].tail(30).sum() / 30) > 0.5,
            (ohlcv_df['MA20_above_MA40'].tail(30).sum() / 30) > 0.5,
            trend_analysis['price_increase_from_launch']
        ]
        
        if any(conditions):
            cprint(f"🚀 Kali: {address} PASSED OHLCV FILTERS! 🌙", 'white', 'on_green', attrs=['bold'])
            return True
            
    cprint(f"🌙 Kali: Dropping {address} - Failed technical conditions", 'yellow')
    return False

def token_overview(address, MAX_SELL_PERCENTAGE, MIN_TRADES_LAST_HOUR, MIN_UNQ_WALLETS2hr, MIN_VIEW24h, MIN_LIQUIDITY):
    url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
    headers = {"X-API-KEY": d.birdeye}

    response = requests.get(url, headers=headers)
    time.sleep(2)
    result = {}

    # Handle 521 error (Cloudflare/server down)
    if response.status_code == 521:
        cprint(f"🔄 Birdeye API temporarily down for {address[-4:]} - waiting 30s...", 'yellow')
        time.sleep(30)  # Wait longer for server issues
        return "retry"  # Signal to retry this token
    
    if response.status_code != 200:
        cprint(f"❌ Failed to get token data for {address[-4:]}: HTTP {response.status_code}", 'red')
        return None

    overview_data = response.json().get('data', {})
    
    # Check market cap first
    mc = overview_data.get('mc', 0)
    if mc > MAX_MARKET_CAP:
        cprint(f"🚫 Token dropped: {address}", 'red')
        cprint(f"Reason: Market cap too high (${mc:,.2f} > ${MAX_MARKET_CAP:,.2f})", 'red')
        return None

    # Check top 10 holder percentage
    top10_holder_percent = overview_data.get('top10HolderPercent', 0)
    if top10_holder_percent > MAX_TOP10_HOLDER_PERCENT:
        cprint(f"🚫 Token dropped: {address}", 'red')
        cprint(f"Reason: Top 10 holders own too much ({top10_holder_percent*100:.1f}% > {MAX_TOP10_HOLDER_PERCENT*100:.1f}%)", 'red')
        return None
    
    buy1h = overview_data.get('buy1h', 0)
    sell1h = overview_data.get('sell1h', 0)
    trade1h = buy1h + sell1h
    total_trades = trade1h

    # Perform buy/sell percentage calculations:
    buy_percentage = (buy1h / total_trades * 100) if total_trades else 0
    sell_percentage = (sell1h / total_trades * 100) if total_trades else 0

    # Criteria checks with colored output:
    if sell_percentage > MAX_SELL_PERCENTAGE:
        cprint(f"🚫 Token dropped: {address}", 'yellow')
        cprint(f"Reason: High sell % ({sell_percentage:.1f}%)", 'yellow')
        return None
    if trade1h < MIN_TRADES_LAST_HOUR:
        cprint(f"🚫 Token dropped: {address}", 'magenta')
        cprint(f"Reason: Low trades ({trade1h})", 'magenta')
        return None
    if overview_data.get('uniqueWallet24h', 0) < MIN_UNQ_WALLETS2hr:
        cprint(f"🚫 Token dropped: {address}", 'cyan')
        cprint(f"Reason: Low wallets ({overview_data.get('uniqueWallet24h', 0)})", 'cyan')
        return None
    if overview_data.get('liquidity', 0) < MIN_LIQUIDITY:
        cprint(f"🚫 Token dropped: {address}", 'white')
        cprint(f"Reason: Low liquidity ({overview_data.get('liquidity', 0)})", 'white')
        return None

    # If we get here, token passed all filters - make it stand out!
    cprint(f"🚀 KALI FOUND A GEM! 🌙", 'white', 'on_green', attrs=['bold'])
    cprint(f"✨ {address} ✨", 'white', 'on_green', attrs=['bold'])
    cprint(f"💫 MC: ${mc:,.2f} | Top10: {top10_holder_percent*100:.1f}% | Trades: {trade1h} | Liquidity: {overview_data.get('liquidity', 0)} | Wallets: {overview_data.get('uniqueWallet24h', 0)}", 'white', 'on_green', attrs=['bold'])
    
    # Add calculated data to the result dictionary:
    result.update({
        'address': address,
        'buy1h': buy1h,
        'sell1h': sell1h,
        'trade1h': trade1h,
        'buy_percentage': buy_percentage,
        'sell_percentage': sell_percentage,
        'liquidity': overview_data.get('liquidity', 0),
        'market_cap': mc,
        'top10_holder_percent': top10_holder_percent
    })

    return result

def get_jupiter_tokens():
    """Fetch new tokens from Jupiter API"""
    print("\n🚀 Fetching tokens from Jupiter API...")
    
    url = 'https://lite-api.jup.ag/tokens/v1/new'
    response = requests.get(url)
    
    if response.status_code != 200:
        print("❌ Failed to fetch Jupiter tokens")
        return None
        
    tokens = response.json()
    
    # Convert to DataFrame
    df = pd.DataFrame(tokens)
    
    # Convert created_at to timestamp (Jupiter timestamps are in UTC)
    df['timestamp'] = pd.to_datetime(df['created_at'].astype(int), unit='s', utc=True)
    
    return df

def add_to_blacklist(token_address, reason):
    """Add a token to the permanent blacklist with the reason"""
    cprint(f'🌙 Kali: Adding {token_address} to blacklist. Reason: {reason}', 'white', 'on_red')
    with open(PERMANENT_BLACKLIST, 'a') as f:
        f.write(f'{token_address},{reason}\n')

def get_blacklisted_tokens():
    """Get set of blacklisted token addresses"""
    if not os.path.exists(PERMANENT_BLACKLIST):
        return set()
    
    blacklisted = set()
    with open(PERMANENT_BLACKLIST, 'r') as f:
        for line in f:
            if line.strip():
                token_address = line.strip().split(',')[0]
                blacklisted.add(token_address)
    return blacklisted

def scan_bot():
    """Main function to scan for new tokens"""
    cprint('🌙 Kali: Starting token scan...', 'white', 'on_cyan')
    print('\n🚀 Fetching tokens from Jupiter API...')

    # Get all new tokens first
    all_tokens_df = get_jupiter_tokens()
    if all_tokens_df is None or all_tokens_df.empty:
        cprint('❌ Kali: No tokens found from Jupiter API', 'white', 'on_red')
        return

    # Filter by time
    time_filtered_df = all_tokens_df[all_tokens_df['timestamp'] >= pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=HOURS_TO_LOOK_AT_NEW_LAUNCHES)].copy()
    
    # Rename 'mint' to 'address' for consistency
    time_filtered_df = time_filtered_df.rename(columns={'mint': 'address'})
    
    # Debug prints
    print('\n📊 DataFrame Columns after renaming:')
    print(time_filtered_df.columns.tolist())
    print('\n📝 First few rows of DataFrame:')
    print(time_filtered_df.head())

    # Get blacklisted tokens
    blacklisted_tokens = get_blacklisted_tokens()
    
    # Remove blacklisted tokens early to save API calls
    time_filtered_df = time_filtered_df[~time_filtered_df['address'].isin(blacklisted_tokens)]
    cprint(f'🌙 Kali: Found {len(time_filtered_df)} tokens after removing blacklisted ones', 'white', 'on_cyan')
    
    # Create a list to store valid tokens
    valid_tokens = []
    
    # Process remaining tokens
    for index, row in time_filtered_df.iterrows():
        token_address = row['address']
        cprint(f'\n🔍 Kali: Checking token {token_address}', 'white', 'on_blue')
        
        # Check security data
        security_data = security_check(token_address)
        if not security_data:
            cprint(f"⚠️ Security check returned no data for {token_address}", 'white', 'on_red')
            add_to_blacklist(token_address, 'security_check')
            continue
            
        # Debug print security data
        cprint(f"🔐 Security Data for {token_address}:", 'white', 'on_cyan')
        if 'data' in security_data:
            print("Top 10 Holder %:", security_data['data'].get('top10HolderPercent'))
            print("Freeze Authority:", security_data['data'].get('freezeAuthority'))
            print("Mutable Metadata:", security_data['data'].get('mutableMetadata'))
            print("Is Token 2022:", security_data['data'].get('isToken2022'))
        else:
            cprint("❌ No 'data' field in security response", 'white', 'on_red')
            add_to_blacklist(token_address, 'invalid_security_data')
            continue

        # Check for freezable with proper error handling
        if security_data['data'].get('freezeAuthority'):
            add_to_blacklist(token_address, 'freezable')
            continue
            
        # Check top holder percentage with proper error handling
        top10_holder_percent = security_data['data'].get('top10HolderPercent')
        if top10_holder_percent is not None:
            if top10_holder_percent > MAX_TOP10_HOLDER_PERCENT:
                add_to_blacklist(token_address, 'top_holder_percent')
                continue
        else:
            cprint(f"⚠️ No top10HolderPercent data for {token_address}", 'white', 'on_red')
            add_to_blacklist(token_address, 'missing_holder_data')
            continue
            
        # Check for mutable metadata
        if DROP_IF_MUTABLE_METADATA and security_data['data'].get('mutableMetadata'):
            add_to_blacklist(token_address, 'mutable_metadata')
            continue
            
        # Check for 2022 token program
        if DROP_IF_2022_TOKEN_PROGRAM and security_data['data'].get('isToken2022'):
            add_to_blacklist(token_address, 'token_2022_program')
            continue
            
        # Check liquidity and other metrics
        token_data = token_overview(
            token_address,
            MAX_SELL_PERCENTAGE=MAX_SELL_PERCENTAGE,
            MIN_TRADES_LAST_HOUR=MIN_TRADES_LAST_HOUR,
            MIN_UNQ_WALLETS2hr=MIN_UNQ_WALLETS2HR,
            MIN_VIEW24h=MIN_VIEW24H,
            MIN_LIQUIDITY=MIN_LIQUIDITY
        )
        
        if token_data == "retry" or not token_data:
            continue

        # If we get here, token passed all filters
        valid_tokens.append(token_address)
        cprint(f"✨ Token {token_address} passed all filters!", 'white', 'on_green')
    
    # Filter DataFrame to only include valid tokens
    if valid_tokens:
        final_df = time_filtered_df[time_filtered_df['address'].isin(valid_tokens)]
        final_df.to_csv(FINAL_SORTED_CSV, index=False)
        cprint(f"💾 Saved {len(final_df)} tokens to {FINAL_SORTED_CSV}", 'white', 'on_green')
    else:
        cprint("❌ No tokens passed all filters", 'white', 'on_red')
        # Create empty DataFrame with required columns to prevent errors
        empty_df = pd.DataFrame(columns=['address', 'timestamp'])
        empty_df.to_csv(FINAL_SORTED_CSV, index=False)

if __name__ == "__main__":
    scan_bot()
    