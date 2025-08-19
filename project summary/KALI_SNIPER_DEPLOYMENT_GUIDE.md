# 🚀 KALI SNIPER: COMPLETE DEPLOYMENT GUIDE

## 📋 PRE-DEPLOYMENT CHECKLIST

### **System Requirements:**
- ✅ Python 3.8 or higher
- ✅ Stable internet connection (low latency preferred)
- ✅ Minimum 2GB RAM available
- ✅ 500MB disk space for logs and data
- ✅ macOS, Linux, or Windows with WSL

### **Required API Keys:**
- ✅ Helius RPC URL with API key
- ✅ Birdeye API key (upgraded subscription recommended)
- ✅ Solana wallet private key (base58 or byte array format)

### **Funding Requirements:**
- ✅ SOL balance for transaction fees (minimum 0.1 SOL)
- ✅ USDC balance for trading (minimum $20 recommended)

---

## 🛠️ INSTALLATION STEPS

### **Step 1: Environment Setup**

#### **Clone and Navigate:**
```bash
cd /path/to/your/projects
git clone [your-repo-url] kali-sniper
cd kali-sniper
```

#### **Create Virtual Environment:**
```bash
# macOS/Linux
python -m venv trading
source trading/bin/activate

# Windows
python -m venv trading
trading\Scripts\activate
```

### **Step 2: Dependencies Installation**

#### **Install Required Packages:**
```bash
pip install -r requirements.txt
```

#### **Verify Installation:**
```bash
python -c "import solana, websockets, requests, termcolor; print('All dependencies installed successfully')"
```

### **Step 3: Configuration Setup**

#### **Create API Keys File:**
```bash
cp dontshare.example.py dontshare.py
```

#### **Edit API Configuration:**
```python
# Edit dontshare.py with your credentials
rpc_url = "https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_KEY"
birdeye = "YOUR_BIRDEYE_API_KEY"
sol_key = "YOUR_SOLANA_PRIVATE_KEY"
```

#### **Update Wallet Address:**
```python
# Edit config.py
MY_SOLANA_ADDERESS = "YOUR_WALLET_ADDRESS"
```

### **Step 4: Data Directory Setup**

#### **Create Required Directories:**
```bash
mkdir -p data
touch data/closed_positions.txt
touch data/deployer_blacklist.txt
echo "# Deployer wallet blacklist - one address per line" > data/deployer_blacklist.txt
```

### **Step 5: System Validation**

#### **Test API Connections:**
```bash
python -c "
import dontshare as d
import requests
print('Testing Helius RPC...')
response = requests.post(d.rpc_url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getHealth'})
print(f'Helius: {response.status_code}')

print('Testing Birdeye API...')
headers = {'X-API-KEY': d.birdeye}
response = requests.get('https://public-api.birdeye.so/defi/price?address=So11111111111111111111111111111111111111112', headers=headers)
print(f'Birdeye: {response.status_code}')
"
```

#### **Test Wallet Connection:**
```bash
python -c "
import nice_funcs as n
import config as c
sol_balance, usd_value = n.get_sol_balance(c.MY_SOLANA_ADDERESS)
print(f'Wallet SOL Balance: {sol_balance} SOL (${usd_value:.2f})')
"
```

---

## 🎮 LAUNCH PROCEDURES

### **Primary Launch Command:**
```bash
python main_speed_engine.py
```

### **Expected Startup Sequence:**
```
🚀 KALI SPEED ENGINE STARTING...
⚡ Transitioning from minutes to MILLISECONDS!
🚀 Kali Speed Engine: Connecting to Helius WebSocket...
✅ Kali Speed Engine: Connected and subscribed to Raydium logs!
🔍 Kali Speed Engine: Monitoring for new pool creations...
💰 Kali Speed Engine: Checking wallet balance...
✅ SOL Balance: X.XXXXXX SOL ($XX.XX)
📡 Kali Speed Engine: Keepalive ping sent
```

### **Alternative Launch Options:**

#### **Speed Engine Only:**
```bash
python raydium_listener.py
```

#### **Background Mode (Linux/macOS):**
```bash
nohup python main_speed_engine.py > kali.log 2>&1 &
```

#### **With Screen Session:**
```bash
screen -S kali
python main_speed_engine.py
# Ctrl+A, D to detach
# screen -r kali to reattach
```

---

## 📊 MONITORING & MAINTENANCE

### **Real-Time Monitoring Commands:**

#### **Watch System Logs:**
```bash
# Monitor successful snipes
tail -f data/speed_engine_snipes.txt

# Monitor rejected tokens  
tail -f data/intelligence_rejections.txt

# Monitor system output
tail -f kali.log  # if running in background
```

#### **Check System Status:**
```bash
# Check wallet balances
python -c "
import nice_funcs as n
import config as c
holdings = n.fetch_wallet_holdings_og(c.MY_SOLANA_ADDERESS)
if not holdings.empty:
    display = n.get_names_nosave(holdings.copy())
    print(display.head())
else:
    print('No token holdings found')
"

# Check SOL balance
python -c "
import nice_funcs as n
import config as c
sol_balance, usd_value = n.get_sol_balance(c.MY_SOLANA_ADDERESS)
print(f'SOL Balance: {sol_balance:.6f} SOL (${usd_value:.2f})')
"
```

### **Performance Monitoring:**

#### **Detection Rate Analysis:**
```bash
# Count pools detected in last hour
tail -n 1000 data/speed_engine_snipes.txt | grep "$(date '+%Y-%m-%d %H:')" | wc -l

# Count rejections in last hour  
tail -n 1000 data/intelligence_rejections.txt | grep "$(date '+%Y-%m-%d %H:')" | wc -l
```

#### **System Health Checks:**
```bash
# Check for WebSocket disconnections
grep "Connection closed" kali.log | tail -10

# Check for API errors
grep "API error" kali.log | tail -10

# Check latest successful operations
tail -5 data/speed_engine_snipes.txt
```

---

## ⚙️ CONFIGURATION OPTIMIZATION

### **Performance Tuning:**

#### **For High-Volume Markets:**
```python
# config.py adjustments
SPEED_ENGINE_SLIPPAGE = 5000        # Increase to 50% for very volatile tokens
SPEED_ENGINE_PRIORITY_FEE = 100000  # Increase for faster execution
MAX_TOKEN_AGE_HOURS = 2.0           # Tighten to 2 hours for newest tokens only
```

#### **For Conservative Trading:**
```python
# config.py adjustments  
USDC_MIN_BUY_SIZE = 2               # Lower minimum position size
USDC_MAX_BUY_SIZE = 5               # Lower maximum position size
STOP_LOSS_PERCENTAGE = -0.15        # Tighter stop-loss at -15%
MAX_MARKET_CAP = 15000              # Lower market cap limit
```

#### **For Aggressive Profit Taking:**
```python
# config.py adjustments
SELL_TIERS = [
    {'profit_multiple': 1.5, 'sell_portion': 0.3, 'name': 'Quick Profit'},
    {'profit_multiple': 3.0, 'sell_portion': 0.5, 'name': 'Major Profit'},
    {'profit_multiple': 8.0, 'sell_portion': 0.7, 'name': 'Moon Shot'}
]
```

### **Security Configuration:**

#### **Maximum Security:**
```python
# config.py adjustments
REJECT_NON_RENOUNCED_OWNERSHIP = True
REJECT_MUTABLE_METADATA = True
ALLOW_MUTABLE_INFO = False
MAX_TOP10_HOLDER_PERCENT = 0.50     # Stricter holder distribution
MIN_LIQUIDITY = 1000                # Higher liquidity requirement
```

#### **Balanced Security:**
```python
# config.py adjustments (current default)
REJECT_NON_RENOUNCED_OWNERSHIP = False
REJECT_MUTABLE_METADATA = False  
ALLOW_MUTABLE_INFO = True
MAX_TOP10_HOLDER_PERCENT = 0.70
MIN_LIQUIDITY = 400
```

---

## 🚨 TROUBLESHOOTING GUIDE

### **Common Issues & Solutions:**

#### **WebSocket Connection Issues:**
```
Problem: "Connection closed, attempting to reconnect..."
Solutions:
1. Check internet connectivity
2. Verify Helius API key validity
3. Check firewall/proxy settings
4. Restart the system if persistent
```

#### **API Authentication Errors:**
```
Problem: "API error (Code: 401/403)"
Solutions:
1. Verify API keys in dontshare.py
2. Check Birdeye subscription status
3. Ensure API keys have sufficient quotas
4. Update expired API keys
```

#### **Transaction Failures:**
```
Problem: "Transaction failed" or "0x1788/0x1789 errors"
Solutions:
1. Increase SPEED_ENGINE_SLIPPAGE in config.py
2. Ensure sufficient USDC balance
3. Check SOL balance for transaction fees
4. Verify network congestion status
```

#### **No Pool Detections:**
```
Problem: No new pools being detected
Solutions:
1. Verify WebSocket connection status
2. Check if patterns are correctly configured
3. Monitor Solana network status
4. Restart the system to refresh connections
```

#### **Intelligence Filter Issues:**
```
Problem: "Token data not ready (Code: 555)"
Solutions:
1. This is normal for very new tokens
2. System will retry automatically
3. Consider increasing INTELLIGENCE_VETTING_TIMEOUT
4. Monitor Birdeye API status
```

### **Emergency Procedures:**

#### **Stop All Trading:**
```bash
# Kill the process
pkill -f "python main_speed_engine.py"

# Or if using screen
screen -r kali
# Ctrl+C to stop
```

#### **Emergency Position Exit:**
```python
# Run emergency exit script
python -c "
import nice_funcs as n
n.close_all_positions()
print('All positions closed')
"
```

#### **Reset System State:**
```bash
# Backup current state
cp data/open_positions_state.json data/open_positions_state_backup.json

# Clear position state
echo '{}' > data/open_positions_state.json

# Clear processed signatures (if needed)
> data/processed_signatures.txt

# Restart system
python main_speed_engine.py
```

---

## 📈 OPTIMIZATION STRATEGIES

### **Performance Optimization:**

#### **Network Optimization:**
- Use a VPS close to trading infrastructure
- Ensure low-latency internet connection
- Consider multiple RPC endpoints for redundancy

#### **System Resource Optimization:**
- Run on dedicated machine/VPS
- Close unnecessary applications
- Monitor memory usage during peak trading

#### **API Optimization:**
- Upgrade to premium Birdeye subscription
- Use multiple API keys for higher rate limits
- Implement request caching where appropriate

### **Trading Strategy Optimization:**

#### **Market Analysis:**
- Monitor successful vs rejected token ratios
- Analyze most profitable holding periods
- Track deployer success rates

#### **Position Management:**
- Adjust dynamic sizing based on market conditions
- Optimize profit tier multipliers based on historical data
- Fine-tune stop-loss levels based on volatility

#### **Risk Management:**
- Diversify across multiple small positions
- Set maximum daily loss limits
- Implement time-based trading windows

---

## 🔒 SECURITY BEST PRACTICES

### **API Key Security:**
- Never commit dontshare.py to version control
- Rotate API keys regularly
- Use environment variables in production
- Monitor API key usage and limits

### **Wallet Security:**
- Use a dedicated trading wallet
- Keep private keys encrypted at rest
- Implement multi-signature for large amounts
- Regular security audits of access patterns

### **System Security:**
- Run in isolated environment
- Keep dependencies updated
- Monitor system logs for anomalies
- Implement access controls for production systems

---

## 📞 SUPPORT & MAINTENANCE

### **Regular Maintenance Tasks:**

#### **Daily:**
- Check system status and performance
- Review successful trades and rejections
- Monitor wallet balances
- Backup important data

#### **Weekly:**
- Analyze performance metrics
- Update deployer blacklist if needed
- Review and optimize configuration
- Clean up log files

#### **Monthly:**
- Update dependencies
- Rotate API keys
- Performance optimization review
- System security audit

### **Getting Help:**
- Check logs for error messages
- Review configuration settings
- Test individual components
- Monitor Solana network status
- Check API service status pages

---

*Deployment Guide v1.0*
*Last Updated: Current System State*
*Status: Production Ready*
