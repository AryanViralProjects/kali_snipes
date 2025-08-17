import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Iterable

import json
import requests
import pandas as pd


def _now_unix() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _sleep_rate_limit(sec: float = 0.3) -> None:
    time.sleep(sec)


def _load_helius_rpc_url() -> Optional[str]:
    """
    Resolve RPC URL from env or secrets files regardless of where the script is executed from.
    Priority: ENV (HELIUS_RPC_URL/SOLANA_RPC_URL/RPC_URL) → dontshare.py → dontshare_backup.py.
    """
    # ENV first
    for env_key in ("HELIUS_RPC_URL", "SOLANA_RPC_URL", "RPC_URL"):
        env_url = os.getenv(env_key)
        if env_url:
            return env_url

    # Ensure repo root is on sys.path (script is inside launches_data/)
    try:
        script_dir = os.path.dirname(__file__)
        repo_root = os.path.abspath(os.path.join(script_dir, ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
    except Exception:
        pass

    def _extract_url(module) -> Optional[str]:
        candidates = [
            "rpc_url",
            "RPC_URL",
            "rpc",
            "helius_rpc_url",
            "HELIUS_RPC_URL",
        ]
        for name in candidates:
            val = getattr(module, name, None)
            if isinstance(val, str) and val.strip():
                return val
        return None

    # dontshare.py
    try:
        import dontshare as d  # type: ignore

        url = _extract_url(d)
        if url:
            return url
    except Exception:
        pass

    # dontshare_backup.py
    try:
        import dontshare_backup as db  # type: ignore

        url = _extract_url(db)
        if url:
            return url
    except Exception:
        pass

    return None


def _rpc_call(rpc_url: str, method: str, params: list, timeout: float = 20.0) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    resp = requests.post(rpc_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    return data.get("result", {})


def _get_signatures(
    rpc_url: str,
    address: str,
    until_unix: int,
    max_to_fetch: int,
) -> List[dict]:
    results: List[dict] = []
    before_sig: Optional[str] = None
    fetched = 0
    while True:
        limit = min(1000, max_to_fetch - fetched) if max_to_fetch else 1000
        if limit <= 0:
            break
        params = [address, {"limit": limit}]
        if before_sig:
            params[1]["before"] = before_sig
        res = _rpc_call(rpc_url, "getSignaturesForAddress", params)
        if not res:
            break
        batch = res if isinstance(res, list) else []
        if not batch:
            break
        for entry in batch:
            bt = entry.get("blockTime") or 0
            if bt and bt < until_unix:
                return results
            results.append(entry)
        fetched += len(batch)
        before_sig = batch[-1].get("signature")
        if len(batch) < limit:
            break
        _sleep_rate_limit(0.15)
    return results


def _get_signatures_until(
    rpc_url: str,
    address: str,
    lower_bound_unix: int,
    max_to_fetch: int,
    start_before_sig: Optional[str] = None,
) -> Tuple[List[dict], Optional[str]]:
    """
    Stream signatures backward until blockTime < lower_bound_unix or max_to_fetch is reached.
    Returns (signatures, next_before_sig_to_continue)
    """
    results: List[dict] = []
    before_sig: Optional[str] = start_before_sig
    fetched = 0
    while True:
        limit = min(1000, max_to_fetch - fetched) if max_to_fetch else 1000
        if limit <= 0:
            break
        params = [address, {"limit": limit}]
        if before_sig:
            params[1]["before"] = before_sig
        res = _rpc_call(rpc_url, "getSignaturesForAddress", params)
        batch = res if isinstance(res, list) else []
        if not batch:
            before_sig = None
            break
        stop = False
        for entry in batch:
            bt = entry.get("blockTime") or 0
            if bt and bt < lower_bound_unix:
                stop = True
                break
            results.append(entry)
        fetched += len(batch)
        before_sig = batch[-1].get("signature")
        if stop or len(batch) < limit:
            break
        _sleep_rate_limit(0.15)
    return results, before_sig


def _extract_new_mints_from_tx(tx: dict) -> List[str]:
    # Conservative heuristic: set(post mints) − set(pre mints)
    try:
        meta = tx.get("meta") or {}
        pre = meta.get("preTokenBalances") or []
        post = meta.get("postTokenBalances") or []
        pre_mints = set([p.get("mint") for p in pre if p.get("mint")])
        post_mints = set([p.get("mint") for p in post if p.get("mint")])
        new_mints = list(post_mints.difference(pre_mints))
        # Filter out obvious LP mint addresses if any hint (length 44 typical; keep all, user can post-filter)
        return [m for m in new_mints if isinstance(m, str) and len(m) > 0]
    except Exception:
        return []


def _get_tx(rpc_url: str, signature: str) -> dict:
    params = [
        signature,
        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
    ]
    return _rpc_call(rpc_url, "getTransaction", params)


def collect_from_helius(
    since_unix: int,
    per_program_limit: int,
    programs: List[Tuple[str, str]],
) -> List[Dict]:
    """
    programs: list of (program_id, source_tag)
    """
    rpc_url = _load_helius_rpc_url()
    if not rpc_url:
        print("[WARN] Missing Helius RPC URL. Set HELIUS_RPC_URL or dontshare.rpc_url.")
        return []

    launches: List[Dict] = []
    seen_mints: set = set()

    for program_id, source in programs:
        try:
            sigs = _get_signatures(rpc_url, program_id, since_unix, per_program_limit)
        except Exception as e:
            print(f"[WARN] getSignaturesForAddress failed for {program_id}: {e}")
            continue

        for s in sigs:
            sig = s.get("signature")
            bt = int(s.get("blockTime") or 0)
            if not sig or bt <= 0:
                continue
            try:
                tx = _get_tx(rpc_url, sig)
            except Exception as e:
                # Skip on errors
                # print(f"[WARN] getTransaction failed {sig}: {e}")
                _sleep_rate_limit(0.08)
                continue
            mints = _extract_new_mints_from_tx(tx)
            for mint in mints:
                if mint in seen_mints:
                    continue
                seen_mints.add(mint)
                launches.append(
                    {
                        "mint": mint,
                        "launch_unix": bt,
                        "source": source,
                        "tx_signature": sig,
                    }
                )
            _sleep_rate_limit(0.05)

    # Sort newest → oldest, then dedupe mints (already deduped)
    launches.sort(key=lambda x: x.get("launch_unix", 0), reverse=True)
    return launches


def _month_windows(since_unix: int, now_unix: Optional[int] = None, days_per_chunk: int = 30) -> Iterable[Tuple[int, int]]:
    """
    Yield (chunk_start, chunk_end] windows going backward in time.
    """
    if now_unix is None:
        now_unix = _now_unix()
    end = now_unix
    min_start = since_unix
    chunk = days_per_chunk * 86400
    while end > min_start:
        start = max(min_start, end - chunk)
        yield (start, end)
        end = start


def collect_from_helius_chunked(
    since_unix: int,
    programs: List[Tuple[str, str]],
    per_program_total_limit: int = 1_000_000,
    days_per_chunk: int = 30,
) -> List[Dict]:
    rpc_url = _load_helius_rpc_url()
    if not rpc_url:
        print("[WARN] Missing Helius RPC URL. Set HELIUS_RPC_URL or dontshare.rpc_url.")
        return []

    all_launches: List[Dict] = []
    seen_mints: set = set()
    # Maintain a per-program continuation cursor
    program_to_before: Dict[str, Optional[str]] = {pid: None for pid, _ in programs}
    program_to_count: Dict[str, int] = {pid: 0 for pid, _ in programs}

    for chunk_start, chunk_end in _month_windows(since_unix, _now_unix(), days_per_chunk):
        for program_id, source in programs:
            if program_to_count[program_id] >= per_program_total_limit:
                continue
            try:
                remaining = per_program_total_limit - program_to_count[program_id]
                sigs, next_before = _get_signatures_until(
                    rpc_url,
                    program_id,
                    lower_bound_unix=chunk_start,
                    max_to_fetch=min(100_000, remaining),
                    start_before_sig=program_to_before[program_id],
                )
            except Exception as e:
                print(f"[WARN] Helius chunk scan failed for {program_id}: {e}")
                continue

            program_to_before[program_id] = next_before
            program_to_count[program_id] += len(sigs)

            for s in sigs:
                sig = s.get("signature")
                bt = int(s.get("blockTime") or 0)
                if not sig or bt <= 0:
                    continue
                try:
                    tx = _get_tx(rpc_url, sig)
                except Exception:
                    _sleep_rate_limit(0.08)
                    continue
                mints = _extract_new_mints_from_tx(tx)
                for mint in mints:
                    if mint in seen_mints:
                        continue
                    seen_mints.add(mint)
                    all_launches.append(
                        {
                            "mint": mint,
                            "launch_unix": bt,
                            "source": source,
                            "tx_signature": sig,
                        }
                    )
                _sleep_rate_limit(0.05)

    all_launches.sort(key=lambda x: x.get("launch_unix", 0), reverse=True)
    return all_launches


def collect_from_pumpfun_api(since_unix: int, max_items: int = 500) -> List[Dict]:
    launches: List[Dict] = []
    seen: set = set()
    base_url = "https://frontend-api.pump.fun/coins"
    limit = 100
    offset = 0
    while len(launches) < max_items:
        url = f"{base_url}?limit={limit}&offset={offset}"
        try:
            resp = requests.get(url, timeout=15)
            if not resp.ok:
                break
            items = resp.json() or []
            if not items:
                break
            for it in items:
                mint = str(it.get("mint") or "").strip()
                created_at = it.get("createdAt")
                if not mint or not created_at:
                    continue
                # createdAt often ms; normalize to seconds
                if created_at > 10_000_000_000:
                    created_at = int(created_at / 1000)
                if created_at < since_unix:
                    # Since results are in descending order, we can early stop on first older page
                    return launches
                if mint in seen:
                    continue
                seen.add(mint)
                launches.append(
                    {
                        "mint": mint,
                        "launch_unix": int(created_at),
                        "source": "pumpfun_api",
                        "tx_signature": "",
                    }
                )
                if len(launches) >= max_items:
                    return launches
            offset += limit
            _sleep_rate_limit(0.2)
        except Exception:
            break
    return launches


def collect_from_dexscreener(
    since_unix: int,
    max_items: int = 5000,
    dex_filter: Optional[str] = "raydium",
    page_sleep: float = 0.25,
) -> List[Dict]:
    """
    Attempt cursor-like pagination using the `since` parameter by walking back in time.
    We request pages and move the cursor to the minimum pairCreatedAt - 1 to get older data.
    If the API does not honor since for older pages, this will naturally stop early.
    """
    launches: List[Dict] = []
    seen: set = set()
    cursor_ms = int(_now_unix() * 1000) + 1
    base_url = "https://api.dexscreener.com/latest/dex/pairs/solana"

    while len(launches) < max_items:
        url = f"{base_url}?since={cursor_ms}&bootstrap=true"
        try:
            resp = requests.get(url, timeout=15)
            if not resp.ok:
                break
            data = resp.json() or {}
            pairs = data.get("pairs") or []
            if not pairs:
                break
            min_created_ms: Optional[int] = None
            appended = 0
            for p in pairs:
                try:
                    base = (p.get("baseToken") or {}).get("address")
                    created = p.get("pairCreatedAt") or 0
                    dex_id = p.get("dexId")
                    if not base or not created:
                        continue
                    # DexScreener uses ms timestamps
                    created_sec = int(created / 1000) if created > 10_000_000_000 else int(created)
                    if created_sec < since_unix:
                        continue
                    if dex_filter and str(dex_id).lower() != str(dex_filter).lower():
                        continue
                    if base in seen:
                        continue
                    seen.add(base)
                    launches.append(
                        {
                            "mint": base,
                            "launch_unix": int(created_sec),
                            "source": f"dexscreener_{dex_id}",
                            "tx_signature": "",
                        }
                    )
                    appended += 1
                    if len(launches) >= max_items:
                        break
                    if min_created_ms is None or created < min_created_ms:
                        min_created_ms = created
                except Exception:
                    continue
            if len(launches) >= max_items:
                break
            if min_created_ms is None:
                break
            # Move cursor back just before the oldest seen timestamp to get older pairs
            cursor_ms = min_created_ms - 1
            if cursor_ms < since_unix * 1000:
                break
            _sleep_rate_limit(page_sleep)
        except Exception:
            break

    launches.sort(key=lambda x: x.get("launch_unix", 0), reverse=True)
    return launches


def write_csv(rows: List[Dict], out_path: str) -> None:
    if not rows:
        print("[INFO] No launches collected; nothing to write.")
        return
    df = pd.DataFrame(rows)
    # Dedup by mint keeping the newest
    df = df.sort_values("launch_unix", ascending=False).drop_duplicates(subset=["mint"], keep="first")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} unique launches → {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect historical launches for Kali backtests")
    parser.add_argument(
        "--since-hours",
        type=int,
        default=24,
        help="How many hours back to collect (default: 24)",
    )
    parser.add_argument(
        "--out",
        default=os.path.join("launches_data", "historical_launches.csv"),
        help="Output CSV path (default: launches_data/historical_launches.csv)",
    )
    parser.add_argument(
        "--sources",
        default="all",
        choices=["all", "helius", "pumpfun", "dexscreener"],
        help="Which source to use (default: all)",
    )
    parser.add_argument(
        "--chunked",
        action="store_true",
        help="Use month-by-month chunked RPC scanning to improve reliability for long ranges",
    )
    parser.add_argument(
        "--chunk-size-days",
        type=int,
        default=30,
        help="Chunk size in days for chunked RPC scanning (default: 30)",
    )
    parser.add_argument(
        "--per-program-limit",
        type=int,
        default=2000,
        help="Max signatures to scan per program for Helius (default: 2000)",
    )
    parser.add_argument(
        "--pump-limit",
        type=int,
        default=500,
        help="Max Pump.fun items to fetch (default: 500)",
    )
    parser.add_argument(
        "--dex-limit",
        type=int,
        default=500,
        help="Max DexScreener pairs to keep (default: 500)",
    )
    parser.add_argument(
        "--raydium-program",
        default="675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
        help="Raydium V4 program ID (default: known mainnet address)",
    )
    parser.add_argument(
        "--pumpfun-program",
        default="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        help="Pump.fun program ID (default: known mainnet address)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    since_unix = _now_unix() - args.since_hours * 3600

    rows: List[Dict] = []

    if args.sources in ("all", "helius"):
        if args.chunked:
            helius_rows = collect_from_helius_chunked(
                since_unix=since_unix,
                programs=[
                    (args.raydium_program, "raydium_helius"),
                    (args.pumpfun_program, "pumpfun_helius"),
                ],
                per_program_total_limit=args.per_program_limit,
                days_per_chunk=args.chunk_size_days,
            )
        else:
            helius_rows = collect_from_helius(
                since_unix=since_unix,
                per_program_limit=args.per_program_limit,
                programs=[
                    (args.raydium_program, "raydium_helius"),
                    (args.pumpfun_program, "pumpfun_helius"),
                ],
            )
        print(f"[HELIUS] Collected {len(helius_rows)} rows")
        rows.extend(helius_rows)

    if args.sources in ("all", "pumpfun"):
        pump_rows = collect_from_pumpfun_api(since_unix=since_unix, max_items=args.pump_limit)
        print(f"[PUMPFUN] Collected {len(pump_rows)} rows")
        rows.extend(pump_rows)

    if args.sources in ("all", "dexscreener"):
        dex_rows = collect_from_dexscreener(
            since_unix=since_unix, max_items=args.dex_limit, dex_filter="raydium"
        )
        print(f"[DEXSCREENER] Collected {len(dex_rows)} rows")
        rows.extend(dex_rows)

    # Normalize and write
    for r in rows:
        r["mint"] = str(r.get("mint") or "").strip()
        r["launch_unix"] = int(r.get("launch_unix") or 0)
        r["source"] = str(r.get("source") or "").strip()
        r["tx_signature"] = str(r.get("tx_signature") or "").strip()

    write_csv(rows, args.out)


if __name__ == "__main__":
    main()


