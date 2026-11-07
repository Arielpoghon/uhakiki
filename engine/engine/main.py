"""Uhakiki API — FastAPI surface: /screen, /attest, /explain, /wallet-screen, /health.

The rules engine is the only decision-maker. /attest writes the verdict the
engine produced to Solana (DevNet). /explain calls the agent layer — which
only explains what the engine decided.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .evaluator import screen
from .loader import load_pack
from .schemas import InvoiceSubmission, ScreenResult

REPO_ROOT = Path(__file__).resolve().parents[2]  # uhakiki/ root
import sys as _sys

if str(REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(REPO_ROOT))  # makes agent importable
DEVNET = os.environ.get("UHAKIKI_CLUSTER", "devnet")

pack, pack_hash = load_pack()

app = FastAPI(
    title="Uhakiki",
    description="AI compliance agent for tokenized real-world assets — "
    "the rules engine decides, the agent explains, the chain proves.",
    version="0.1.0",
)


PROGRAM_ID = "FEvabxdQJsdDaQuHi9fzWH7MvUygpMUS7DWUtmQkGVtd"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(REPO_ROOT / "app" / "index.html")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "program_id": PROGRAM_ID,
        "pack_id": pack.pack_id,
        "pack_hash": pack_hash,
        "cluster": DEVNET,
    }


@app.post("/screen")
def screen_invoice(invoice: InvoiceSubmission) -> ScreenResult:
    return screen(invoice, pack, pack_hash)


@app.post("/attest")
def attest(result: ScreenResult) -> dict:
    """Write the engine's verdict to Solana via the attest client script.

    Returns {signature, attestation_pda, explorer_url}. Simulated when
    UHAKIKI_ATTEST_MODE=simulated (no key/CLI) — labeled honestly.
    """
    if os.environ.get("UHAKIKI_ATTEST_MODE", "").lower() == "simulated":
        payload = f"{result.asset_id}|{result.verdict.value}|{result.rule_pack_hash}"
        uid = hashlib.sha256(payload.encode()).hexdigest()[:32]
        return {
            "mode": "simulated",
            "signature": "sim-" + uid,
            "attestation_pda": "sim-" + uid[:16],
            "explorer_url": "",
            "note": "SIMULATED proof — deterministic hash of the attestation payload.",
        }
    return _attest_onchain(result)


def _attest_onchain(result: ScreenResult) -> dict:
    try:
        from .attest import attest

        return attest(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"attestation failed: {exc}") from exc


@app.post("/explain")
def explain(result: ScreenResult) -> dict:
    from agent.explainer import explain_result

    return explain_result(result)


@app.post("/wallet-screen")
def wallet_screen(body: dict) -> dict:
    from agent.wallet_screener import screen_wallet

    wallet = body.get("wallet", "")
    if not isinstance(wallet, str) or not (32 <= len(wallet) <= 44):
        raise HTTPException(status_code=400, detail="provide a Solana wallet pubkey (32-44 chars)")
    return screen_wallet(wallet)
