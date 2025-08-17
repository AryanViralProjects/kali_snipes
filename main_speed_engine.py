"""
🚀 KALI SPEED ENGINE - TIER 1 SNIPER BOT
Real-time WebSocket detection with millisecond-level execution
"""

import asyncio
import time
import threading
from termcolor import cprint
from datetime import datetime
import dontshare as d
import nice_funcs as n
from config import *
from raydium_listener import start_speed_engine, listen_for_new_pools
from pump_fun_listener import listen_for_pump_fun
from virtuals_listener import listen_for_virtuals
try:
    # Optional import; tracker runs as a standalone script in this mode
    from position_tracker_v2 import EnhancedPositionTracker
except Exception:
    EnhancedPositionTracker = None
import warnings
warnings.filterwarnings('ignore')

def run_risk_management():
    """
    Background risk management - runs the advanced strategy PnL monitoring
    """
    while True:
        try:
            cprint("🛡️ Kali Speed + Strategy Engine: Running advanced risk management...", 'white', 'on_blue')
            
            # === ADVANCED STRATEGY ENGINE RISK MANAGEMENT ===
            if ENABLE_TIERED_EXITS:
                if POSITION_TRACKER_MANAGES_EXITS:
                    # Exits are managed by the external position tracker
                    cprint("🔒 Exits managed by Position Tracker. Skipping internal sells.", 'cyan')
                else:
                    # Use the advanced PNL management system
                    n.advanced_pnl_management()
                    
                # Show strategy performance summary
                summary = n.get_position_performance_summary()
                if "No positions" not in summary:
                    cprint(f"📊 Strategy Summary: {summary}", 'blue')
                    
            else:
                # Fallback to legacy system
                cprint("📈 Kali Speed Engine: Using legacy risk management", 'cyan')
                
                if POSITION_TRACKER_MANAGES_EXITS:
                    cprint("🔒 Exits managed by Position Tracker. Legacy sells disabled.", 'cyan')
                else:
                    # Get open positions
                    open_positions_df = n.fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
                    
                    if not open_positions_df.empty:
                        # Check for winning positions (first profit target)
                        winning_positions_df = open_positions_df[open_positions_df['USD Value'] > SELL_AT_MULTIPLE * USDC_SIZE]
                        
                        for index, row in winning_positions_df.iterrows():
                            token_mint_address = row['Mint Address']
                            if token_mint_address not in DO_NOT_TRADE_LIST:
                                cprint(f'💰 Kali Speed Engine: Taking profit on {token_mint_address[-6:]}', 'white', 'on_green')
                                n.pnl_close(token_mint_address)
                        
                        # Check for losing positions (tightened stop loss)
                        sl_size = ((1+STOP_LOSS_PERCENTAGE) * USDC_SIZE)
                        losing_positions_df = open_positions_df[open_positions_df['USD Value'] < sl_size]
                        losing_positions_df = losing_positions_df[losing_positions_df['USD Value'] != 0]
                        
                        for index, row in losing_positions_df.iterrows():
                            token_mint_address = row['Mint Address']
                            if token_mint_address not in DO_NOT_TRADE_LIST and token_mint_address != USDC_CA:
                                cprint(f'🛑 Kali Speed Engine: Stop loss triggered for {token_mint_address[-6:]}', 'white', 'on_red')
                                n.pnl_close(token_mint_address)
            
            # Sleep for 2 minutes before next check
            time.sleep(120)
            
        except Exception as e:
            cprint(f"❌ Kali Speed Engine: Risk management error: {e}", 'red')
            time.sleep(60)

def run_balance_monitor():
    """
    Monitor SOL balance and system health
    """
    while True:
        try:
            cprint("💰 Kali Speed Engine: Checking wallet balance...", 'white', 'on_cyan')
            
            sol_amount, sol_value = n.get_sol_balance(MY_SOLANA_ADDERESS)
            
            if sol_amount is not None:
                cprint(f"✅ SOL Balance: {sol_amount} SOL (${sol_value:.2f})", 'white', 'on_green')
                
                # Check if SOL balance is getting low
                if float(sol_amount) < 0.01:
                    cprint(f"⚠️ Kali Speed Engine: LOW SOL WARNING! Only {sol_amount} SOL remaining", 'white', 'on_yellow')
                    
                if float(sol_amount) < 0.005:
                    cprint(f"🚨 Kali Speed Engine: CRITICAL SOL BALANCE! Only {sol_amount} SOL remaining", 'white', 'on_red')
                    cprint("🛑 Consider adding more SOL for transaction fees", 'white', 'on_red')
            else:
                cprint("❌ Kali Speed Engine: Failed to get SOL balance", 'red')
            
            # Sleep for 5 minutes before next balance check
            time.sleep(300)
            
        except Exception as e:
            cprint(f"❌ Kali Speed Engine: Balance monitor error: {e}", 'red')
            time.sleep(120)

def run_speed_engine_main():
    """
    Main Speed Engine coordinator
    """
    cprint("🚀 KALI SPEED ENGINE STARTING UP...", 'white', 'on_blue', attrs=['bold'])
    cprint("⚡ REVOLUTIONIZING FROM MINUTES TO MILLISECONDS!", 'white', 'on_blue', attrs=['bold'])
    cprint("🎯 Real-time WebSocket detection + Ultra-fast execution", 'white', 'on_blue', attrs=['bold'])
    
    # Display configuration
    cprint("\n📊 SPEED ENGINE CONFIGURATION:", 'white', 'on_cyan', attrs=['bold'])
    cprint(f"💰 Trade Size: ${USDC_SIZE} USDC", 'cyan')
    cprint(f"🎯 Profit Target: {int((SELL_AT_MULTIPLE - 1) * 100)}%", 'cyan')
    cprint(f"🛑 Stop Loss: {int(abs(STOP_LOSS_PERCENTAGE) * 100)}%", 'cyan')
    cprint(f"⚡ Priority Fee: {PRIORITY_FEE} lamports", 'cyan')
    cprint(f"🌐 Wallet: {MY_SOLANA_ADDERESS}", 'cyan')
    
    # Check initial SOL balance
    sol_amount, sol_value = n.get_sol_balance(MY_SOLANA_ADDERESS)
    if sol_amount is None:
        cprint("❌ CRITICAL: Cannot get SOL balance. Check your RPC connection!", 'white', 'on_red')
        return
    
    if float(sol_amount) < 0.005:
        cprint(f"🚨 CRITICAL: SOL balance too low ({sol_amount} SOL). Need at least 0.005 SOL for fees!", 'white', 'on_red')
        return
    
    cprint(f"\n✅ Initial SOL Balance: {sol_amount} SOL (${sol_value:.2f})", 'white', 'on_green')
    
    # Start background threads
    cprint("\n🔧 Starting background services...", 'white', 'on_blue')
    
    # Risk management thread
    risk_thread = threading.Thread(target=run_risk_management, daemon=True)
    risk_thread.start()
    cprint("✅ Risk management thread started", 'green')
    
    # Balance monitor thread  
    balance_thread = threading.Thread(target=run_balance_monitor, daemon=True)
    balance_thread.start()
    cprint("✅ Balance monitor thread started", 'green')

    # Position tracker is run separately when ENABLE_POSITION_TRACKER=False
    
    cprint("\n🚀 LAUNCHING REAL-TIME DETECTION ENGINE...", 'white', 'on_green', attrs=['bold'])
    cprint("🔍 Monitoring Raydium for new pool creations...", 'white', 'on_green', attrs=['bold'])
    
    # Start the main speed engine (WebSocket listener)
    try:
        start_speed_engine()
    except KeyboardInterrupt:
        cprint("\n⏹️ Kali Speed Engine: Graceful shutdown initiated...", 'yellow')
    except Exception as e:
        cprint(f"\n❌ Kali Speed Engine: Fatal error: {e}", 'red')


async def run_multi_pool_async():
    """
    Run Raydium, Pump.fun, and Virtuals listeners concurrently.
    """
    cprint("🚀 KALI MULTI-POOL SPEED ENGINE STARTING...", 'white', 'on_blue', attrs=['bold'])
    tasks = [
        asyncio.create_task(listen_for_new_pools()),
        asyncio.create_task(listen_for_pump_fun()),
        asyncio.create_task(listen_for_virtuals()),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()


def run_multi_pool_engine():
    """
    Entry for multi-pool engine (async gather of all listeners).
    """
    try:
        asyncio.run(run_multi_pool_async())
    except KeyboardInterrupt:
        cprint("\n⏹️ Kali Multi-Pool Engine: Shutting down gracefully...", 'yellow')

def run_hybrid_mode():
    """
    Run both speed engine and original bot in parallel
    """
    cprint("🔄 KALI HYBRID MODE: Speed Engine + Original Bot", 'white', 'on_magenta', attrs=['bold'])
    
    # Start speed engine in separate thread
    speed_thread = threading.Thread(target=run_speed_engine_main, daemon=False)
    speed_thread.start()
    
    # Import and run original bot logic in main thread
    from main import bot
    import schedule
    
    cprint("📡 Starting original bot polling system as backup...", 'white', 'on_blue')
    
    # Run original bot once
    bot()
    
    # Schedule original bot to run every 10 minutes as backup
    schedule.every(10).minutes.do(bot)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            cprint("\n⏹️ Kali Hybrid Mode: Shutting down...", 'yellow')
            break
        except Exception as e:
            cprint(f"❌ Kali Hybrid Mode: Error: {e}", 'red')
            time.sleep(30)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "speed":
            run_speed_engine_main()
        elif mode == "multi":
            run_multi_pool_engine()
        elif mode == "hybrid":
            run_hybrid_mode()
        else:
            print("Usage:")
            print("  python main_speed_engine.py speed   # Raydium only")
            print("  python main_speed_engine.py multi   # Raydium + Pump.fun + Virtuals")
            print("  python main_speed_engine.py hybrid  # Speed Engine + Original Bot")
    else:
        # Default to multi-pool engine
        run_multi_pool_engine()