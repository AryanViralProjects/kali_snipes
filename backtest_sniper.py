import argparse
import os
import time
from datetime import datetime
from typing import Dict, Tuple, List

import requests
import pandas as pd

# Local config and keys
import dontshare as d
from config import (
    USDC_SIZE,
    SELL_AT_MULTIPLE,
    STOP_LOSS_PERCENTAGE,
    MIN_LIQUIDITY,
    MAX_MARKET_CAP,
    ENABLE_PUMP_FILTER,
    PUMP_MIN_VOL_5M_USD,
    PUMP_MIN_GREEN_CANDLES_5M,
    PUMP_MIN_PRICE_CHANGE_5M_PCT,
    PUMP_MIN_LIQUIDITY,
    PUMP_MIN_MARKET_CAP,
    PUMP_MAX_TOP10_HOLDER_PERCENT,
)

BIRDEYE_API = getattr(d, "birdeye", None)
HEADERS = {"X-API-KEY": BIRDEYE_API} if BIRDEYE_API else {}

DATA_DIR = os.path.join("data", "backtest")
os.makedirs(DATA_DIR, exist_ok=True)


def _sleep_rate_limit(sec: float = 0.6) -> None:
    time.sleep(sec)


def fetch_ohlcv(mint: str, start_unix: int, hours: int = 24, tf: str = "1m") -> pd.DataFrame:
    end_unix = start_unix + hours * 3600
    url = (
        f"https://public-api.birdeye.so/defi/ohlcv?address={mint}&type={tf}"
        f"&time_from={start_unix}&time_to={end_unix}"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if not resp.ok:
            return pd.DataFrame()
        items = (resp.json() or {}).get("data", {}).get("items", [])
        if not items:
            return pd.DataFrame()
        df = pd.DataFrame(items)[["unixTime", "o", "h", "l", "c", "v"]]
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        return df
    except Exception:
        return pd.DataFrame()


def fetch_overview(mint: str) -> Dict:
    url = f"https://public-api.birdeye.so/defi/token_overview?address={mint}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if not resp.ok:
            return {}
        return (resp.json() or {}).get("data", {}) or {}
    except Exception:
        return {}


def fetch_security(mint: str) -> Dict:
    url = f"https://public-api.birdeye.so/defi/token_security?address={mint}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if not resp.ok:
            return {}
        return (resp.json() or {}).get("data", {}) or {}
    except Exception:
        return {}


def apply_filters(df: pd.DataFrame, meta: Dict, sec: Dict, launch_unix: int) -> Tuple[bool, str]:
    # Age check (at launch) — for backtest we assume snipe at time_from ~ 0h
    # We still verify MAX_MARKET_CAP, MIN_LIQUIDITY at/near launch
    liq = float(meta.get("liquidity", 0) or 0)
    mc = float(meta.get("mc", 0) or 0)
    top10 = float(meta.get("top10HolderPercent", 0) or 0)
    buy_tax = float(sec.get("buyTax", 0) or 0)
    sell_tax = float(sec.get("sellTax", 0) or 0)

    # Base market quality
    if liq < MIN_LIQUIDITY:
        return False, f"Low liquidity {liq} < {MIN_LIQUIDITY}"
    if MAX_MARKET_CAP and mc > MAX_MARKET_CAP:
        return False, f"High MC {mc} > {MAX_MARKET_CAP}"

    # Security style checks (simplified)
    if top10 > 0 and top10 > PUMP_MAX_TOP10_HOLDER_PERCENT:
        return False, f"Top10 {top10:.0%} > {PUMP_MAX_TOP10_HOLDER_PERCENT:.0%}"
    if buy_tax > 0.05 or sell_tax > 0.05:
        return False, "High tax"

    # Pump momentum on first 5 candles after launch
    if ENABLE_PUMP_FILTER:
        if df.empty or len(df) < 2:
            return False, "Not enough 1m candles"
        first5 = df.iloc[:5].copy()
        vol_sum = float(first5["volume"].sum())
        greens = int((first5["close"] > first5["open"]).sum())
        if vol_sum < PUMP_MIN_VOL_5M_USD:
            return False, f"5m volume {vol_sum:.0f} < {PUMP_MIN_VOL_5M_USD}"
        if greens < PUMP_MIN_GREEN_CANDLES_5M:
            return False, f"greens {greens} < {PUMP_MIN_GREEN_CANDLES_5M}"
        # Price change over the window
        try:
            start_price = float(first5["open"].iloc[0])
            end_price = float(first5["close"].iloc[-1])
            if start_price > 0:
                change = (end_price / start_price) - 1.0
                if change < PUMP_MIN_PRICE_CHANGE_5M_PCT:
                    return False, f"5m change {change:.1%} < {PUMP_MIN_PRICE_CHANGE_5M_PCT:.0%}"
        except Exception:
            return False, "price calc error"
        if liq < PUMP_MIN_LIQUIDITY or mc < PUMP_MIN_MARKET_CAP:
            return False, "pump liq/mc too low"

    return True, "Passed"


def simulate_pnl(df: pd.DataFrame, buy_size: float = None, tp_mult: float = None, sl_pct: float = None,
                 slippage: float = 0.03, fee: float = 0.02) -> Tuple[float, str, float]:
    """Simulate a single trade using closing prices.
    Returns: profit_usd, outcome (TP/SL/Hold), hold_hours
    """
    if df.empty:
        return 0.0, "NoData", 0.0
    if buy_size is None:
        buy_size = float(USDC_SIZE)
    if tp_mult is None:
        tp_mult = float(SELL_AT_MULTIPLE)
    if sl_pct is None:
        sl_pct = float(STOP_LOSS_PERCENTAGE)

    # Entry at first close + slippage
    entry_price = float(df["close"].iloc[0]) * (1 + slippage)
    tokens = buy_size / entry_price
    entry_value = buy_size - fee

    entry_ts = int(df["timestamp"].iloc[0])

    for i in range(1, len(df)):
        px = float(df["close"].iloc[i])
        val = tokens * px
        if val >= entry_value * tp_mult:
            exit_value = val * (1 - slippage) - fee
            hold_hours = (int(df["timestamp"].iloc[i]) - entry_ts) / 3600.0
            return exit_value - entry_value, "TP", hold_hours
        if val <= entry_value * (1 + sl_pct):
            exit_value = val * (1 - slippage) - fee
            hold_hours = (int(df["timestamp"].iloc[i]) - entry_ts) / 3600.0
            return exit_value - entry_value, "SL", hold_hours

    # End
    final_val = tokens * float(df["close"].iloc[-1]) * (1 - slippage) - fee
    hold_hours = (int(df["timestamp"].iloc[-1]) - entry_ts) / 3600.0
    return final_val - entry_value, "Hold", hold_hours


def run_backtest(csv_path: str, limit: int = None, hours: int = 24, tf: str = "1m", out_csv: str = "backtest_results.csv") -> pd.DataFrame:
    launches = pd.read_csv(csv_path)
    if limit is not None:
        launches = launches.head(limit)

    results: List[Dict] = []

    for idx, row in launches.iterrows():
        mint = str(row["mint"]).strip()
        launch_unix = int(row.get("launch_unix", 0))
        if not mint or launch_unix <= 0:
            continue

        # Fetch data
        df = fetch_ohlcv(mint, launch_unix, hours=hours, tf=tf)
        _sleep_rate_limit()
        ov = fetch_overview(mint)
        _sleep_rate_limit()
        sec = fetch_security(mint)
        _sleep_rate_limit()

        passed, reason = apply_filters(df, ov, sec, launch_unix)
        if not passed:
            results.append({
                "mint": mint,
                "passed": False,
                "reason": reason,
                "profit": 0.0,
                "outcome": "Reject",
                "hold_hours": 0.0,
            })
            continue

        profit, outcome, hold_hours = simulate_pnl(df)
        results.append({
            "mint": mint,
            "passed": True,
            "reason": "Passed",
            "profit": round(profit, 4),
            "outcome": outcome,
            "hold_hours": round(hold_hours, 3),
        })

    res_df = pd.DataFrame(results)
    if not res_df.empty:
        # Aggregate metrics
        traded = res_df[res_df["passed"]]
        if not traded.empty:
            win_rate = (traded["outcome"] == "TP").mean() * 100.0
            avg_roi = (traded["profit"] / float(USDC_SIZE)).mean() * 100.0
        else:
            win_rate = 0.0
            avg_roi = 0.0
        print(f"Backtest: trades={len(traded)} | win_rate={win_rate:.1f}% | avg_roi={avg_roi:.1f}%")

    out_path = os.path.join(DATA_DIR, out_csv)
    res_df.to_csv(out_path, index=False)
    print(f"Saved results to {out_path}")
    return res_df


def main():
    parser = argparse.ArgumentParser(description="Kali Sniper Backtester")
    parser.add_argument("--csv", required=True, help="Path to historical launches CSV with columns: mint,launch_unix")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tokens")
    parser.add_argument("--hours", type=int, default=24, help="Hours of OHLCV to fetch from launch")
    parser.add_argument("--tf", default="1m", help="Candle timeframe (1m/3m/5m)")
    parser.add_argument("--out", default="backtest_results.csv", help="Output CSV filename")
    args = parser.parse_args()

    if not BIRDEYE_API:
        print("[WARN] Missing Birdeye API key in dontshare.py (birdeye)")

    run_backtest(args.csv, limit=args.limit, hours=args.hours, tf=args.tf, out_csv=args.out)


if __name__ == "__main__":
    main()
