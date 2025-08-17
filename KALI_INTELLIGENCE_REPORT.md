## Kali Sniper Bot – Intelligence and Security Report

### Overview
Kali Sniper combines multi-source, real-time pool detection with layered intelligence and security vetting, targeting high-momentum meme coins and exiting quickly at 50% profit. It integrates:
- **Multi-source listeners**: Raydium, Pump.fun, and Virtuals (running concurrently)
- **Freshness and pump gates**: Fast 1–5 minute OHLCV heuristics
- **Birdeye-based security checks** and market quality constraints
- **Token age backstops** with RPC fallback
- **Position governance**: Max concurrent positions, re-entry guards, and tiered exits (50% profit full exit)

---

### How the bot operates
- **Detection (Speed Engine – multi-source)**
  - `raydium_listener.py`: Subscribes to Raydium LP V4 logs, extracts new token mints.
  - `pump_fun_listener.py`: Subscribes to Pump.fun program logs; processes token creation signatures.
  - `virtuals_listener.py`: Subscribes to Virtuals logs; processes new agent token creations.
  - All listeners feed a unified fast path: `trigger_fast_snipe(token_mint, signature)`.

- **Pre-trade gates (fast, low-latency)**
  - **Global position cap**: Skips if active positions ≥ `MAX_POSITIONS`.
  - **Do-not-trade / closed guard**: Skips tokens present in `DO_NOT_TRADE_LIST` or `closed_positions.txt`.
  - **Quick pump gate (5-minute momentum + quality)**
    - See Pump Filter section below; rejects before heavy vetting if weak.
  - **Name blocklist**: Rejects tokens matching `NAME_BLOCKLIST_KEYWORDS`.

- **Intelligence vetting (Birdeye + heuristics)**
  - Runs `nice_funcs.pre_trade_token_vetting(...)` for comprehensive validation; see Security and Market Quality sections below.

- **Execution (Speed Engine)**
  - Fixed-size snipe (e.g., `$USDC_SIZE`) with Jupiter v6, versioned transactions, dynamic compute/prioritization.
  - Records a new position and logs snipe event to `./data/speed_engine_snipes.txt`.

- **Position management (Strategy Engine / Tracker)**
  - `position_tracker_v2.py` monitors price and balance, manages exits:
    - Profit Tier 1 at `1.5x` → **full exit (100%)** using `kill_switch`.
    - Stop-loss at `-10%` → full exit.
  - After full exits or stop-loss, token is appended to `closed_positions.txt` to prevent re-entry.

---

### Freshness Filter (1-minute OHLCV + pressure) – fast anti-old guard
- Config (in `config.py`)
  - `ENABLE_FRESHNESS_FILTER = True`
  - `FRESH_MAX_1M_CANDLES = 10` (reject if >10 candles when first seen)
  - `FRESH_INITIAL_WINDOW_MIN = 20` (lookback window for count)
  - `FRESH_ENABLE_MOMENTUM_CHECK = True`
  - `FRESH_MIN_VOLUME_USD_FIRST5 = 5000` (sum of first up-to-5 1m candles)
  - `FRESH_CATASTROPHIC_DUMP_RATIO = 0.2` (reject if candle2 low < 20% of candle1 high)
  - `FRESH_ENABLE_PRESSURE_CHECK = True`
  - `FRESH_MIN_BUY_SELL_RATIO = 2.0` (uses Birdeye `buy1h/sell1h` proxy)

- Purpose
  - Rejects stale launches, early rug patterns, and low-pressure debuts within milliseconds.

---

### Pump Filter (5-minute momentum gate) – target strong pumps
- Config (in `config.py`)
  - `ENABLE_PUMP_FILTER = True`
  - `PUMP_MIN_VOL_5M_USD = 8000` (total last five 1m candles)
  - `PUMP_MIN_GREEN_CANDLES_5M = 3`
  - `PUMP_MIN_PRICE_CHANGE_5M_PCT = 0.10` (≥ +10%)
  - `PUMP_MIN_LIQUIDITY = 5000`
  - `PUMP_MIN_MARKET_CAP = 2000`
  - `PUMP_MAX_TOP10_HOLDER_PERCENT = 0.70`

- Logic (in `passes_pump_momentum_filter`)
  - Reject if liquidity or market cap is below minimums.
  - Reject if `top10HolderPercent` > 70% (concentrated supply risk).
  - Require 5m OHLCV strength: min total volume, ≥3 green candles, and ≥10% price lift.

- Purpose
  - Prefer tokens that are already exhibiting healthy 5m momentum with quality market stats.

---

### Security filters (Birdeye Security API)
Critical (auto-reject if True):
- **Fake token** (`fakeToken = True`)
- **Honeypot** (`honeypot = True`)
- **Freezable token** (`freezable = True` or `freezeAuthority` exists)
- **Token 2022** (`isToken2022 = True`) – experimental standard

High Risk:
- **Mintable** (`mintable = True`)
- **Mutable metadata** (`mutableMetadata = True`) – reject if `REJECT_MUTABLE_METADATA = True`, else warn
- **Transfer fees** (`transferFees = True`)
- **Buy tax > `MAX_BUY_TAX`**
- **Sell tax > `MAX_SELL_TAX`**
- **Owner percentage > `MAX_OWNER_PERCENTAGE`**
- **Update authority percentage > `MAX_UPDATE_AUTHORITY_PERCENTAGE`**
- **Top 10 holders > `MAX_TOP10_HOLDER_PERCENT`**

Medium:
- **Mutable info** (`mutableInfo = True`) – reject if `ALLOW_MUTABLE_INFO = False`, else warn

---

### Market quality filters (Birdeye Overview API)
- **Liquidity ≥ `MIN_LIQUIDITY`** (e.g., 400+ USD)
- **Market cap ≤ `MAX_MARKET_CAP`** (e.g., ≤ 30K)
- **Token age**
  - If creation time provided: reject if age > `MAX_TOKEN_AGE_HOURS` (1 hour by default)
  - Else fallback: compute via `token_overview`/RPC oldest signature; reject if > cap
  - Heuristic backstop: very high liquidity/MC with missing age → reject as likely old

- **Name blocklist**: `NAME_BLOCKLIST_KEYWORDS`

---

### Pre-buy guardrails (applied across all listeners)
- **Global position cap**: If `get_active_position_count() ≥ MAX_POSITIONS`, skip.
- **Sequential mode (optional)**: If enabled, skip when any position open (override for single-position mode).
- **Re-entry guard**: Skip mints in `DO_NOT_TRADE_LIST` or `closed_positions.txt`.

---

### Exits and risk management
- **Profit target**: First tier at `1.5x` (50%) – configured as **100% sell** → full exit.
- **Stop-loss**: Tight `-10%` – full exit on trigger.
- **State tracking**: `./data/open_positions_state.json` for tiers and P&L; summary available via Strategy Engine helpers.
- **Blacklist-on-failure**: Certain sell failures add the mint to `PERMANENT_BLACKLIST` and `closed_positions.txt`.

---

### Config essentials
- Keys and RPC: `dontshare.py`
- Strategy and intelligence settings: `config.py`
- Entry point (multi-source): `python main_speed_engine.py multi`
- Position tracker (run in parallel): `python position_tracker_v2.py`

---

### File map
- Detection: `raydium_listener.py`, `pump_fun_listener.py`, `virtuals_listener.py`
- Vetting/trading/utilities: `nice_funcs.py`
- Strategy/positions: `position_tracker_v2.py`
- Orchestration: `main_speed_engine.py`
- Configuration: `config.py`, secrets: `dontshare.py`
- Maintenance: `sol_refund.py`

---

### Tuning tips
- Tighten momentum: raise `PUMP_MIN_VOL_5M_USD` (e.g., 10–20K), `PUMP_MIN_PRICE_CHANGE_5M_PCT` (e.g., 15%).
- Tighten freshness: raise `FRESH_MIN_VOLUME_USD_FIRST5`, `FRESH_MIN_BUY_SELL_RATIO`.
- Adjust risk: lower `MAX_TOP10_HOLDER_PERCENT` (e.g., 0.5) for stricter holder distribution.
- Concurrency: set `ENABLE_SEQUENTIAL_MODE = False` and rely on `MAX_POSITIONS`.
