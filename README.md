# UHAKIKI — AI compliance agent for tokenized invoices on Solana

*"Uthibitisho wa kila mali" — verifiable proof for every asset.*

Uhakiki screens tokenized real-world assets — starting with **SME invoices** —
against a jurisdiction rule pack, produces **ALLOW / RESTRICT / DENY** with a
written rationale (English + Swahili), and writes the verdict to Solana as an
**on-chain attestation** with a full audit trail. Any liquidity provider can
price an invoice instantly because the compliance work is already done — and
provably on-chain.

> **The rules engine decides. The agent explains. The chain proves.**

## Demo scenario

*Mama Mboga Logistics* (Nairobi) holds a KES 500,000 invoice against a
supermarket chain. A liquidity pool wants to buy it at a discount — but first
it requires an Uhakiki attestation. Flip the demo's buyer to a sanctioned
entity and watch the verdict go ALLOW → DENY in one click, with the exact
rule that fired, explained in English and Swahili, and recorded on DevNet.

## Disclosure

An earlier prototype of this concept (Haki) was built for a different event
on Base. **Uhakiki is a complete ground-up rebuild on Solana** — new Anchor
program, new rules engine, new agent layer — written entirely during this
hackathon. Honesty is part of the story.

## Architecture

```
Dashboard (single-file HTML, no build step)
      │ REST
      ▼
FastAPI (/screen /attest /explain /wallet-screen /health)
      ├── Rules engine — deterministic, AST-whitelisted YAML packs,
      │   sha256(pack) written on-chain for reproducibility
      ├── Agent — explain-only (EN + SW), grounded in triggered rules,
      │   wallet risk summary from real DevNet history
      └── Uhakiki program (Anchor, DevNet)
          Attestation PDA: ["attestation", issuer, asset_id]
          issue_attestation (upsert) · revoke_attestation
```

**Separation of powers:** the LLM never decides a verdict. The deterministic
engine is the only decision-maker; the agent rewrites *why* in plain language
and is guardrailed against inventing reasons beyond the triggered rules.

## Quick start

```bash
# program — requires the Solana toolchain (anchor 1.2.x; see the toolchain
# note in scripts/demo_e2e.sh — anchor 1.2 pairs with Agave 4.x)
anchor build          # -> target/deploy/uhakiki.so

# end-to-end proof: local validator + engine + on-chain attestation +
# account read-back (no faucet needed on localnet)
./scripts/demo_e2e.sh            # or: ./scripts/demo_e2e.sh devnet

# engine tests (14) + API
cd engine && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q tests/
.venv/bin/uvicorn engine.main:app --port 8000     # dashboard on http://localhost:8000

# dashboard (standalone, if not served by the API)
cd app && python3 -m http.server 8080
```

**Verification status.** The rules engine ships with 14 green tests covering
every verdict branch and boundary. The on-chain program is verified
end-to-end against a live validator: attestations for both demo scenarios
are recorded on-chain and the attestation accounts decode to the expected
verdict, rule-pack hash and issuer (`scripts/demo_e2e.sh` reproduces this).
The LiteSVM unit suite for the program is archived under
`programs/uhakiki/tests/` (disabled pending the Anchor 1.2 / litesvm type
unification — see the note in that directory).

## Why Solana

Verdicts settle in ~1 second at a fraction of a penny. Attestations are
on-chain ownership of a compliance decision: any marketplace, pool, or
lending protocol can read them trustlessly — the proof *is* the product.

## What's next

Node Engine / W3Node Cape Town (Nov 12–14, Real-World Assets track): more
asset classes (land deeds), more jurisdictions (SA pack), SPL-tokenized
invoice purchases gated on a valid ALLOW attestation.

