# 📊 KALI SNIPER BOT - PNL TRACKING & EXIT STRATEGY DOCUMENTATION

## 🎯 Overview
The Kali Sniper Bot implements a sophisticated PnL (Profit and Loss) tracking system with automated exit strategies. The bot continuously monitors all open positions and executes trades based on predefined profit targets and stop-loss levels.

## 🔄 How PnL Tracking Works

### 1. **Position Entry & Initial Tracking**
When the bot buys a token:
- Records the initial investment amount (e.g., $5 USDC)
- Stores position state in `./data/open_positions_state.json`
- Tracks entry time, token address, and purchase details

### 2. **Continuous Monitoring**
The bot runs a background thread (`run_risk_management()`) that:
- Checks positions every **2 minutes**
- Fetches current wallet holdings using Birdeye API
- Calculates real-time USD value of each position
- Compares current value against profit/loss thresholds

### 3. **Position State Management**
Each position is tracked with:
```json
{
  "token_address": {
    "initial_investment_usdc": 5.0,
    "entry_time": "2024-01-01T10:00:00",
    "tiers_sold": [],  // Tracks which profit tiers have been executed
    "total_usdc_extracted": 0
  }
}
```

## 📈 Exit Strategy System

The bot uses a **TIERED EXIT STRATEGY** with multiple profit targets:

### **Tier System Configuration**
```python
# Stop Loss
STOP_LOSS_PERCENTAGE = -0.25  # Exit at -25% loss

# Profit Tiers
Tier 1: 2x (100% profit) → Sell 50% of position
Tier 2: 5x (400% profit) → Sell 50% of remaining
Tier 3: 11x (1000% profit) → Sell 75% of remaining
```

### **How Exit Works:**

#### 🛑 **Stop-Loss Execution** (Priority 1)
- If position drops below -25% (e.g., $5 → $3.75)
- **Action**: Immediately sell 100% of position
- **Function**: `kill_switch(token_address)`
- Removes position from tracking

#### 💰 **Profit-Taking Execution** (Priority 2)

**Example with $5 initial investment:**

1. **Token reaches 2x ($10 value)**
   - Bot sells 50% of tokens
   - Recovers ~$5 USDC
   - Keeps 50% for further gains
   - Marks Tier 1 as executed

2. **Token reaches 5x ($25 value on remaining)**
   - Bot sells 50% of remaining tokens
   - Recovers ~$12.5 USDC
   - Keeps 25% of original position
   - Marks Tier 2 as executed

3. **Token reaches 11x ($55+ value on remaining)**
   - Bot sells 75% of remaining tokens
   - Takes massive profits
   - Closes entire position
   - Removes from tracking

## 🔧 Technical Implementation

### **Key Functions:**

1. **`advanced_pnl_management()`** (nice_funcs.py:875)
   - Main PnL monitoring function
   - Runs every 2 minutes
   - Checks all positions against thresholds
   - Executes sells when targets hit

2. **`execute_tiered_sell()`** (nice_funcs.py:815)
   - Handles partial position sells
   - Calculates exact token amounts
   - Executes market sells via Jupiter

3. **`market_sell()`** / `kill_switch()`**
   - Performs actual token sales
   - Uses Jupiter aggregator for best prices
   - Handles slippage and transaction confirmation

### **Monitoring Flow:**
```
Every 2 minutes:
  ↓
Fetch wallet holdings
  ↓
For each position:
  ↓
Check stop-loss → If triggered → Sell 100%
  ↓
Check profit tiers → If reached → Sell portion
  ↓
Update position state
  ↓
Continue monitoring
```

## 📊 Real-Time Feedback

The bot provides continuous updates:
```
🛡️ Kali Speed + Strategy Engine: Running advanced risk management...
🔍 Kali Strategy: Analyzing 9mwuFd (24.50)
🎯 Kali Strategy: First Major Profit HIT for 9mwuFd!
   Value: 10.25 > Target: 10.00
   Profit: 5.25 (+105.0%)
💰 Kali Strategy: Executing First Major Profit (Tier 1)
   Selling 50% of current position
✅ Kali Strategy: First Major Profit executed successfully!
   Estimated USDC received: $5.12
```

## ⚙️ Configuration

All PnL settings are in `config.py`:
- `STOP_LOSS_PERCENTAGE`: Stop-loss threshold
- `SELL_TIERS`: Profit-taking tiers
- `ENABLE_TIERED_EXITS`: Enable/disable tiered system
- Check interval: 120 seconds (hardcoded in main_speed_engine.py)

## 🔄 Sequential Mode Integration

With `ENABLE_SEQUENTIAL_MODE = True`:
- Bot only trades one position at a time
- Waits for position to exit (profit/loss) before new trades
- Prevents overexposure to market risk

## 📝 Summary

The Kali Sniper Bot's PnL system:
1. **Tracks** every position from entry to exit
2. **Monitors** values every 2 minutes
3. **Protects** capital with -25% stop-loss
4. **Maximizes** gains with 3-tier profit system
5. **Executes** automatically without manual intervention
6. **Reports** all actions in real-time

This creates a fully automated trading system that:
- Limits losses to maximum -25%
- Captures profits at multiple levels
- Allows positions to run for massive gains
- Operates 24/7 without supervision