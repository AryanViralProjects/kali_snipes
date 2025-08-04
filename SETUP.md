# Kali Solana Trading Bot Setup Guide

## Prerequisites
- Python 3.9 or higher
- pip package manager
- Active internet connection

## Installation

### 1. Clone or Download the Bot
```bash
git clone your-repo-url
cd solana-sniper-2025-main
```

### 2. Create Virtual Environment (Recommended)
```bash
# Using conda
conda create -n trading python=3.11
conda activate trading

# OR using venv
python -m venv trading
source trading/bin/activate  # Linux/Mac
# OR
trading\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# OR install minimal requirements
pip install -r requirements-minimal.txt
```

### 4. Configure API Keys
1. Copy `dontshare.example.py` to `dontshare.py`
2. Update the following in `dontshare.py`:
   - `key` = Your Solana private key
   - `birdeye` = Your Birdeye API key
   - `rpc_url` = Your Helius RPC URL

### 5. Update Wallet Address
Update `MY_SOLANA_ADDERESS` in `config.py` with your wallet's public address.

### 6. Fund Your Wallet
- Add SOL for transaction fees (~0.1 SOL minimum)
- Add USDC for trading (amount depends on your USDC_SIZE setting)

### 7. Run the Bot
```bash
python main.py
```

## VPS Deployment

For 24/7 operation, deploy on a VPS:

```bash
# Install screen for persistent sessions
sudo apt install screen

# Start bot in screen session
screen -S kali-bot
python main.py

# Detach from screen (Ctrl+A, then D)
# Reconnect later with: screen -r kali-bot
```

## Configuration

Key settings in `config.py`:
- `USDC_SIZE` = Amount to spend per trade
- `SELL_AT_MULTIPLE` = Profit target multiplier
- `STOP_LOSS_PERCENTAGE` = Loss threshold
- `MAX_POSITIONS` = Maximum concurrent positions

## Troubleshooting

1. **Import errors**: Ensure all packages installed with `pip install -r requirements.txt`
2. **API errors**: Check your API keys in `dontshare.py`
3. **Balance errors**: Ensure wallet has SOL and USDC
4. **Permission errors**: Check file permissions for CSV files in `data/` folder

## Security
- Never share your `dontshare.py` file
- Keep private keys secure
- Use environment variables for production deployments