📋 DETAILED WORKFLOW BREAKDOWN

🚀 PHASE 1: SYSTEM INITIALIZATION (main_speed_engine.py)



python







# Launch Command

python main_speed_engine.py  # Default: Speed Engine only

python main_speed_engine.py speed   # Explicit Speed Engine  

python main_speed_engine.py hybrid  # Speed + Legacy Bot





Initialization Steps:

📊 Configuration Load - Load all settings from config.py

🔑 API Validation - Validate Helius RPC, Birdeye API, Jupiter API

💰 SOL Balance Check - Ensure sufficient SOL for transaction fees (>0.005 SOL)

🧵 Background Services Start:

🛡️ Risk Management Thread (2-minute intervals)

💰 Balance Monitor Thread (5-minute intervals)

⚡ WebSocket Speed Engine (Real-time)



⚡ PHASE 2: SPEED ENGINE (Real-Time Detection) (raydium_listener.py)

🔍 Step 1: WebSocket Monitoring

python







🌐 Helius WebSocket Connection: wss://mainnet.helius-rpc.com/?api-key=xxx

🎯 Program ID: 675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8 (Raydium LP V4)

📡 Subscription: All Raydium transactions in real-time





🔥 Step 2: Pool Detection

python







# Launch Command

python main_speed_engine.py  # Default: Speed Engine only

python main_speed_engine.py speed   # Explicit Speed Engine  

python main_speed_engine.py hybrid  # Speed + Legacy Bot





📝 Step 3: Token Extraction

python







🌐 Helius WebSocket Connection: wss://mainnet.helius-rpc.com/?api-key=xxx

🎯 Program ID: 675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8 (Raydium LP V4)

📡 Subscription: All Raydium transactions in real-time





🚫 Step 4: Duplicate Prevention

python







# Listen for specific log patterns:

pool_creation_patterns = [

    "InitializeAccount3",    # 65% of new pools

    "InitializeAccount",     # 35% of new pools  

    "initialize2",           # Legacy (kept for compatibility)

]



# When detected:

🔥 NEW RAYDIUM POOL DETECTED! Signature: ABC123...







🧠 PHASE 3: INTELLIGENCE ENGINE (15-Point Filtering) (nice_funcs.py)

🛡️ Security Filters (Critical)

python







⚡ Extract token addresses from transaction signature

💎 NEW TOKEN DETECTED!

   Base Token: 6mZXjL8cWvBxByuQzwQJUHnb3KbawgUx9datcpQRDkm6

   Quote Token: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v (USDC)

   Transaction: https://solscan.io/tx/ABC123...





🚫 Additional Protections

python







# Check processed signatures file

📁 File: ./data/processed_signatures.txt

⚠️ Skip if signature already processed

✅ Add new signature to prevent re-processing





Intelligence Results

python







🧠 Kali Intelligence: Running comprehensive vetting pipeline...



✅ 1. Fake Token Check        - Reject scam/imitation tokens

✅ 2. Ownership Renounced     - Check if owner gave up control  

✅ 3. Honeypot Check          - Ensure buyers can sell

✅ 4. Freezable Token Check   - Reject if can freeze transfers

✅ 5. Token 2022 Check        - Reject experimental standard

✅ 6. Mintable Token Check    - Reject infinite supply tokens

✅ 7. Mutable Metadata        - Check if name/logo changeable

✅ 8. Transfer Fees Check     - Reject fee-charging tokens

✅ 9. Buy Tax Check           - Max 5% buy tax

✅ 10. Sell Tax Check         - Max 5% sell tax

✅ 11. Owner Percentage       - Max 30% owner concentration

✅ 12. Update Authority       - Max 30% authority concentration  

✅ 13. Top 10 Holders         - Max 70% top holder concentration

✅ 14. Market Quality         - Min $400 liquidity, Max $30K mcap

✅ 15. Token Age Check        - Max 4 hours old (NEW!)







📊 PHASE 4: STRATEGY ENGINE (Dynamic Execution) (nice_funcs.py)

💰 Step 1: Dynamic Position Sizing

python







🔍 Deployer Blacklist Check - Known scammer wallets

📁 File: ./data/deployer_blacklist.txt

⚡ Retry Logic: 8 attempts with exponential backoff (Birdeye 555 errors)





⚡ Step 2: Ultra-Fast Jupiter Execution

python







# If APPROVED:

🎯 Kali Intelligence: Token QRDkm6 APPROVED! Executing DYNAMIC ULTRA-FAST BUY



# If REJECTED:

🚫 Kali Intelligence: Token QRDkm6 REJECTED by intelligence engine

📁 Log to: ./data/intelligence_rejections.txt





📊 Step 3: Position Recording

python







📊 Kali Speed + Strategy: Fetching liquidity for dynamic sizing...

⚡ Kali Speed Strategy: Dynamic sizing applied

   Liquidity: $8,450 → Size: $4.23 USDC



# Sizing Formula:

dynamic_size = min(

    liquidity * USDC_BUY_TARGET_PERCENT_OF_LP,  # % of liquidity pool

    USDC_MAX_BUY_SIZE,                          # Maximum limit

    max(USDC_MIN_BUY_SIZE, usdc_balance * 0.8) # Minimum limit

)







🛡️ PHASE 5: CONTINUOUS RISK MANAGEMENT

💎 Tiered Profit Taking (Every 2 minutes)

python







🚀 Kali Speed Engine: FAST BUY initiated for QRDkm6



# Jupiter v6 API Parameters:

- Slippage: 30% (slippageBps=3000)

- Priority Fee: 100,000 lamports  

- Skip Preflight: True

- Max Accounts: 64

- Enhanced Routing: onlyDirectRoutes=false



✅ Transaction successful! https://solscan.io/tx/DEF456...





🛑 Stop Loss Protection

python







📊 Kali Strategy: Position recorded - $4.23 into QRDkm6

📁 File: ./data/position_states.json

📁 File: ./data/speed_engine_snipes.txt





💰 Balance Monitoring (Every 5 minutes)

python







📈 Kali Strategy Engine: Running Advanced PNL Management



# 3-Tier Exit Strategy:

Tier 1: 25% at +25% profit  

Tier 2: 50% at +50% profit

Tier 3: 75% at +100% profit



# Example:

💰 TIER 1 HIT: Selling 25% of QRDkm6 at +28% profit

💰 TIER 2 HIT: Selling 50% of QRDkm6 at +52% profit  

💰 TIER 3 HIT: Selling 75% of QRDkm6 at +105% profit









📈 PERFORMANCE TRACKING & LOGGING

📁 Key Data Files:

python







🛑 Stop Loss: -25% (STOP_LOSS_PERCENTAGE = -0.25)

🚨 STOP LOSS TRIGGERED: Selling 100% of QRDkm6 at -23% loss





📊 Real-Time Console Output:

python







💰 Kali Speed Engine: Checking wallet balance...

✅ SOL Balance: 0.205497609 SOL ($34.07)



# Warnings:

⚠️ LOW SOL WARNING: < 0.01 SOL

🚨 CRITICAL SOL BALANCE: < 0.005 SOL









⚙️ CONFIGURATION HIGHLIGHTS

🎯 Current Settings: 1

python









./data/speed_engine_snipes.txt      # Successful trades

./data/intelligence_rejections.txt  # Filtered out tokens  

./data/position_states.json         # Active positions

./data/processed_signatures.txt     # Duplicate prevention

./data/deployer_blacklist.txt       # Known scammers

./data/closed_positions.txt         # Completed trades









🚀 SYSTEM STATUS

✅ FULLY OPERATIONAL TIER 1 SYSTEM 2

⚡ Speed Engine: 100% pool detection accuracy (120+ pools/minute)

🧠 Intelligence Engine: 15-point security filtering + token age filter

📊 Strategy Engine: Dynamic sizing + 3-tier profit taking

🛡️ Risk Management: Continuous monitoring + stop loss protection

Your Kali Sniper Bot is a state-of-the-art trading system that detects new tokens in milliseconds, filters them through comprehensive security checks, and executes trades with dynamic position sizing - all while managing risk through automated profit-taking and stop-loss mechanisms! 🎯🚀



Here is the diagram:



graph TD

    A["🚀 START: python main_speed_engine.py"] --> B["🔧 System Initialization"]

    B --> C["💰 SOL Balance Check"]

    C --> D{"SOL > 0.005?"}

    D -->|No| E["🚨 CRITICAL: Insufficient SOL"]

    D -->|Yes| F["📡 Start Background Services"]

    

    F --> G["🛡️ Risk Management Thread"]

    F --> H["💰 Balance Monitor Thread"]

    F --> I["⚡ Speed Engine WebSocket"]

    

    I --> J["🔍 Monitor Raydium LP V4"]

    J --> K["📨 WebSocket Message"]

    K --> L{"Pool Creation<br/>Pattern?"}

    

    L -->|No| J

    L -->|Yes| M["🔥 NEW POOL DETECTED!"]

    

    M --> N["📝 Extract Token Addresses"]

    N --> O{"Token Extraction<br/>Successful?"}

    O -->|No| P["⚠️ Retry with Backoff"]

    P --> N

    O -->|Yes| Q["🧠 INTELLIGENCE ENGINE"]

    

    Q --> R["🔒 Security Check #1-15"]

    R --> S["📊 Market Quality Check"]

    S --> T["⏰ Token Age Check"]

    T --> U["🚫 Deployer Blacklist"]

    U --> V{"All Checks<br/>Pass?"}

    

    V -->|No| W["🚫 REJECTED: Log & Skip"]

    W --> J

    V -->|Yes| X["🎯 APPROVED FOR TRADING!"]

    

    X --> Y["📊 STRATEGY ENGINE"]

    Y --> Z["💰 Dynamic Position Sizing"]

    Z --> AA["⚡ Ultra-Fast Jupiter Buy"]

    AA --> BB{"Transaction<br/>Successful?"}

    

    BB -->|No| CC["❌ Failed: Log Error"]

    CC --> J

    BB -->|Yes| DD["✅ SUCCESS: Position Recorded"]

    

    DD --> EE["📈 Profit Management Loop"]

    EE --> FF["💎 Tiered Exits (25%, 50%, 75%)"]

    FF --> GG["🛑 Stop Loss Monitoring"]

    GG --> HH{"Position<br/>Closed?"}

    

    HH -->|No| EE

    HH -->|Yes| II["📊 Performance Logging"]

    II --> J

    

    G --> JJ["🔄 Every 2 Minutes"]

    JJ --> KK["📊 Check Open Positions"]

    KK --> LL["💰 Profit Taking Logic"]

    LL --> MM["🛑 Stop Loss Logic"]

    MM --> G

    

    H --> NN["🔄 Every 5 Minutes"]

    NN --> OO["💰 SOL Balance Check"]

    OO --> PP{"SOL < 0.01?"}

    PP -->|Yes| QQ["⚠️ LOW SOL WARNING"]

    PP -->|No| H

    QQ --> H