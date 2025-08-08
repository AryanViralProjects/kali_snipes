# 🎯 Kali Sniper Bot - Tier 1 Solana Trading System

**Revolutionary millisecond-latency Solana trading bot with real-time WebSocket detection and comprehensive intelligence filtering.**

## 🚀 Features

### ⚡ **Speed Engine** - Real-Time Detection
- **WebSocket Integration**: Helius RPC for millisecond-level pool detection
- **100% Accuracy**: Fixed pool detection patterns (InitializeAccount3/InitializeAccount)
- **Duplicate Prevention**: Signature tracking to prevent reprocessing
- **Retry Logic**: Exponential backoff for unconfirmed transactions

### 🧠 **Intelligence Engine** - 15-Point Security Filtering
- **Critical Security Checks**: Fake tokens, honeypots, freezable tokens
- **Risk Assessment**: Buy/sell taxes, owner concentration, holder distribution
- **Token Age Filter**: Only trade tokens created within 4 hours (prevents old token trading)
- **Deployer Blacklist**: Automatic scammer detection and prevention
- **Market Quality**: Liquidity and market cap validation

### 📊 **Strategy Engine** - Dynamic Execution & Management
- **Dynamic Position Sizing**: Liquidity-based trade sizing
- **Ultra-Fast Jupiter v6**: Optimized slippage and routing
- **Tiered Profit Taking**: 3-tier exit strategy (25%, 50%, 75%)
- **Advanced Stop Loss**: Configurable risk management
- **Real-Time Monitoring**: Continuous PnL tracking

## 📋 Requirements

### **APIs Required:**
- **Helius RPC**: WebSocket and HTTP endpoints
- **Birdeye API**: Security and market data (upgraded subscription recommended)
- **Jupiter v6**: Swap execution

### **Dependencies:**
```bash
pip install -r requirements.txt
```

## ⚙️ Installation & Setup

1. **Clone Repository:**
```bash
git clone https://github.com/AryanViralProjects/kali_snipes.git
cd kali_snipes
```

2. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure API Keys:**
   - Copy `dontshare.example.py` to `dontshare.py`
   - Add your API keys and wallet private key

4. **Configure Settings:**
   - Edit `config.py` for trading parameters
   - Set your Solana wallet address in `MY_SOLANA_ADDERESS`

## 🚀 Usage

### **Primary Launch (Recommended):**
```bash
python main_speed_engine.py
```

### **Speed Engine Only:**
```bash
python main_speed_engine.py speed
```

### **Hybrid Mode (Speed + Legacy):**
```bash
python main_speed_engine.py hybrid
```

## 📊 Configuration

### **Key Settings in `config.py`:**
```python
# Trading Parameters
USDC_SIZE = 5                    # Base trade size
SELL_AT_MULTIPLE = 1.5          # 50% profit target
STOP_LOSS_PERCENTAGE = -0.25    # 25% stop loss
PRIORITY_FEE = 20000            # Transaction priority

# Intelligence Filters
MAX_TOKEN_AGE_HOURS = 4.0       # Only trade tokens < 4 hours old
MIN_LIQUIDITY = 400             # Minimum $400 liquidity
MAX_MARKET_CAP = 30000          # Maximum $30K market cap
MAX_BUY_TAX = 0.05             # Maximum 5% buy tax
MAX_SELL_TAX = 0.05            # Maximum 5% sell tax

# Speed Engine
SPEED_ENGINE_SLIPPAGE = 3000    # 30% slippage tolerance
```

## 🛡️ Security Features

### **15-Point Intelligence Filter:**
1. **Fake Token Detection** - Rejects scam/imitation tokens
2. **Ownership Renouncement** - Checks if owner gave up control
3. **Honeypot Detection** - Ensures buyers can sell
4. **Freezable Token Check** - Rejects tokens that can freeze transfers
5. **Token 2022 Filter** - Rejects experimental token standard
6. **Mintable Token Check** - Rejects tokens with infinite supply
7. **Mutable Metadata Check** - Flags changeable token info
8. **Transfer Fee Detection** - Rejects fee-charging tokens
9. **Buy Tax Validation** - Maximum 5% buy tax
10. **Sell Tax Validation** - Maximum 5% sell tax
11. **Owner Concentration** - Maximum 30% owner holdings
12. **Authority Concentration** - Maximum 30% update authority
13. **Holder Distribution** - Maximum 70% top 10 holders
14. **Market Quality Check** - Liquidity and market cap limits
15. **Token Age Filter** - Only trade tokens < 4 hours old

### **Additional Protections:**
- **Deployer Blacklist**: Known scammer wallet tracking
- **Signature Deduplication**: Prevents double-processing
- **Balance Monitoring**: SOL balance warnings and protection

## 📈 Performance & Monitoring

### **Real-Time Logging:**
- Pool detection events
- Intelligence filtering results
- Trade executions and results
- PnL updates and position management

### **Data Files:**
```
data/
├── speed_engine_snipes.txt      # Successful trades
├── intelligence_rejections.txt  # Filtered tokens
├── position_states.json         # Active positions
├── processed_signatures.txt     # Duplicate prevention
├── deployer_blacklist.txt       # Known scammers
└── closed_positions.txt         # Completed trades
```

## 🔧 Architecture

### **3-Engine System:**
- **Speed Engine** (`raydium_listener.py`): Real-time WebSocket detection
- **Intelligence Engine** (`nice_funcs.py`): Security filtering and validation
- **Strategy Engine** (`nice_funcs.py`): Dynamic execution and risk management

### **Background Services:**
- **Risk Management Thread**: 2-minute PnL monitoring
- **Balance Monitor Thread**: 5-minute SOL balance checks
- **WebSocket Listener**: Real-time pool detection

## ⚠️ Risk Disclaimer

**This is experimental trading software. Use at your own risk.**

- **Test thoroughly** with small amounts first
- **Monitor actively** during operation
- **Understand the risks** of automated trading
- **Keep sufficient SOL** for transaction fees
- **Review all configuration** before running

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📧 Support

For issues and support:
- Create an issue in this repository
- Include detailed logs and configuration
- Describe the problem and expected behavior

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🎯 Kali Sniper Bot - Revolutionizing Solana Trading with Millisecond Precision** 🚀