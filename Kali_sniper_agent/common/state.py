import json
import os
from termcolor import cprint
from config import OPEN_POSITIONS_STATE_FILE, SELL_TIERS
import time

def load_position_states():
    try:
        if not os.path.exists(OPEN_POSITIONS_STATE_FILE):
            os.makedirs('./data', exist_ok=True)
            with open(OPEN_POSITIONS_STATE_FILE, 'w') as f:
                json.dump({}, f, indent=4)
            return {}
        with open(OPEN_POSITIONS_STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        cprint(f"⚠️ Kali State: Error loading position states: {e}", 'yellow')
        return {}

def save_position_states(states):
    try:
        os.makedirs('./data', exist_ok=True)
        with open(OPEN_POSITIONS_STATE_FILE, 'w') as f:
            json.dump(states, f, indent=4)
    except Exception as e:
        cprint(f"❌ Kali State: Error saving position states: {e}", 'red')

def record_new_position(token_address, buy_size_usdc, liquidity=0):
    try:
        cprint(f"📝 Kali State: Recording new position for {token_address[-6:]}", 'cyan')
        cprint(f"   Investment: ${buy_size_usdc:.2f}, Liquidity: ${liquidity:,.0f}", 'cyan')
        states = load_position_states()
        if token_address not in states:
            states[token_address] = {
                "initial_investment_usdc": float(buy_size_usdc),
                "initial_liquidity": float(liquidity),
                "tiers_sold": [],
                "entry_timestamp": time.time(),
                "total_sold_usdc": 0.0,
                "strategy_type": "tiered_dynamic"
            }
            save_position_states(states)
            cprint(f"📊 Kali State: Position recorded - ${buy_size_usdc:.2f} into {token_address[-6:]}", 'white', 'on_green')
        else:
            cprint(f"⚠️ Kali State: Position {token_address[-6:]} already tracked", 'yellow')
    except Exception as e:
        cprint(f"❌ Kali State: Error recording position: {e}", 'red')

def update_position_tier_sold(token_address, tier_index, sell_amount_usdc):
    try:
        states = load_position_states()
        if token_address in states:
            if tier_index not in states[token_address]['tiers_sold']:
                states[token_address]['tiers_sold'].append(tier_index)
                states[token_address]['total_sold_usdc'] += float(sell_amount_usdc)
                save_position_states(states)
                tier_name = SELL_TIERS[tier_index]['name'] if tier_index < len(SELL_TIERS) else f"Tier {tier_index + 1}"
                cprint(f"💰 Kali State: {tier_name} executed for {token_address[-6:]} (+${sell_amount_usdc:.2f})", 'white', 'on_green')
        else:
            cprint(f"⚠️ Kali State: Position {token_address[-6:]} not found in tracking", 'yellow')
    except Exception as e:
        cprint(f"❌ Kali State: Error updating tier: {e}", 'red')

def remove_position_state(token_address):
    try:
        states = load_position_states()
        if token_address in states:
            state = states[token_address]
            initial = state.get('initial_investment_usdc', 0)
            total_sold = state.get('total_sold_usdc', 0)
            tiers_executed = len(state.get('tiers_sold', []))
            profit_loss = total_sold - initial
            profit_percent = (profit_loss / initial * 100) if initial > 0 else 0
            cprint(f"📊 Kali State: Closing {token_address[-6:]} | P&L: ${profit_loss:+.2f} ({profit_percent:+.1f}%)", 'white', 'on_blue')
            cprint(f"   Tiers executed: {tiers_executed}/{len(SELL_TIERS)} | Total sold: ${total_sold:.2f}", 'blue')
            del states[token_address]
            save_position_states(states)
        else:
            cprint(f"⚠️ Kali State: Position {token_address[-6:]} not found for removal", 'yellow')
    except Exception as e:
        cprint(f"❌ Kali State: Error removing position state: {e}", 'red')
