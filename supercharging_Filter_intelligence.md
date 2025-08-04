# Tier 1 Intelligence Engine Upgrade Plan for Kali Sniper Bot

**Objective:** To create a robust, multi-stage filtering pipeline that instantly analyzes new tokens for security risks and historical red flags, ensuring the bot only trades high-potential assets.

---

## Part 1: Pre-Trade Security & Sanity Checks

**Problem:** The current filtering in `get_new_tokens.py` happens too late and isn't integrated into the high-speed workflow.

**Solution:** We will create a single, fast function that runs immediately after a new pool is detected by the WebSocket listener. This function will use your Birdeye API to perform a rapid-fire security assessment.

### Step 1.1: Consolidate and Enhance Security Filtering

We will modify `nice_funcs.py` to include a comprehensive, all-in-one security function. This function will be called by your `raydium_listener.py` script.

```python
# In nice_funcs.py

# ... other imports
from termcolor import cprint
import requests
import dontshare as d # Your API keys

# This function combines security and initial liquidity checks
def pre_trade_token_vetting(token_address, birdeye_api_key, helius_rpc_url):
    """
    Performs a rapid, pre-trade analysis of a token.
    Returns True if the token passes all checks, False otherwise.
    """
    cprint(f"🔬 Vetting token: {token_address}", 'yellow')

    # === Birdeye Security Check ===
    try:
        sec_url = f"[https://public-api.birdeye.so/defi/token_security?address=](https://public-api.birdeye.so/defi/token_security?address=){token_address}"
        sec_headers = {"X-API-KEY": birdeye_api_key}
        sec_response = requests.get(sec_url, headers=sec_headers, timeout=5) # 5-second timeout
        
        if sec_response.status_code != 200:
            cprint(f"   -> ❌ VETTING FAILED: Birdeye security API error (Code: {sec_response.status_code})", 'red')
            return False
            
        security_data = sec_response.json().get('data', {})
        if not security_data:
            cprint("   -> ❌ VETTING FAILED: No security data returned from Birdeye.", 'red')
            return False

        # --- Your Existing Filters (Now faster and pre-trade) ---
        if security_data.get('isToken2022'):
            cprint("   -> ❌ VETTING FAILED: Token 2022 Program is a no-go.", 'red')
            return False

        if security_data.get('mutableMetadata'):
            cprint("   -> ❌ VETTING FAILED: Metadata is mutable.", 'red')
            return False

        if security_data.get('freezeAuthority') is not None:
            cprint("   -> ❌ VETTING FAILED: Token is freezable.", 'red')
            return False
        
        top_10_pct = security_data.get('top10HolderPercent', 1.0) # Default to 100% if not found
        if top_10_pct > 0.7: # Using your config's 70% threshold
            cprint(f"   -> ❌ VETTING FAILED: Top 10 holders have {top_10_pct:.2%}, which is too high.", 'red')
            return False
            
    except requests.exceptions.RequestException as e:
        cprint(f"   -> ❌ VETTING FAILED: Network error during security check: {e}", 'red')
        return False
        
    # === Birdeye Liquidity & Market Cap Check ===
    try:
        overview_url = f"[https://public-api.birdeye.so/defi/token_overview?address=](https://public-api.birdeye.so/defi/token_overview?address=){token_address}"
        overview_headers = {"X-API-KEY": birdeye_api_key}
        overview_response = requests.get(overview_url, headers=overview_headers, timeout=5)
        
        if overview_response.status_code != 200:
            cprint(f"   -> ❌ VETTING FAILED: Birdeye overview API error (Code: {overview_response.status_code})", 'red')
            return False
        
        overview_data = overview_response.json().get('data', {})
        if not overview_data:
            cprint("   -> ❌ VETTING FAILED: No overview data returned from Birdeye.", 'red')
            return False
            
        liquidity = overview_data.get('liquidity', 0)
        market_cap = overview_data.get('mc', 0)
        
        # --- Your Existing Sanity Checks ---
        if liquidity < 400: # Using your config's MIN_LIQUIDITY
            cprint(f"   -> ❌ VETTING FAILED: Insufficient liquidity (${liquidity:,.2f})", 'red')
            return False
            
        if market_cap > 30000: # Using your config's MAX_MARKET_CAP
             cprint(f"   -> ❌ VETTING FAILED: Market cap too high (${market_cap:,.2f})", 'red')
             return False

    except requests.exceptions.RequestException as e:
        cprint(f"   -> ❌ VETTING FAILED: Network error during overview check: {e}", 'red')
        return False

    cprint(f"   -> ✅ VETTING PASSED: Token {token_address} looks clean.", 'green')
    return True
Step 1.2: Integration with the WebSocket ListenerNow, you will call this new function from raydium_listener.py before you even consider buying.# In raydium_listener.py, modify the process_new_pool function

# Make sure to import your new function and other necessities
from nice_funcs import pre_trade_token_vetting, market_buy_fast
import dontshare as d
from solders.keypair import Keypair
from solana.rpc.api import Client

# Initialize these once when the listener starts
KEYPAIR = Keypair.from_base58_string(d.sol_key)
HTTP_CLIENT = Client(d.rpc_url_https) # Assumes you have a separate HTTPS URL in dontshare.py

async def process_new_pool(signature):
    """
    Fetches transaction details, extracts token mints, and runs pre-trade checks.
    """
    cprint(f"   -> Processing signature: {signature}", 'cyan')
    
    # --- Step 1: Get Transaction and Extract Mints ---
    # (This logic needs to be built using your Helius HTTPS RPC)
    # response = HTTP_CLIENT.get_transaction(signature, max_supported_transaction_version=0)
    # base_token_address = parse_base_mint_from_tx(response)
    # quote_token_address = parse_quote_mint_from_tx(response)
    
    # For demonstration, let's assume we extracted the new token's address
    # and the other token was SOL or USDC (which we ignore)
    new_token_address = "ADDRESS_EXTRACTED_FROM_TX" 

    # --- Step 2: Run the Intelligence Filter ---
    is_safe = pre_trade_token_vetting(new_token_address, d.birdeye, d.rpc_url_https)

    if not is_safe:
        cprint(f"   -> Bot Decision: REJECTED token {new_token_address}", 'magenta')
        return # Stop processing and wait for the next pool

    # --- Step 3: If Safe, Execute High-Speed Buy ---
    cprint(f"   -> Bot Decision: APPROVED token {new_token_address}. Preparing to snipe.", 'green', attrs=['bold'])
    
    # Convert your USDC_SIZE from config.py to lamports
    usdc_amount_lamports = 5 * 1_000_000 # Example: 5 USDC
    
    # market_buy_fast(
    #     token_to_buy=new_token_address,
    #     usdc_amount_in_lamports=usdc_amount_lamports,
    #     keypair=KEYPAIR,
    #     http_client=HTTP_CLIENT
    # )

Part 2: Deployer Wallet Analysis (Rug-Pull History)Problem: Scammers often reuse wallets to launch multiple fraudulent tokens. Your bot is blind to this history.Solution: We will create a simple, persistent database to track deployer wallets and check against it before trading.Step 2.1: Augment the Blacklisting SystemWe'll create a new blacklist specifically for deployer wallets.Create a new file in your ./data/ directory named deployer_blacklist.txt.Each line in this file will be a Solana wallet address known for launching rugs.Step 2.2: Create the Deployer Check FunctionAdd a new function to nice_funcs.py to handle this check.# In nice_funcs.py

def get_deployer_address(token_address, birdeye_api_key):
    """
    Gets the creator/deployer address of a token from Birdeye.
    """
    try:
        url = f"[https://public-api.birdeye.so/defi/token_security?address=](https://public-api.birdeye.so/defi/token_security?address=){token_address}"
        headers = {"X-API-KEY": birdeye_api_key}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get('data', {}).get('creatorAddress')
    except Exception:
        return None

def check_deployer_blacklist(deployer_address):
    """
    Checks if a deployer wallet is on the blacklist.
    Returns True if blacklisted, False otherwise.
    """
    if not deployer_address:
        return False # Can't check a null address
        
    try:
        with open('./data/deployer_blacklist.txt', 'r') as f:
            blacklist = {line.strip() for line in f}
        
        if deployer_address in blacklist:
            cprint(f"   -> ❌ VETTING FAILED: Deployer wallet {deployer_address} is on the blacklist.", 'red', attrs=['bold'])
            return True
            
    except FileNotFoundError:
        # If the file doesn't exist, it can't be blacklisted.
        return False
        
    return False

# You will also need a function to ADD to the blacklist later
def add_deployer_to_blacklist(deployer_address):
    """Adds a deployer address to the blacklist."""
    if not deployer_address:
        return
    with open('./data/deployer_blacklist.txt', 'a') as f:
        f.write(f"{deployer_address}\n")

Step 2.3: Integration into the Vetting PipelineFinally, add this check into your pre_trade_token_vetting function in nice_funcs.py.# In nice_funcs.py, inside the pre_trade_token_vetting function:

def pre_trade_token_vetting(token_address, birdeye_api_key, helius_rpc_url):
    # ... (all the other checks from before)

    # === Deployer History Check (NEW) ===
    deployer = get_deployer_address(token_address, birdeye_api_key)
    if check_deployer_blacklist(deployer):
        # The check_deployer_blacklist function already prints the reason
        return False

    # ... (rest of the function)

    cprint(f"   -> ✅ VETTING PASSED: Token {token_address} looks clean.", 'green')
    return True
This intelligence upgrade transforms your bot from a blind sniper into a discerning hunter. It will now automatically reject the vast majority of scams and low-quality tokens, saving you capital and significantly increasing the probability that your trades are on legitimate