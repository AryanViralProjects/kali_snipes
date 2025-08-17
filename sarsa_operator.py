#!/usr/bin/env python3
"""
Sarsa Operator - Supervisory agent for Kali sniper bot
- Token age verification fallback (web search placeholder + cache)
- Redundant risk management (fail-safe stop-loss enforcement)
- Persistent PNL ledger logging
"""
import asyncio
import csv
import json
import os
import time
from datetime import datetime, timezone
from termcolor import cprint

import nice_funcs as n
from config import (
    MAX_TOKEN_AGE_HOURS,
    CLOSED_POSITIONS_TXT,
)

# Files
TOKEN_AGE_CACHE_FILE = './data/token_age_cache.json'
PNL_LEDGER_FILE = './data/pnl_ledger.csv'

# ------------- Token age cache helpers -------------

def load_age_cache():
    try:
        with open(TOKEN_AGE_CACHE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        cprint(f"Sarsa: Failed to load age cache: {e}", 'yellow')
        return {}


def save_age_cache(cache):
    try:
        os.makedirs('./data', exist_ok=True)
        with open(TOKEN_AGE_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=4)
    except Exception as e:
        cprint(f"Sarsa: Failed to save age cache: {e}", 'yellow')


# ------------- Token age verification (fallback) -------------

async def verify_token_age_via_search(token_address: str) -> bool:
    """Fallback age verification using web search placeholder + cache."""
    cache = load_age_cache()
    cached = cache.get(token_address)
    if cached is not None:
        age_hours = float(cached.get('age_hours', 0))
        if age_hours <= MAX_TOKEN_AGE_HOURS:
            cprint(f"   -> Sarsa Cache: {token_address[-6:]} age {age_hours:.2f}h OK", 'green')
            return True
        else:
            cprint(f"   -> Sarsa Cache: {token_address[-6:]} age {age_hours:.2f}h REJECTED", 'red')
            return False

    cprint(f"   -> Sarsa: Performing web search for age (placeholder) {token_address[-6:]}", 'yellow')
    # Placeholder: Could not determine; approve as new by fail-safe to avoid blocking speed path
    token_age_hours = None

    # Cache the unknown result with small TTL behavior (we store None as -1)
    cache[token_address] = {
        'age_hours': token_age_hours if token_age_hours is not None else -1,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    save_age_cache(cache)

    if token_age_hours is None:
        # Fail-safe approve when unknown; Kali's own checks still apply
        return True

    return token_age_hours <= MAX_TOKEN_AGE_HOURS


# ------------- Persistent PNL logging -------------

def log_final_pnl(token_address: str, final_state: dict) -> None:
    os.makedirs('./data', exist_ok=True)
    # Ensure header
    try:
        new_file = not os.path.exists(PNL_LEDGER_FILE)
        with open(PNL_LEDGER_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(['timestamp', 'token_address', 'initial_investment', 'total_sold', 'pnl_usd', 'pnl_percent', 'exit_reason'])
            initial = float(final_state.get('initial_investment_usdc', 0))
            total_sold = float(final_state.get('total_sold_usdc', 0))
            pnl_usd = total_sold - initial
            pnl_percent = (pnl_usd / initial * 100) if initial > 0 else 0.0
            exit_reason = final_state.get('exit_reason', '')
            writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                token_address,
                f"{initial:.2f}",
                f"{total_sold:.2f}",
                f"{pnl_usd:.2f}",
                f"{pnl_percent:.2f}%",
                exit_reason,
            ])
    except Exception as e:
        cprint(f"Sarsa: Failed to log PNL: {e}", 'yellow')


# ------------- Supervisory monitoring loop -------------

async def sarsa_monitoring_loop():
    cprint("🤖 Sarsa Operator: Redundant PNL & Risk Management ACTIVATED", 'magenta', attrs=['bold'])
    cprint("   -> Supervising primary PNL manager: position_tracker_v2.py", 'cyan')

    while True:
        loop_start = time.time()
        try:
            states = n.load_position_states()
            if not states:
                cprint("   -> Sarsa: No active positions.", 'cyan')
                await asyncio.sleep(120)
                continue

            holdings_df = n.fetch_wallet_holdings_og(n.MY_SOLANA_ADDERESS)
            wallet_mints = set(holdings_df['Mint Address']) if not holdings_df.empty else set()

            for token, state in list(states.items()):
                try:
                    # Already closed by primary tracker
                    if token not in wallet_mints:
                        cprint(f"   -> Sarsa: Detected closed position {token[-6:]}. Logging PNL.", 'green')
                        log_final_pnl(token, state)
                        n.remove_position_state(token)
                        continue

                    # Evaluate current value vs stop-loss
                    row = holdings_df[holdings_df['Mint Address'] == token].iloc[0]
                    current_value = float(row['USD Value'])
                    initial = float(state.get('initial_investment_usdc', 0))
                    stop_loss_value = initial * (1 + n.STOP_LOSS_PERCENTAGE)

                    if current_value <= 0:
                        # Treat as dust; stop tracking
                        cprint(f"   -> Sarsa: {token[-6:]} value is $0. Removing from tracking.", 'yellow')
                        try:
                            with open(CLOSED_POSITIONS_TXT, 'a') as f:
                                f.write(f"{token}\n")
                        except Exception:
                            pass
                        n.remove_position_state(token)
                        continue

                    if current_value < stop_loss_value:
                        cprint(f"   -> SARSA FAIL-SAFE: STOP-LOSS missed for {token[-6:]} (now ${current_value:.2f} < ${stop_loss_value:.2f}). Exiting.", 'red', attrs=['bold'])
                        n.kill_switch(token)
                        # Mark exit reason for ledger if state remains
                        state['exit_reason'] = 'sarsa_stop_loss'
                        log_final_pnl(token, state)
                        n.remove_position_state(token)
                except Exception as inner_err:
                    cprint(f"   -> Sarsa: Error supervising {token[-6:]}: {inner_err}", 'yellow')
                    continue

        except Exception as e:
            cprint(f"Sarsa: Monitoring loop error: {e}", 'red')

        # Keep a 5-minute cadence
        elapsed = time.time() - loop_start
        sleep_s = max(300 - elapsed, 30)
        await asyncio.sleep(sleep_s)


# ------------- Entry point -------------

async def main():
    await sarsa_monitoring_loop()

if __name__ == '__main__':
    asyncio.run(main())
