"""Replay API — serves the dashboard with the real captured run data.

The responses below are the ACTUAL outputs of a verified live run (real
validator, real on-chain attestations — tx signatures included). Used for
demo recording when the live stack cannot run on this machine.
"""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

REPO_ROOT = Path(__file__).resolve().parents[2]
CAP = json.load(open("/tmp/uhakiki-capture.json"))

app = FastAPI(title="Uhakiki replay")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(REPO_ROOT / "app" / "index.html")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "program_id": "FEvabxdQJsdDaQuHi9fzWH7MvUygpMUS7DWUtmQkGVtd",
            "pack_id": "kenya-invoices-v1", "cluster": "devnet"}


@app.post("/screen")
def screen(inv: dict) -> dict:
    # sanctioned flip → the DENY capture; otherwise ALLOW
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
