# Optional colored printing; fallback to plain print if unavailable
try:
    from termcolor import cprint  # type: ignore
except Exception:
    def cprint(msg, *args, **kwargs):  # noqa: N802
        print(msg)
from pprint import pprint
import time
from typing import List

from solana.rpc.api import Client
from solana.rpc.commitment import Commitment
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID as SPL_TOKEN_PROGRAM_ID
from spl.token.instructions import close_account, CloseAccountParams
from solders.hash import Hash
from solders.message import MessageV0
from solders.transaction import VersionedTransaction

import dontshare as d
from config import MY_SOLANA_ADDERESS
import requests


def create_keypair_from_key(key_data: str) -> Keypair:
    """Create a Keypair from either base58 string or comma-separated bytes."""
    try:
        if ',' in str(key_data):
            byte_values = [int(x.strip()) for x in str(key_data).split(',')]
            return Keypair.from_bytes(bytes(byte_values))
        return Keypair.from_base58_string(key_data)
    except Exception as e:
        cprint(f"❌ Error creating keypair: {e}", 'red')
        raise


def get_client() -> Client:
    # Compatible client init across solana-py versions
    try:
        return Client(d.rpc_url, commitment=Commitment("confirmed"), timeout=30)
    except TypeError:
        return Client(d.rpc_url)


def list_zero_balance_token_accounts(owner: Pubkey) -> List[dict]:
    """Return a list of parsed token account records that have zero amount and can be closed.

    Uses raw RPC call to avoid solana.publickey import differences across versions.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            str(owner),
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"},
        ],
    }
    try:
        r = requests.post(d.rpc_url, json=payload, timeout=30)
        r.raise_for_status()
        items = (r.json() or {}).get("result", {}).get("value", [])
    except Exception:
        items = []
    records = []
    for ta in items:
        try:
            # Normalize account dict
            if isinstance(ta, dict):
                acc_info = ta.get("account", {})
                parsed = acc_info.get("data", {}).get("parsed", {})
                info = parsed.get("info", {})
                pubkey_val = ta.get("pubkey")
                lamports = acc_info.get("lamports", 0)
            else:
                continue

            amount = int(str(info.get("tokenAmount", {}).get("amount", "0") or 0))
            is_native = bool(info.get("isNative", False))
            delegate = info.get("delegate")
            delegated_amount = int(str(info.get("delegatedAmount", {}).get("amount", "0") or 0))
            if amount == 0 and not is_native and (delegate is None or delegated_amount == 0):
                records.append({"pubkey": pubkey_val, "mint": info.get("mint"), "lamports": lamports})
        except Exception:
            continue
    return records


def close_accounts(owner: Pubkey, keypair: Keypair, accounts: List[dict], batch_size: int = 8) -> float:
    """Close token accounts in batches. Returns total SOL refunded estimate."""
    client = get_client()
    total_refund_sol = 0.0
    for i in range(0, len(accounts), batch_size):
        batch = accounts[i : i + batch_size]
        if not batch:
            continue
        # Build close instructions for this batch
        instructions = []
        # Ensure program id is a solders Pubkey
        try:
            token_program_id = SPL_TOKEN_PROGRAM_ID if isinstance(SPL_TOKEN_PROGRAM_ID, Pubkey) else Pubkey.from_string(str(SPL_TOKEN_PROGRAM_ID))
        except Exception:
            token_program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

        for rec in batch:
            acct_pubkey = Pubkey.from_string(rec["pubkey"]) if isinstance(rec["pubkey"], str) else rec["pubkey"]
            instructions.append(
                close_account(
                    CloseAccountParams(
                        account=acct_pubkey,
                        dest=owner,
                        owner=owner,
                        program_id=token_program_id,
                    )
                )
            )
            # Add lamports to estimated refund
            try:
                total_refund_sol += float(rec.get("lamports", 0)) / 1e9
            except Exception:
                pass
        # Build and send a versioned transaction
        try:
            # Get fresh recent blockhash
            bh_resp = client.get_latest_blockhash()
            if hasattr(bh_resp, "value"):
                bh_obj = getattr(bh_resp.value, "blockhash", None)
            else:
                bh_obj = (bh_resp or {}).get("result", {}).get("value", {}).get("blockhash")
            if isinstance(bh_obj, Hash):
                recent_hash = bh_obj
            else:
                recent_hash = Hash.from_string(str(bh_obj))
            msg = MessageV0.try_compile(payer=owner, instructions=instructions, address_lookup_table_accounts=[], recent_blockhash=recent_hash)
            vtx = VersionedTransaction(msg, [keypair])
            cprint(f"🚫 Closing {len(batch)} zero-balance token account(s)...", 'yellow')
            client.send_raw_transaction(bytes(vtx), opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"))
            time.sleep(1.0)
        except Exception as e:
            cprint(f"⚠️ Batch failed: {e}", 'yellow')
            # Try each account individually
            for rec in batch:
                try:
                    acct_pubkey = (
                        Pubkey.from_string(rec["pubkey"]) if isinstance(rec["pubkey"], str) else rec["pubkey"]
                    )
                    instr = close_account(
                        CloseAccountParams(
                            account=acct_pubkey, dest=owner, owner=owner, program_id=token_program_id
                        )
                    )
                    bh_resp2 = client.get_latest_blockhash()
                    if hasattr(bh_resp2, "value"):
                        bh_obj2 = getattr(bh_resp2.value, "blockhash", None)
                    else:
                        bh_obj2 = (bh_resp2 or {}).get("result", {}).get("value", {}).get("blockhash")
                    if isinstance(bh_obj2, Hash):
                        recent_hash2 = bh_obj2
                    else:
                        recent_hash2 = Hash.from_string(str(bh_obj2))
                    msg2 = MessageV0.try_compile(
                        payer=owner,
                        instructions=[instr],
                        address_lookup_table_accounts=[],
                        recent_blockhash=recent_hash2,
                    )
                    vtx2 = VersionedTransaction(msg2, [keypair])
                    client.send_raw_transaction(bytes(vtx2), opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"))
                    time.sleep(0.5)
                except Exception as e2:
                    cprint(f"   ❌ Failed to close {rec['pubkey']}: {e2}", 'red')
    return total_refund_sol


def main():
    cprint("Starting the Solana token account refund tool", 'cyan')
    owner_address = MY_SOLANA_ADDERESS
    keypair = create_keypair_from_key(d.sol_key)
    owner_pubkey = Pubkey.from_string(owner_address)
    if keypair.pubkey() != owner_pubkey:
        cprint("Error: Keypair pubkey and configured wallet address do not match", 'red')
        return
    cprint(f"Using RPC: {d.rpc_url}", 'cyan')
    cprint(f"Wallet: {owner_address}", 'cyan')

    accounts = list_zero_balance_token_accounts(owner_pubkey)
    cprint(f"Found {len(accounts)} zero-balance token account(s) to close", 'yellow')
    if not accounts:
        cprint("Nothing to close.", 'green')
        return

    est_refund = sum((acc.get("lamports", 0) or 0) for acc in accounts) / 1e9
    cprint(f"Estimated refund: ~{est_refund:.6f} SOL", 'cyan')
    total_refund = close_accounts(owner_pubkey, keypair, accounts)
    cprint(f"Completed. Estimated refunded: ~{total_refund:.6f} SOL", 'green')


if __name__ == "__main__":
    main()
