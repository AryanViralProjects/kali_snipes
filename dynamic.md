# Tier 1 Strategy Engine Upgrade Plan for Kali Sniper Bot

**Objective:** To replace the rigid, fixed-percentage trading strategy with a dynamic system that adapts to market conditions, protects capital aggressively, and maximizes profits from winning trades.

---

## Part 1: Dynamic Position Sizing

**Problem:** The current bot uses a fixed `USDC_SIZE` for every trade, regardless of the token's initial liquidity. This is suboptimal and can be risky. A $5 buy into a $500 liquidity pool is a huge entry (10%) that can cause massive slippage, while a $5 buy into a $50,000 pool is a tiny fraction.

**Solution:** We will adjust the buy-in amount to be relative to the token's initial liquidity, capped by a maximum size.

### Step 1.1: Modify `config.py`

Let's add a few parameters to control this new behavior.

```python
# In config.py

############### main.py configurations ###############
# ... (existing configurations)

# NEW DYNAMIC SIZING CONFIG
USDC_BUY_TARGET_PERCENT_OF_LP = 0.005 # Target buying 0.5% of the initial liquidity
USDC_MAX_BUY_SIZE = 10 # The absolute maximum USDC to spend on a single trade ($10)
USDC_MIN_BUY_SIZE = 4 # The absolute minimum USDC to spend on a single trade ($4)
Step 1.2: Update The Buying LogicWe'll modify the open_position function in nice_funcs.py to use these new parameters. It will require the token's liquidity, which you can get from the token_overview function you already have.# In nice_funcs.py, inside the open_position function

def open_position(token_mint_address):
    cprint(f'🌙 Kali: Evaluating position for token: {token_mint_address}', 'white', 'on_blue')

    # ... (all your blacklist and existing position checks)

    # --- Fetch Liquidity for Dynamic Sizing ---
    token_overview_data = get_token_overview(token_mint_address) # You already have this helper function
    if not token_overview_data:
        cprint(f'⚠️ Kali: Could not get token overview for {token_mint_address}, skipping', 'white', 'on_red')
        return

    liquidity = token_overview_data.get('liquidity', 0)
    if liquidity == 0:
        cprint(f'⚠️ Kali: Token {token_mint_address} has zero liquidity, skipping', 'white', 'on_red')
        return

    # --- Calculate Dynamic Buy Size ---
    target_buy_size = liquidity * USDC_BUY_TARGET_PERCENT_OF_LP
    
    # Clamp the buy size between your defined min and max
    actual_buy_size = max(USDC_MIN_BUY_SIZE, min(target_buy_size, USDC_MAX_BUY_SIZE))
    
    cprint(f'💡 Kali: LP is ${liquidity:,.2f}. Target buy: ${target_buy_size:,.2f}. Actual buy: ${actual_buy_size:,.2f}', 'cyan')

    size_needed_in_lamports = int(actual_buy_size * 10**6) # Convert final USDC size to lamports
    size_needed_str = str(size_needed_in_lamports)

    # --- Call your fast market buy with the new dynamic size ---
    # if not market_buy_fast(token_mint_address, size_needed_str): # Assumes you are using the new fast function
    # ... (rest of your execution logic)
Part 2: Realistic PNL Management & Tiered ExitsProblem: The current strategy of selling 70% at +50% profit and holding on until a -60% loss is not optimal. The stop-loss is too wide (inviting catastrophic losses) and the take-profit is too simple (missing out on 10x+ runners).Solution: We will implement a much tighter stop-loss and a multi-stage, tiered take-profit system. This requires a way to track the state of each open position.Step 2.1: Update config.py with New Strategy Parameters# In config.py

############### main.py configurations ###############
# ... (existing configurations)

SELL_AT_MULTIPLE = 1.5 # This will now be our FIRST profit target
STOP_LOSS_PERCENTAGE = -0.25 # TIGHTEN THIS! -0.25 = down 25%. A much more realistic SL.

# NEW TIERED SELLING STRATEGY
# This defines our profit-taking plan.
# We sell a PORTION of the REMAINING position at each tier.
SELL_TIERS = [
    # Tier 1: At 100% profit (2x), sell 50% of the current holdings.
    {'profit_multiple': 2.0, 'sell_portion': 0.5},
    
    # Tier 2: At 400% profit (5x), sell 50% of the NEW current holdings.
    {'profit_multiple': 5.0, 'sell_portion': 0.5},
    
    # Tier 3: At 1000% profit (11x), sell 75% of the NEW current holdings.
    {'profit_multiple': 11.0, 'sell_portion': 0.75}
]

# NEW STATE-TRACKING FILE
OPEN_POSITIONS_STATE_FILE = './data/open_positions_state.json'
Step 2.2: Create a Position State Management SystemYour bot needs to remember what it has done for each trade. A simple JSON file is perfect for this.Create a new file: ./data/open_positions_state.json and leave it empty initially: {}Add new helper functions to nice_funcs.py to manage this state file.# In nice_funcs.py

import json
import os

def load_position_states():
    """Loads the state of all open positions from the JSON file."""
    if not os.path.exists(OPEN_POSITIONS_STATE_FILE):
        return {}
    with open(OPEN_POSITIONS_STATE_FILE, 'r') as f:
        return json.load(f)

def save_position_states(states):
    """Saves the state of all open positions to the JSON file."""
    with open(OPEN_POSITIONS_STATE_FILE, 'w') as f:
        json.dump(states, f, indent=4)

# You will call this function right after a successful buy
def record_new_position(token_address, buy_size_usdc):
    """Records a new position in the state file."""
    states = load_position_states()
    if token_address not in states:
        states[token_address] = {
            "initial_investment_usdc": buy_size_usdc,
            "tiers_sold": [] # A list to record which profit tiers have been hit
        }
        save_position_states(states)

# You will call this after fully closing a position (SL or final TP)
def remove_position_state(token_address):
    """Removes a position's state upon full exit."""
    states = load_position_states()
    if token_address in states:
        del states[token_address]
        save_position_states(states)
Step 2.3: Re-architect the Main PNL Loop in main.pyThis is the most significant change. You need to replace your current PNL logic with a new loop that checks each open position against the tiered strategy.# In main.py, inside the bot() function, replace the entire PNL section

def bot():
    # ... (SOL balance check and other initial logic)

    cprint("\n📈 Kali: Running PNL Management Engine...", 'white', 'on_blue')

    open_positions_df = n.fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
    position_states = n.load_position_states()

    # Create a set of mints we have in our wallet for quick lookup
    wallet_mints = set(open_positions_df['Mint Address'])

    # Iterate through the positions we are TRACKING
    for mint, state in list(position_states.items()):
        
        # Check if we still hold this token. If not, remove from tracking.
        if mint not in wallet_mints:
            cprint(f'👻 Kali: Position {mint} no longer in wallet. Removing from state.', 'yellow')
            n.remove_position_state(mint)
            continue

        # Get current value of this position
        position_row = open_positions_df[open_positions_df['Mint Address'] == mint].iloc[0]
        current_usd_value = position_row['USD Value']
        initial_investment = state['initial_investment_usdc']
        
        # --- 1. STOP-LOSS CHECK (HIGHEST PRIORITY) ---
        stop_loss_value = initial_investment * (1 + STOP_LOSS_PERCENTAGE)
        if current_usd_value < stop_loss_value:
            cprint(f'🚨 Kali: STOP-LOSS triggered for {mint}! Value ${current_usd_value:,.2f} < SL ${stop_loss_value:,.2f}', 'white', 'on_red')
            n.kill_switch(mint) # Your full-exit function
            n.remove_position_state(mint) # Clean up state
            continue # Move to the next tracked position

        # --- 2. TIERED TAKE-PROFIT CHECK ---
        for i, tier in enumerate(SELL_TIERS):
            tier_profit_value = initial_investment * tier['profit_multiple']
            
            # Check if we crossed the profit threshold AND we haven't sold this tier yet
            if current_usd_value >= tier_profit_value and i not in state['tiers_sold']:
                cprint(f'💰 Kali: TIER {i+1} PROFIT hit for {mint}! Value ${current_usd_value:,.2f} > TP ${tier
