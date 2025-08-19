### FILE DIRECTORIES ####
CLOSED_POSITIONS_TXT = './data/closed_positions.txt'
FILTERED_PRICECHANGE_URLS_CSV = './data/filtered_pricechange_with_urls.csv'
FINAL_SORTED_CSV = './data/final-sorted.csv'
HYPER_SORTED_CSV = './data/hyper-sorted-sol.csv'
NEW_LAUNCHED_CSV = './data/new_launches.csv'
READY_TO_BUY_CSV = './data/ready_to_buy.csv'
TOKEN_PER_ADDY_CSV = './data/token_per_addy.csv'
VIBE_CHECKED_CSV = './data/vibe_checked.csv'
FILTERED_WALLET_HOLDINGS = './data/filtered_wallet_holdings.csv'
PRE_MCAP_FILTER_CSV = './data/pre_mcap_filter.csv'
ALL_NEW_TOKENS = './data/all_new_tokens.csv'
PERMANENT_BLACKLIST = './data/permanent_blacklist.txt'


# Blacklist reasons that will cause permanent blacklisting
PERMANENT_BLACKLIST_REASONS = [
    'token_2022_program',  # Token uses 2022 program
    'mutable_metadata',    # Token has mutable metadata
    'top_holder_percent',  # Top holders own too much
    'freezable',          # Token can be frozen
    'min_liquidity',      # Below minimum liquidity
    'security_check'      # Failed security check
]

# Minute marks to run token scanning (00, 15, 30, 45)
SCAN_MINUTE_MARKS = [0, 15, 30, 45]

# below are all of the variables we can change in the bot, change them here opposed to in the files
# this bot trades USDC / token on solana 
# keep a little SOl in your wallet to pay for fees and USDC is the trading token

############### main.py configurations ###############

EXIT_ALL_POSITIONS = False # when this is set to true, we are exiting all positions in FULL
DO_NOT_TRADE_LIST = ['cf8CqpDqTy8NURoyiJer7Ri42XyxMuWVirNQ5E6pump','DsfwbGtT2pSFaFTZUe6hwwir2wQvFvXsYahC4uv6T85y', 'Q1BaFmfN8TXdMVS98RYMhFZWRzVTCp8tUDhqM9CgcAL','HiZZAjSHf8W53QPtWYzj1y9wqhdirg124fiEHFGiUpQh', 'AuabGXArmR3QwuKxT3jvSViVPscQASkFAvnGDQCE8tfm','rxkExwV2Gay2Bf1so4chsZj7f4MiLKTx45bd9hQy6dK','BmDXugmfBhqKE7S2KVdDnVSNGER5LXhZfPkRmsDfVuov','423scBCY2bzX6YyqwkjCfWN114JY3xvyNNZ1WsWytZbF','7S6i87ZY29bWNbkviR2hyEgRUdojjMzs1fqMSXoe3HHy', '8nBNfJsvtVmZXhbyLCBg3ndVW2Zwef7oHuCPjQVbRqfc','FqW3CJYF3TfR49WXRusxqCbJMNSjnay1A51sqP34ZxcB','EwsHNUuAtPc6SHkhMu8sQoyL6R4jnWYUU1ugstHXo5qQ', '9Y9yqdNUL76v1ybpkQnVUj35traGEHXTBJB2b1iszFVv', 'Fd1hzhprThxCwz2tv5rTKyFeVCyEKRHaGqhT7hDh4fsW', '83227N9Fq4h1HMNnuKut61beYcB7fsCnRbzuFDCt2rRQ', 'J1oqg1WphZaiRDTfq7gAXho6K1xLoRMxVvVG5BBva3fh', 'GEvQuL9DT2UDtuTCCyjxm6KXEc7B5oguTHecPhKad8Dr', '7jjxmbPSUBVj87Zx9VMb7smNB7YsyxMDFbCDoTECRgAF']
# to never open a position on tokens like USDC since thats the base, and tokens that may be frozen or broken, place above
# can also put in closed_position.txt but if the bot gets into a frozen token, closed_positions wont work and youll need to put above
USDC_CA = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'

MY_SOLANA_ADDERESS =  "B5MYmAaSAyiJ7dLNfyhHNMTyp3oGye6cYPe8h6taU6qp" # PUT YOUR ADDRESS HERE
USDC_SIZE = 4
MAX_POSITIONS = 3
SELL_AT_MULTIPLE = 1.5 # Exit at 50% profit (1.5x the investment) 
STOP_LOSS_PERCENTAGE = -.6 # -.7 = down 70%, set to -.99 to essentialy disable
SELL_AMOUNT_PERCENTAGE = 0.7 # Sell 70% of position when taking profits, keep 30% for bigger gains 
orders_per_open = 1

SLIPPAGE = 499  # 5000 is 50%, 500 is 5% and 50 is .5%
PRIORITY_FEE = 20000 # 200000 is about .035 usd at 150 sol, after a bit of testing 100000 is sufficient and is .02 usd
SELL_SLIPPAGE_BPS = 3000  # 30% max slippage for exit swaps (tracker)
DUST_USD_THRESHOLD = 0.25  # Do not attempt sells when position value <= this
DYNAMIC_SLIPPAGE_STEPS_BPS = [100, 200, 300, 400, 500]  # 1% -> 5%

############### SPEED ENGINE CONFIGURATIONS ###############
SPEED_ENGINE_PRIORITY_FEE = 50000  # Higher priority fee for ultra-fast execution
SPEED_ENGINE_SLIPPAGE = 3000  # 30% slippage for highly volatile new tokens (enhanced for 0x1788 error prevention)
SPEED_ENGINE_TIMEOUT = 5  # Request timeout in seconds
ENABLE_SPEED_ENGINE_LOGGING = True  # Log speed engine snipes to file

############### INTELLIGENCE ENGINE CONFIGURATIONS ###############
INTELLIGENCE_VETTING_TIMEOUT = 50  # Maximum time for intelligence vetting (seconds) - increased for new token indexing
ENABLE_DEPLOYER_BLACKLIST = True  # Enable deployer wallet history checking
AUTO_BLACKLIST_BAD_PERFORMERS = True  # Auto-blacklist tokens that fail after purchase
INTELLIGENCE_LOG_REJECTIONS = True  # Log all rejected tokens for analysis

############### DYNAMIC STRATEGY ENGINE CONFIGURATIONS ###############
# Dynamic Position Sizing - DISABLED: Using fixed $3 trades instead
# USDC_BUY_TARGET_PERCENT_OF_LP = 0.005  # Target buying 0.5% of the initial liquidity
# USDC_MAX_BUY_SIZE = 3  # The absolute maximum USDC to spend on a single trade
# USDC_MIN_BUY_SIZE = 1   # The absolute minimum USDC to spend on a single trade

# Advanced Tiered Profit Taking Strategy
STOP_LOSS_PERCENTAGE = -0.10  # TIGHTENED: -25% stop loss (was -60%)
SELL_AT_MULTIPLE = 1.5  # This becomes our FIRST profit target (50% profit)

# Multi-Tier Profit Taking System
# Each tier sells a portion of REMAINING position at increasing profit levels
SELL_TIERS = [
    # Tier 1: At 50% profit (1.5x), sell 70% of current holdings
    {'profit_multiple': 1.5, 'sell_portion': 1.0, 'name': 'Take Profit'},

    # Tier 2: At 100% profit (2x), sell 50% of current holdings
    # {'profit_multiple': 2.0, 'sell_portion': 0.5, 'name': 'First Major Profit'},
    
    # # Tier 3: At 400% profit (5x), sell 50% of remaining holdings  
    # {'profit_multiple': 5.0, 'sell_portion': 0.5, 'name': 'Moon Shot'},
    
    # # Tier 4: At 1000% profit (11x), sell 75% of remaining holdings
    # {'profit_multiple': 11.0, 'sell_portion': 0.75, 'name': 'Generational Wealth'}
]

# Position State Tracking
OPEN_POSITIONS_STATE_FILE = './data/open_positions_state.json'
ENABLE_DYNAMIC_SIZING = True  # Disable dynamic position sizing - use fixed $3 trades
ENABLE_TIERED_EXITS = True    # Enable tiered profit taking system

# Position tracker ownership of exits
# When True, the external position tracker (position_tracker_v2.py) is responsible
# for all take-profit and stop-loss sells. The sniper bot will only buy.
POSITION_TRACKER_MANAGES_EXITS = True
ENABLE_POSITION_TRACKER = False  # Do NOT auto-start; run tracker as its own script

# Testing helper: if > 0, position tracker will force an exit
# for any tracked position whose age exceeds this threshold (seconds).
# Keep 0 in production and override via env var PTV2_FORCE_EXIT_SECONDS in tests.
TEST_FORCE_EXIT_SECONDS = 0



# === BIRDEYE SECURITY FILTER CONFIGURATIONS ===
# Based on official Birdeye Security Documentation: https://docs.birdeye.so/docs/security

# CRITICAL SEVERITY FILTERS (Auto-reject if True)
REJECT_FAKE_TOKENS = True                    # Scam/imitation tokens
REJECT_NON_RENOUNCED_OWNERSHIP = False       # 🔧 DISABLED: Allow non-renounced ownership (HIGHER RISK)  
REJECT_HONEYPOTS = True                      # Buyers can't sell
REJECT_FREEZABLE_TOKENS = True               # Can freeze token transfers
REJECT_TOKEN_2022 = True                     # New token standard (experimental)

# HIGH RISK FILTERS  
REJECT_MINTABLE_TOKENS = True                # Can create infinite supply
REJECT_MUTABLE_METADATA = False              # 🔧 FLEXIBLE: Allow mutable metadata (name/logo changes)
REJECT_TRANSFER_FEES = True                  # Charges fees on transfers
MAX_OWNER_PERCENTAGE = 0.30                  # Max % owner can hold (30%)
MAX_UPDATE_AUTHORITY_PERCENTAGE = 0.30       # Max % update authority can hold (30%)
MAX_TOP10_HOLDER_PERCENT = 0.70              # Max % top 10 holders can hold (70%)
MAX_BUY_TAX = 0.05                          # Max buy tax (5%)
MAX_SELL_TAX = 0.05                         # Max sell tax (5%)

# MEDIUM RISK FILTERS (Configurable)
ALLOW_MUTABLE_INFO = True                    # 🔧 FLEXIBLE: Allow changeable additional token info

# only scan birdeye for new tokens between these two times in minutes. ex. between the 1 and 15 minute mark of each hour
scan_start_min = 10
scan_end_min = 22
# same for pnl loss so they offset each other
pnl_start_min= 40
pnl_end_min = 58

# How many hours back to look for new token launches
HOURS_TO_LOOK_AT_NEW_LAUNCHES = 1.0

# Maximum token age to trade (reject tokens older than this)
MAX_TOKEN_AGE_HOURS = 1.0  # Only trade tokens created within last 24 hours

# === FRESHNESS FILTER (Low-latency 1m OHLCV gate) ===
# Enable to reject older tokens quickly before heavy checks
ENABLE_FRESHNESS_FILTER = True
# Reject if more than this many 1-minute candles are present in recent window
FRESH_MAX_1M_CANDLES = 8
# OHLCV lookback window in minutes for freshness evaluation
FRESH_INITIAL_WINDOW_MIN = 15
# Momentum check on first few 1m candles
FRESH_ENABLE_MOMENTUM_CHECK = True
FRESH_MIN_VOLUME_USD_FIRST5 = 15000  # Sum of volumes of first up-to-5 candles
# Catastrophic dump threshold between first two candles (80% drop)
FRESH_CATASTROPHIC_DUMP_RATIO = 0.3
# Buy/Sell pressure check (proxy via Birdeye overview buy1h/sell1h unless unique data available)
FRESH_ENABLE_PRESSURE_CHECK = True
FRESH_MIN_BUY_SELL_RATIO = 3.0
FRESH_USE_OVERVIEW_COUNTS_AS_PROXY = True

# === PUMP FILTER (Target strong 5-minute momentum) ===
ENABLE_PUMP_FILTER = True
# Minimum USD volume across last 5 one-minute candles (softer)
PUMP_MIN_VOL_5M_USD = 10000
# Minimum number of green candles in last 5 (softer)
PUMP_MIN_GREEN_CANDLES_5M = 3
# Minimum price change over last 5 minutes (softer)
PUMP_MIN_PRICE_CHANGE_5M_PCT = 0.15
# Minimum liquidity to engage pumps (softer)
PUMP_MIN_LIQUIDITY = 3000
# Minimum market cap to avoid micro-caps (allow unknown/zero)
PUMP_MIN_MARKET_CAP = 0
# Reject if top 10 holders exceed this (reuse MAX_TOP10_HOLDER_PERCENT if desired)
PUMP_MAX_TOP10_HOLDER_PERCENT = 0.50
PUMP_HOLDER_CHECK_MIN_WALLETS = 20
PUMP_HOLDER_CHECK_MIN_TRADES = 10
# Name-based keyword blacklist (case-insensitive substring match)
NAME_BLOCKLIST_KEYWORDS = [
    'deepseek',          # blocks Deepseek / Deepseek AI
    'deep seek',
    'deepseek ai',
    'deepseekai',
]

############### ohlcv_filter.py configurations ###############
MAX_SELL_PERCENTAGE = 100 
MIN_TRADES_LAST_HOUR = 9
MIN_UNQ_WALLETS2HR = 30
MIN_VIEW24H = 15
MIN_LIQUIDITY = 400
BASE_URL = "https://api.birdeye.so/v1"
MAX_MARKET_CAP = 30000

############### SEQUENTIAL TRADING MODE ###############
# When enabled, bot will only trade one position at a time
# It will wait for current position to hit profit target or stop loss before taking new trades
ENABLE_SEQUENTIAL_MODE = False # Set to False for multiple concurrent positions

# Maximum time to hold a position before force closing (hours)
# Set to 0 to disable time-based exits
MAX_POSITION_HOLD_TIME = 0  # Disabled by default, rely on profit/loss targets

# Log file for skipped opportunities in sequential mode
SEQUENTIAL_SKIPPED_LOG = './data/sequential_skipped.txt'

############### ohlcv_filter.py configurations ###############
# in this section a lot is hard coded, so dive into the file if you want to make tweaks

TIMEFRAME = '3m' # 1m, 3m 5m, 15m, 1h, 4h, 1d

# NEW 3/9
max_amount_of_bars_before_dropping = 120 #00 # 120 bars is 6 hours if over that amount of bars, we dropping
# the above is how you can make sure that the bot only trades on new tokens... for example:
# if you use a 5m time frame, and you say max_amount_of_bars_before_dropping = 10 
# then 10 * 5 == 50 minutes, so if the token has been trading for more than 50 minutes, we drop it
# if you want to go under 80 in the above, use a smaller timeframe like the 1min
# another thing to make sure its not already rugged, here we check the avg close price and if the last close is > avg, we keep, if not, we drop
only_keep_if_above_avg_close = True # if the close is above the average close, keep it 

get_new_data = True 
max_market_cap_to_scan_for = 30000 # og is 30000
min_market_cap_to_scan_for = 50
number_of_tokens_to_search_through = 50000 # og 15000
minimum_24hour_volume_of_tokens = 1000 


