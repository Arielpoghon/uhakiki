"""Hosted-demo API — serves the dashboard with the captured live-run data.

The responses are the ACTUAL outputs of a verified live run on a local
Solana validator (real on-chain attestations — the tx signatures in the
attestation box are real explorer links). This hosted instance exists
because a free-tier host cannot run solana-test-validator; the genuinely
live flow runs from the repo: ./scripts/demo_e2e.sh
"""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP = json.load(open(Path(__file__).resolve().parent / "demo_capture.json"))

app = FastAPI(title="Uhakiki hosted demo")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(REPO_ROOT / "app" / "index.html")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "program_id": "FEvabxdQJsdDaQuHi9fzWH7MvUygpMUS7DWUtmQkGVtd",
            "pack_id": "kenya-invoices-v1", "cluster": "devnet"}


@app.post("/screen")
def screen(inv: dict) -> dict:
    key = "dirty" if inv.get("buyer", {}).get("sanctions_hit") else "clean"
    return CAP[key]["screen"]


@app.post("/explain")
def explain(result: dict) -> dict:
    key = "dirty" if result["verdict"] == "DENY" else "clean"
    return CAP[key]["explain"]


@app.post("/attest")
def attest(result: dict) -> dict:
    key = "dirty" if result["verdict"] == "DENY" else "clean"
    return CAP[key]["attest"]


@app.post("/wallet-screen")
def wallet(body: dict) -> dict:
    return {"wallet": body.get("wallet", ""), "tx_count": 47,
            "flags": ["very high recent activity (demo flag)"],
            "summary_en": "Wallet has 47 recent transactions on DevNet. Flags: very high "
                          "recent activity (demo flag). Risk lists are demo mocks.",
            "note": "demo"}
