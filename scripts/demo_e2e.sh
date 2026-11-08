#!/usr/bin/env bash
# Uhakiki end-to-end: local validator + deployed program + rules engine +
# AI explanation + on-chain attestation. Proves the full flow in one command.
# Usage: ./scripts/demo_e2e.sh [localnet|devnet]   (default: localnet)
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/share/solana/agave-4.4.1/bin:$HOME/.cargo/bin:$PATH"

MODE="${1:-localnet}"
if [ "$MODE" = "devnet" ]; then
  : "${UHAKIKI_ATTESTER_KEY:?set UHAKIKI_ATTESTER_KEY (path to solana-keygen JSON) for devnet}"
  export UHAKIKI_RPC_URL="https://api.devnet.solana.com"
  echo "[uhakiki] cluster: DevNet"
else
  echo "[uhakiki] killing any stale validators…"
  pkill -f '[s]olana-test-validator' 2>/dev/null || true
  sleep 2
  echo "[uhakiki] starting local validator with the Uhakiki program…"
  solana-test-validator --reset \
    --bpf-program FEvabxdQJsdDaQuHi9fzWH7MvUygpMUS7DWUtmQkGVtd target/deploy/uhakiki.so \
    > /tmp/uhakiki-validator.log 2>&1 &
  VALIDATOR_PID=$!
  trap 'kill $VALIDATOR_PID 2>/dev/null || true' EXIT
  # wait for RPC health (up to 60s)
  for i in $(seq 1 30); do
    curl -s -m 2 http://127.0.0.1:8899 -X POST -H 'Content-Type: application/json' \
      -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' | grep -q ok && break
    sleep 2
  done
  echo "[uhakiki] validator up (pid $VALIDATOR_PID)"
  export UHAKIKI_RPC_URL="http://127.0.0.1:8899"
fi

cd engine
.venv/bin/python - << 'PYEOF'
import os, sys, json, time
sys.path.insert(0, "."); sys.path.insert(0, "..")
import httpx
RPC = os.environ["UHAKIKI_RPC_URL"]
http = httpx.Client(timeout=30)

# on localnet: fresh keypair, funded via RPC (in-process — no key files)
from solders.keypair import Keypair
if os.environ.get("UHAKIKI_ATTESTER_KEY"):
    kp = Keypair.from_bytes(bytes(json.load(open(os.environ["UHAKIKI_ATTESTER_KEY"]))))
else:
    kp = Keypair()
    for i in range(15):
        r = http.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": "requestAirdrop",
                                 "params": [str(kp.pubkey()), 10_000_000_000]}).json()
        if "result" in r:
            break
        if i == 14:
            print("[e2e] FATAL: airdrop failed:", str(r.get("error"))[:120])
            sys.exit(1)
        time.sleep(2)
bal = http.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": "getBalance",
                           "params": [str(kp.pubkey())]}).json()["result"]["value"]
print(f"[e2e] attester {kp.pubkey()} balance: {bal / 1e9} SOL")
assert bal >= 1_000_000_000, "attester unfunded"

from engine.loader import load_pack
from engine.evaluator import screen
from engine.schemas import InvoiceSubmission
from agent.explainer import explain_result
from engine.attest import attest

pack, pack_hash = load_pack()
sys.path.insert(0, "../scripts")
from demo_seed import CLEAN_INVOICE, sanctioned_buyer
clean = InvoiceSubmission(**CLEAN_INVOICE)
dirty = InvoiceSubmission(**sanctioned_buyer(CLEAN_INVOICE))

for label, inv in (("CLEAN (Mama Mboga)", clean), ("SANCTIONED buyer", dirty)):
    r = screen(inv, pack, pack_hash)
    e = explain_result(r)
    print(f"--- {label}: {r.verdict.value} ---")
    print("rules:", [t.rule_id for t in r.triggered_rules] or "none")
    print("EN:", e["explanation_en"][:90], "…")
    print("SW:", e["explanation_sw"][:90], "…")
    a = attest(r, keypair=kp)
    print("ATTESTED onchain:", a["signature"][:28], "…")
    print("explorer:", a["explorer_url"])
print("UHAKIKI END-TO-END: verdicts attested onchain")
PYEOF
