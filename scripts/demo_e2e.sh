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
  echo "[uhakiki] cluster: DevNet"
else
  echo "[uhakiki] starting local validator with the Uhakiki program…"
  solana-test-validator --reset \
    --bpf-program FEvabxdQJsdDaQuHi9fzWH7MvUygpMUS7DWUtmQkGVtd target/deploy/uhakiki.so \
    > /tmp/uhakiki-validator.log 2>&1 &
  VALIDATOR_PID=$!
  trap 'kill $VALIDATOR_PID 2>/dev/null || true' EXIT
  sleep 6
  echo "[uhakiki] validator up (pid $VALIDATOR_PID)"
  solana airdrop 5 --url localhost >/dev/null 2>&1 || true
fi

# attester key: on localnet, generate a fresh funded one
if [ "$MODE" = "localnet" ]; then
  ATTESTER_JSON=$(mktemp /tmp/uhakiki-attester-XXXX.json)
  solana-keygen new -o "$ATTESTER_JSON" --force --no-passphrase >/dev/null
  solana airdrop 10 --url localhost -k "$ATTESTER_JSON" >/dev/null 2>&1 || \
  for i in 1 2 3; do solana airdrop 5 --url localhost -k "$ATTESTER_JSON" >/dev/null 2>&1 && break; sleep 2; done
  export UHAKIKI_ATTESTER_KEY="$ATTESTER_JSON"
fi
echo "[uhakiki] attester: $(solana address -k "$UHAKIKI_ATTESTER_KEY" 2>/dev/null || echo '?')"

cd engine
.venv/bin/python - << 'PYEOF'
import os, sys
sys.path.insert(0, "."); sys.path.insert(0, "..")
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
    try:
        a = attest(r)
        print("ATTESTED onchain:", a["signature"][:28], "…")
        print("explorer:", a["explorer_url"])
    except Exception as exc:
        print("ATTEST FAILED:", str(exc)[:200])
PYEOF
