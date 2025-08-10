from termcolor import colored, cprint
from config import * 
import warnings
warnings.filterwarnings('ignore')
import math, os
import requests
import pandas as pd
import time 
import threading
import asyncio
import dontshare as d   
import json
import nice_funcs as n
import schedule
from datetime import datetime 
from get_new_tokens import scan_bot  # Import scan_bot instead of ohlcv_filter
from position_tracker_v2 import EnhancedPositionTracker



def bot():
    # Get the current time
    now = datetime.now()
    cprint(f'🌙 Kali live bot running at {now}', 'white', 'on_green')

    # checking if need to kill all positions
    while EXIT_ALL_POSITIONS:
        cprint(f'exiting all positions bc EXIT_ALL_POSITIONS is set to {EXIT_ALL_POSITIONS}', 'white', 'on_magenta')
        n.close_all_positions()
        open_positions_df = n.fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)

    time.sleep(1)
    # Get current positions for PNL management
    open_positions_df = n.fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)

    # Check SOL balance with retries
    retry_count = 0
    sol_amount = None
    sol_value = None

    cprint("\n🔍 Kali: Checking SOL Balance", 'white', 'on_blue')
    
    while retry_count < 3 and (sol_amount is None or sol_value is None):
        retry_count += 1
        cprint(f"\n💫 Kali: SOL Balance Check Attempt {retry_count}/3", 'white', 'on_cyan')
        sol_amount, sol_value = n.get_sol_balance(MY_SOLANA_ADDERESS)
        
        if sol_amount is not None:
            cprint(f"✅ SOL Balance: {sol_amount} SOL (${sol_value:.2f})", 'white', 'on_green')
            break
        else:
            cprint(f"⚠️ Attempt {retry_count} failed to get SOL balance", 'white', 'on_red')
            time.sleep(30)

    # If we still don't have SOL balance after retries, exit
    if sol_amount is None:
        cprint("🚨 CRITICAL: Failed to get SOL balance after 3 attempts. Exiting bot...", 'white', 'on_red')
        cprint("💡 This is likely due to API connection issues. Check your API keys!", 'white', 'on_yellow')
        return  # Exit gracefully instead of sleeping forever

    # Check if SOL balance is too low
    if float(sol_amount) < 0.005:
        cprint(f"🚨 Kali: SOL BALANCE CRITICAL! Only {sol_amount} SOL remaining", 'white', 'on_red')
        cprint(f"Need at least: 0.005 SOL", 'white', 'on_red')
        cprint(f"Current value: ${sol_value:.2f}", 'white', 'on_red')
        return

    # Print final SOL balance info
    cprint("\n💰 Kali SOL BALANCE INFO:", 'white', 'on_light_blue')
    cprint(f"Amount: {sol_amount} SOL", 'white', 'on_light_blue')


####### 🎯 DYNAMIC STRATEGY ENGINE - TIERED EXITS & SMART SIZING

    # === ADVANCED PNL MANAGEMENT ===
    if ENABLE_TIERED_EXITS:
        if POSITION_TRACKER_MANAGES_EXITS:
            cprint('🔒 Exits managed by Position Tracker. Skipping internal sells.', 'cyan')
        else:
            cprint('🎯 Kali Strategy Engine: Running Advanced Tiered PNL Management', 'white', 'on_blue', attrs=['bold'])
            n.advanced_pnl_management()
    else:
        cprint('📈 Kali: Using Legacy PNL Management', 'white', 'on_cyan')
        # Legacy PNL management (simplified version)
        
        # Check for winning positions (first profit target)
        open_positions_count = open_positions_df.shape[0]
        winning_positions_df = open_positions_df[open_positions_df['USD Value'] > SELL_AT_MULTIPLE * USDC_SIZE]

        for index, row in winning_positions_df.iterrows():
            token_mint_address = row['Mint Address']
            if token_mint_address not in DO_NOT_TRADE_LIST:
                cprint(f'🌙 Kali: Winning Position (50% profit) - Token: {token_mint_address}', 'white', 'on_green')
                n.pnl_close(token_mint_address)
            cprint('✨ Kali: Done closing winning positions...', 'white', 'on_magenta')

        # Check for losing positions (tightened stop loss)
        sl_size = ((1+STOP_LOSS_PERCENTAGE) * USDC_SIZE)
        losing_positions_df = open_positions_df[open_positions_df['USD Value'] < sl_size]
        losing_positions_df = losing_positions_df[losing_positions_df['USD Value'] != 0]
     
        for index, row in losing_positions_df.iterrows():
            token_mint_address = row['Mint Address']
            if token_mint_address in DO_NOT_TRADE_LIST:
                cprint(f'🚫 Kali: Skipping trade for {token_mint_address} (in DO_NOT_TRADE_LIST)', 'white', 'on_red')
                continue
            if token_mint_address != USDC_CA:
                n.pnl_close(token_mint_address)
               
        cprint('🌙 Kali: Done with legacy PNL management', 'white', 'on_magenta')


####### 🎯 STRATEGY ENGINE ACTIVE

    # Start position tracker thread if enabled (manages exits)
    if ENABLE_POSITION_TRACKER and POSITION_TRACKER_MANAGES_EXITS:
        def _run_tracker():
            tracker = EnhancedPositionTracker()
            asyncio.run(tracker.run())
        # Start only once per process
        if not any(getattr(t, 'name', '').startswith('PositionTrackerThread') for t in threading.enumerate()):
            tracker_thread = threading.Thread(target=_run_tracker, daemon=True, name='PositionTrackerThread')
            tracker_thread.start()
            cprint('✅ Position tracker thread started', 'green')

    # Run token scan every time
    cprint(f'🔍 Kali: Running token scan...', 'white', 'on_cyan')
    scan_bot()  # Run the scan_bot from get_new_tokens.py
        
    try:
        df = pd.read_csv(FINAL_SORTED_CSV)
    except Exception as e:
        cprint(f"❌ Kali: Error reading {FINAL_SORTED_CSV}: {str(e)}", 'white', 'on_red')
        return

    # look at closed_positions.txt and if the token is there, then remove that row from the df
    with open(CLOSED_POSITIONS_TXT, 'r') as f:
        closed_positions = [line.strip() for line in f.readlines()]
    df = df[~df['address'].isin(closed_positions)]
    df.to_csv(READY_TO_BUY_CSV, index=False)

    df = n.get_names(df)

# 🍀 THIS IS WHERE THE BUYING STARTS
    for index, row in df.iterrows():
        usdc_holdings = n.get_position(USDC_CA)
        usdc_holdings = float(usdc_holdings)
        token_mint_address = row['address']
        
        if usdc_holdings > USDC_SIZE:
            cprint(f'💰 Kali: USDC Balance {usdc_holdings} > {USDC_SIZE}, opening position...', 'white', 'on_blue')
            cprint(f'📝 Token Address: {token_mint_address}', 'white', 'on_blue')
            n.open_position(token_mint_address)
        else:
            cprint(f'⚠️ Kali: Insufficient USDC ({usdc_holdings}), skipping position', 'white', 'on_red')
    
    time.sleep(5)

bot()
cprint('🌙 Kali: Done with 1st run, now looping...', 'white', 'on_green')

# Schedule bot to run every 120 seconds
schedule.every(600).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
        time.sleep(30)  # Check schedule every 30 seconds
    except Exception as e:
        cprint('❌ Kali: Connection error!', 'white', 'on_red')
        cprint(str(e), 'white', 'on_red')
        time.sleep(30)

