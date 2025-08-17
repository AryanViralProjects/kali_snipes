Plan: Building "Sarsa," the AI Operator for Kali Sniper BotObjective: To develop and integrate "Sarsa," an intelligent agentic layer that enhances the Kali sniper bot with advanced risk management, external data verification (web search), and redundant position management.🧠 Part 1: Sarsa's Core Responsibilities & ArchitectureSarsa will operate as a high-level supervisor, running in a separate process that monitors and commands the core sniper bot's components.Token Age Verification: Use a fast API call to check token age first. If data is unavailable (as expected for new tokens), use the Perplexity API as a fallback to find the true age and prevent snipes on old coins.Redundant Risk Management: Act as a supervisory fail-safe for your primary PNL system (position_tracker_v2.py), ensuring no position is left unmanaged in case of a failure or stall in the primary system.Performance Logging: Maintain a persistent PNL ledger for historical performance analysis.New Files Required:sarsa_operator.py: The main entry point and logic for the Sarsa agent../data/pnl_ledger.csv: A new persistent file to record the outcome of every closed trade../data/token_age_cache.json: A cache to store token ages found via web search to reduce redundant API calls.🛠️ Part 2: Step-by-Step Implementation PlanStep 2.1: Optimized Token Age VerificationThis is Sarsa's most critical task. We will implement a two-stage verification process inside raydium_listener.py to ensure speed and accuracy.1. Update raydium_listener.py to perform the two-stage check:# In raydium_listener.py, inside trigger_fast_snipe()

import sarsa_operator # Import the new agent
import nice_funcs as n # To access the Birdeye API call
from datetime import datetime, timezone
from config import MAX_TOKEN_AGE_HOURS

async def trigger_fast_snipe(token_address, signature):
    cprint(f"🕵️ Verifying token age for {token_address[-6:]}", 'cyan')
    
    # === STAGE 1: FAST API CHECK ===
    # First, try to get the creation time directly from Birdeye's API.
    # This will be fast but will likely be 'null' for brand new tokens.
    creation_time = n.get_token_creation_time(token_address) # You will need to create this helper function
    
    is_new_enough = False
    if creation_time is not None:
        # If data exists, calculate age and decide
        age_seconds = (datetime.now(timezone.utc) - datetime.fromtimestamp(creation_time, tz=timezone.utc)).total_seconds()
        if age_seconds <= (MAX_TOKEN_AGE_HOURS * 3600):
            cprint(f"   -> ✅ API Check PASSED: Token age is {age_seconds/3600:.2f} hours.", 'green')
            is_new_enough = True
        else:
            cprint(f"   -> 🚫 API Check FAILED: Token is too old ({age_seconds/3600:.2f} hours).", 'red')
            return # Reject the token
    else:
        # === STAGE 2: SARSA WEB SEARCH (FALLBACK) ===
        # If Birdeye hasn't indexed the creationTime yet, consult Sarsa.
        cprint(f"   -> API Check: No creation time found. Consulting Sarsa Operator...", 'yellow')
        is_new_enough = await sarsa_operator.verify_token_age_via_search(token_address)
        if not is_new_enough:
            cprint(f"🚫 Sarsa Operator: REJECTED {token_address[-6:]} - Web search confirmed token is too old.", 'red', attrs=['bold'])
            return

    # If age check passes, proceed with the rest of the intelligence vetting
    cprint(f"✅ Sarsa Operator: Token age approved. Handing over to Kali's Intelligence Engine.", 'magenta')
    
    # ... (rest of the existing trigger_fast_snipe logic for security checks and buying)
2. Create the verify_token_age_via_search function in sarsa_operator.py:This function is now specifically for the web search fallback.# In sarsa_operator.py
import requests
from datetime import datetime, timedelta, timezone
import json
from config import MAX_TOKEN_AGE_HOURS

TOKEN_AGE_CACHE_FILE = './data/token_age_cache.json'

def load_age_cache():
    try:
        with open(TOKEN_AGE_CACHE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_age_cache(cache):
    with open(TOKEN_AGE_CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

async def verify_token_age_via_search(token_address):
    cache = load_age_cache()
    if token_address in cache:
        # Check if cached entry is still valid
        cached_age_hours = cache[token_address]['age_hours']
        if cached_age_hours <= MAX_TOKEN_AGE_HOURS:
            cprint(f"   -> Sarsa Cache: Age for {token_address[-6:]} is {cached_age_hours:.2f}h. OK.", 'green')
            return True
        else:
            cprint(f"   -> Sarsa Cache: Age for {token_address[-6:]} is {cached_age_hours:.2f}h. REJECTED.", 'red')
            return False

    cprint(f"   -> Sarsa: Performing web search for {token_address[-6:]} age using Perplexity...", 'yellow')
    
    # This placeholder simulates the web search result using the Perplexity API
    token_age_hours = get_age_from_perplexity(token_address)
    
    if token_age_hours is None:
        cprint(f"   -> Sarsa: Could not determine age via web search. Approving as 'new' (fail-safe).", 'yellow')
        return True # Fail-safe: if age can't be found, assume it's new
        
    # Update cache with the age found from the web search
    cache[token_address] = {'age_hours': token_age_hours, 'timestamp': datetime.now().isoformat()}
    save_age_cache(cache)

    if token_age_hours > MAX_TOKEN_AGE_HOURS:
        return False
    
    return True

def get_age_from_perplexity(token_address):
    """
    Uses the Perplexity API to find the token's creation date from a block explorer.
    Returns the age in hours, or None if not found.
    """
    # You will need to get a Perplexity API key and store it in your dontshare.py file
    # PERPLEXITY_API_KEY = d.perplexity_key
    
    # A highly specific prompt is key to getting a good result
    prompt = f"Go to the URL [https://solscan.io/token/](https://solscan.io/token/){token_address}. Find the 'Timestamp' of the very first transaction for this token. Return ONLY the UTC timestamp string (e.g., 'YYYY-MM-DD HH:MM:SS UTC')."
    
    # --- PSEUDO-CODE for Perplexity API call ---
    # headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
    # payload = {"model": "pplx-7b-online", "messages": [{"role": "user", "content": prompt}]}
    # response = requests.post("[https://api.perplexity.ai/chat/completions](https://api.perplexity.ai/chat/completions)", headers=headers, json=payload)
    #
    # if response.ok:
    #     result_text = response.json()['choices'][0]['message']['content']
    #     # Parse the timestamp string from result_text
    #     creation_dt = datetime.strptime(result_text, '%Y-%m-%d %H:%M:%S %Z')
    #     creation_dt = creation_dt.replace(tzinfo=timezone.utc)
    #     age_seconds = (datetime.now(timezone.utc) - creation_dt).total_seconds()
    #     return age_seconds / 3600
    # else:
    #     return None
    
    # For now, this remains a placeholder
    return None # Returning None to simulate a new, unindexed token.
Step 2.2: Redundant Risk & PNL ManagementSarsa will run its own monitoring loop, completely separate from your primary PNL manager (position_tracker_v2.py). Its role is not to replace the primary tracker, but to act as a supervisory fail-safe. It periodically checks on all open positions to ensure the primary tracker is functioning correctly. If it detects a position that should have been sold (e.g., it has breached the stop-loss) but hasn't been, Sarsa assumes the primary tracker has failed and takes emergency action.1. Create the main loop in sarsa_operator.py:# In sarsa_operator.py
import time
import nice_funcs as n
from config import STOP_LOSS_PERCENTAGE

async def sarsa_monitoring_loop():
    cprint("🤖 Sarsa Operator: Redundant PNL & Risk Management System ACTIVATED.", 'magenta', attrs=['bold'])
    cprint("   -> Supervising primary PNL manager: position_tracker_v2.py", 'cyan')
    while True:
        try:
            cprint("   -> Sarsa: Performing supervisory check...", 'magenta')
            
            states = n.load_position_states()
            if not states:
                cprint("   -> Sarsa: No active positions to supervise.", 'cyan')
                time.sleep(120) # Check every 2 minutes if no positions
                continue

            wallet_holdings = n.fetch_wallet_holdings_og(n.MY_SOLANA_ADDERESS)
            wallet_mints = set(wallet_holdings['Mint Address']) if not wallet_holdings.empty else set()

            for token, state in list(states.items()):
                # If position is no longer in wallet, it means it was sold by the primary tracker.
                if token not in wallet_mints:
                    cprint(f"   -> Sarsa: Detected closed position for {token[-6:]}. Logging PNL.", 'green')
                    log_final_pnl(token, state) # Call the PNL logger
                    n.remove_position_state(token) # Clean up the state file
                    continue
                
                # If position still exists, Sarsa checks if the primary tracker has missed a stop-loss.
                position_row = wallet_holdings[wallet_holdings['Mint Address'] == token].iloc[0]
                current_value = position_row['USD Value']
                initial_investment = state['initial_investment_usdc']
                
                # Sarsa's Fail-safe Check
                stop_loss_value = initial_investment * (1 + STOP_LOSS_PERCENTAGE)
                if current_value < stop_loss_value:
                    cprint(f"   -> SARSA FAIL-SAFE TRIGGERED! STOP-LOSS MISSED FOR {token[-6:]}", 'red', attrs=['bold'])
                    cprint(f"   -> Sarsa is taking control and executing emergency exit.", 'red')
                    n.kill_switch(token)

        except Exception as e:
            cprint(f"   -> Sarsa Error: An error occurred in the monitoring loop: {e}", 'red')
            
        time.sleep(300) # Sarsa checks every 5 minutes
Step 2.3: Persistent PNL LoggingThis function is called by Sarsa when it detects a closed position.1. Create the PNL logger in sarsa_operator.py:# In sarsa_operator.py
import csv
from datetime import datetime

PNL_LEDGER_FILE = './data/pnl_ledger.csv'

def log_final_pnl(token_address, final_state):
    # Ensure the CSV file has a header
    try:
        with open(PNL_LEDGER_FILE, 'x', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'token_address', 'initial_investment', 'total_sold', 'pnl_usd', 'pnl_percent'])
    except FileExistsError:
        pass # Header already exists

    initial = final_state.get('initial_investment_usdc', 0)
    total_sold = final_state.get('total_sold_usdc', 0) # This comes from the tiered sells

    # If total_sold is 0, it means a stop-loss was hit and we sold at current value (which is now 0).
    # This is a simplification; a more robust system would record the exit value of the SL.
    # For now, we assume a total loss if no tiers were sold.
    if total_sold == 0:
        pnl_usd = -initial
    else:
        pnl_usd = total_sold - initial
        
    pnl_percent = (pnl_usd / initial * 100) if initial > 0 else 0
    
    # Write the final PNL record
    with open(PNL_LEDGER_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            token_address,
            f"{initial:.2f}",
            f"{total_sold:.2f}",
            f"{pnl_usd:.2f}",
            f"{pnl_percent:.2f}%"
        ])
Step 2.4: Launching SarsaSarsa runs as its own process. You would launch it in a separate terminal after starting the main bot and the primary position tracker.# Terminal 1: Launch the main sniper bot
python main_speed_engine.py speed

# Terminal 2: Launch the primary PNL manager
python position_tracker_v2.py

# Terminal 3: Launch the Sarsa AI Operator
python sarsa_operator.py
This architecture provides a powerful separation of concerns. The Kali bot focuses on high-speed execution, position_tracker_v2.py handles high-frequency PNL, and Sarsa provides the slower, more thoughtful oversight, external data gathering, and resilience.