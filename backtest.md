# Backtesting Guidelines for Solana Sniper Bot

This document provides a step-by-step guide to building a backtest script for the Solana Sniper Bot. The script should simulate the bot's behavior on historical data from 2024-2025 Solana meme coin launches. Focus on replaying launches, applying the bot's filters (e.g., age, security, liquidity, momentum), simulating buys/sells based on PNL logic (tiered TP at 1.5x, SL at -10%), and computing metrics like win rate (30-50% target), average ROI, drawdowns, and total P&L.

The backtest should use Python (3.12+), libraries like `pandas`, `numpy`, `requests`, and mock the bot's functions (e.g., from `Nice_func.py`). Account for fixed $4 buys, slippage (0.5-3%), priority fees (~$0.01-0.02/tx), and small positions.

## Prerequisites
- Python environment with: `pandas`, `numpy`, `requests`, `datetime`.
- API keys: Birdeye (for OHLCV/prices), Helius (for tx/block replays).
- Historical dataset: Collect ~100-500 meme token mints from 2024-2025 (e.g., via Dune Analytics queries or CoinGecko lists). For each: launch timestamp, 1-24h OHLCV (1m/3m candles), liquidity, MC, security data.
- Bot config: Use values from `config.py` (e.g., `USDC_SIZE=4`, `SELL_AT_MULTIPLE=1.5`, `STOP_LOSS_PERCENTAGE=-0.1`, `MIN_LIQUIDITY=400`, `MAX_MARKET_CAP=30000`).

## Step 1: Data Collection Module
Create a function to fetch or load historical data for tokens.
- **Input**: List of token mint addresses (e.g., from CSV: `historical_launches.csv` with columns: `mint`, `launch_time_unix`, `birdeye_url`).
- **Output**: For each token, a Pandas DataFrame with:
  - OHLCV (open, high, low, close, volume) at 1m/3m resolution for first 24h post-launch.
  - Metadata: liquidity at launch, MC, top10 holders %, age (hours), buy/sell taxes, freeze/mint authorities.
- **How**:
  - Use Birdeye API: `/defi/ohlcv` for candles, `/defi/token_overview` for metadata, `/defi/token_security` for vetting.
  - Fallback: Helius RPC `getSignaturesForAddress` to replay launch txs and estimate age/liquidity.
  - Handle rate limits: Batch queries, sleep 1-2s between calls.
  - Store in CSVs (e.g., `./data/backtest/{token}_ohlcv.csv`) for reuse.
- **Example Code Snippet**:
  ```python
  import requests
  import pandas as pd
  from datetime import datetime

  def fetch_token_data(mint, api_key, launch_unix):
      time_from = launch_unix
      time_to = launch_unix + 86400  # 24h
      url = f"https://public-api.birdeye.so/defi/ohlcv?address={mint}&type=1m&time_from={time_from}&time_to={time_to}"
      headers = {"X-API-KEY": api_key}
      response = requests.get(url, headers=headers)
      if response.status_code == 200:
          items = response.json().get('data', {}).get('items', [])
          df = pd.DataFrame(items)[['unixTime', 'o', 'h', 'l', 'c', 'v']]
          df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
          # Add metadata fetch similarly
          return df
      return pd.DataFrame()
  ```

## Step 2: Filter Simulation
Replicate the bot's vetting logic to decide if a token would have been "sniped".
- **Functions to Mock**:
  - `pre_trade_token_vetting`: Check security (honeypot, freezable, taxes <5%, top10 <70%), liquidity (>400), MC (<30k), age (<1h).
  - `passes_pump_momentum_filter`: Min vol $2500/5m, min green candles 2/5, price change >5%.
  - `get_token_age_hours_api`: Calculate age from launch_unix.
- **Input**: Token metadata/OHLCV.
- **Output**: Boolean (pass/fail), reason (for logging).
- **Edge Cases**: Skip if data incomplete; assume launch price = first close.
- **Example**:
  ```python
  def apply_filters(df_ohlcv, metadata):
      # Age check
      age_hours = (datetime.now().timestamp() - metadata['launch_unix']) / 3600
      if age_hours > 1.0:
          return False, "Too old"
      # Liquidity/MC
      if metadata['liquidity'] < 400 or metadata['mc'] > 30000:
          return False, "Invalid liq/MC"
      # Pump check on first 5 candles
      recent = df_ohlcv.head(5)
      vol_sum = recent['volume'].sum()
      greens = (recent['close'] > recent['open']).sum()
      if vol_sum < 2500 or greens < 2:
          return False, "No momentum"
      # Security: Mock high holders/taxes
      if metadata['top10_percent'] > 0.7 or metadata['sell_tax'] > 0.05:
          return False, "Security fail"
      return True, "Passed"
  ```

## Step 3: Trade Simulation
For passing tokens, simulate buy → hold → exit.
- **Buy**: At t=0 (first candle close) + slippage (e.g., 3%).
- **Position Tracking**: Start with $4 USDC; compute token amount = buy_size / (buy_price * (1 + slippage)).
- **PNL Loop**: Iterate through OHLCV (use close for value updates).
  - Check TP: If value >= entry * 1.5, sell 100% - slippage → profit.
  - Check SL: If value <= entry * (1 - 0.1), sell - slippage → loss.
  - If no exit by end, sell at last close (or hold for metrics).
- **Fees**: Subtract $0.02 per trade (priority fee + Solana base).
- **Output per Trade**: Entry/exit prices, profit/loss, duration (hours), outcome (TP/SL/Hold).
- **Example**:
  ```python
  def simulate_pnl(df_ohlcv, buy_size=4, tp=1.5, sl=-0.1, slippage=0.03, fee=0.02):
      if df_ohlcv.empty:
          return 0, "No data"
      buy_price = df_ohlcv['close'].iloc[0] * (1 + slippage)
      tokens_bought = buy_size / buy_price
      entry_value = buy_size - fee
      
      for i in range(1, len(df_ohlcv)):
          curr_price = df_ohlcv['close'].iloc[i]
          curr_value = tokens_bought * curr_price
          if curr_value >= entry_value * tp:
              exit_value = curr_value * (1 - slippage) - fee
              return exit_value - entry_value, "TP"
          if curr_value <= entry_value * (1 + sl):
              exit_value = curr_value * (1 - slippage) - fee
              return exit_value - entry_value, "SL"
      # End of data
      final_value = tokens_bought * df_ohlcv['close'].iloc[-1] * (1 - slippage) - fee
      return final_value - entry_value, "Hold"
  ```

## Step 4: Run Backtest and Compute Metrics
- **Loop**: Over all tokens → Apply filters → If pass, simulate trade → Collect results in DF.
- **Metrics**:
  - Win Rate: (TP trades / total trades) * 100.
  - Avg ROI: Mean(profits / buy_size).
  - Total P&L: Sum(profits).
  - Max Drawdown: Max peak-to-trough % loss across portfolio.
  - Sharpe: (Avg ROI - risk_free_rate) / std(ROI), risk_free=0.02 (annual).
  - Trades: Total, Wins, Losses, Avg Hold Time.
- **Logging**: CSV output (e.g., `backtest_results.csv`), plots (ROI histogram via matplotlib).
- **Example Main Loop**:
  ```python
  results = []
  for index, row in pd.read_csv('historical_launches.csv').iterrows():
      mint = row['mint']
      df_ohlcv = fetch_token_data(mint, API_KEY, row['launch_unix'])
      metadata = {}  # Fetch/add metadata
      pass_filter, reason = apply_filters(df_ohlcv, metadata)
      if pass_filter:
          profit, outcome = simulate_pnl(df_ohlcv)
          results.append({'mint': mint, 'profit': profit, 'outcome': outcome})
  
  df = pd.DataFrame(results)
  win_rate = (df['outcome'] == 'TP').mean() * 100
  avg_roi = (df['profit'] / 4).mean() * 100  # %
  print(f"Win Rate: {win_rate}% | Avg ROI: {avg_roi}%")
  df.to_csv('backtest_results.csv', index=False)
  ```

## Step 5: Validation and Edge Cases
- **Test on Subsets**: Run on 10 tokens first; scale to 100+.
- **Assumptions**: Use close prices for simplicity; add randomness for slippage (np.random.uniform(0.005, 0.03)).
- **Drawdowns**: Track cumulative P&L over time.
- **Improvements**: Add multi-position simulation (if max_positions >1), sequential mode waits.
- **Runtime**: ~1-5 min per 100 tokens; optimize with caching.

## Output Requirements
- Script: `backtest_sniper.py` – Runnable from CLI (e.g., `python backtest_sniper.py --tokens=100`).
- Report: Generate MD/CSV summary with metrics/plots.
- Handle Errors: Skip failed fetches; log reasons.