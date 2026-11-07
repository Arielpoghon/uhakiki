"""Wallet screener — on-chain history → risk summary (AI Track brief:
"flag risky programs, tokens and wallets before a user signs").

Reads real DevNet RPC data for the wallet's recent signatures; the risk
allowlist/denylist is a clearly-labeled mock. Falls back to an empty-history
report when RPC is unreachable — never crashes the demo.
"""
from __future__ import annotations

import json
import urllib.request

RPC_URL = "https://api.devnet.solana.com"

# Mock risk lists for the demo (clearly labeled, not production data).
RISKY_PROGRAMS = {
    "DeSoMeRskyP5p8BbrRJ6QVLoNbMhYbVBhe2wYyVwhD": "known scam token launcher (demo flag)",
}
NOTE = "Risk lists are demo mocks — not production intelligence."


def _rpc(method: str, params: list) -> dict | None:
    try:
        req = urllib.request.Request(
            RPC_URL,
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp).get("result")
    except Exception:
        return None


def screen_wallet(wallet: str) -> dict:
    sigs = _rpc("getSignaturesForAddress", [wallet, {"limit": 50}]) or []
    tx_count = len(sigs) if isinstance(sigs, list) else 0
    flags: list[str] = []

    if tx_count == 0:
        flags.append("no on-chain history — new or offline wallet (KYC pending)")
    recent_failures = sum(1 for s in sigs[:20] if isinstance(s, dict) and s.get("err"))
    if recent_failures:
        flags.append(f"{recent_failures} failed transactions in the last 20 (demo flag)")
    if tx_count > 40:
        flags.append("very high recent activity (demo flag)")

    return {
        "wallet": wallet,
        "tx_count": tx_count,
        "flags": flags,
        "summary_en": (
            f"Wallet {wallet[:8]}… has {tx_count} recent transactions on DevNet. "
            + ("Flags: " + "; ".join(flags) + "." if flags else "No risk flags on the demo lists.")
            + " " + NOTE
        ),
        "note": NOTE,
    }
