# Uhakiki — Devpost submission text

**Name:** Uhakiki
**One-liner:** AI compliance agent that screens tokenized real-world assets and issues verifiable on-chain attestations on Solana.
**Tracks:** AI Track + DeFi Track (auto-entered for Top 3)

## Inspiration
African SMEs are paid 30–120 days late while suppliers need cash now. The
MSME financing gap in Sub-Saharan Africa is estimated at $300B+ (IFC). The
bottleneck in invoice financing is always the same: verification and
compliance — is the invoice real, is the buyer creditworthy, is anyone
sanctioned, does the deal comply? That review is manual, slow and expensive.

## What it does
Uhakiki screens a tokenized invoice against a Kenya rule pack, produces
ALLOW / RESTRICT / DENY with a written rationale (English + Swahili), and
writes the verdict to Solana DevNet as an on-chain attestation (Anchor
program, EAS-style PDA registry) with the rule-pack hash for
reproducibility. A live demo flips the buyer to a sanctioned entity —
ALLOW → DENY in one click — and a wallet screener reads real DevNet history
and flags risky activity before a user signs.

## How we built it
- **Uhakiki program** (Anchor/Rust, DevNet): Attestation PDA
  ["attestation", issuer, asset_id]; issue (upsert) + revoke; rule-pack
  sha256 + rationale URI stored on-chain. Tested with LiteSVM in-process
  (issue/upsert/revoke/auth/overflow — 6 tests).
- **Rules engine** (Python, deterministic): YAML jurisdiction pack,
  AST-whitelisted check expressions (no eval), worst-severity-wins.
- **Agent** (explain-only): grounded EN+SW explanations — guardrailed so it
  can only reference the triggered rules; falls back to a template when no
  LLM key is set (demo-safe).
- **Dashboard**: single-file HTML, zero build step, scenario flip.
- **Stack:** Solana, Anchor, Rust, LiteSVM, Python, FastAPI, Pydantic.

## Disclosure
An earlier prototype of this concept (Haki) was built for a different event
on Base. Uhakiki is a complete ground-up rebuild on Solana written entirely
during this hackathon.

## Challenges
Getting the Anchor 1.2 toolchain working (needed Agave 4 + a rustup sbf
toolchain); writing an evaluator that validates rule expressions safely
without eval; keeping the LLM honest by construction (grounding guardrail).

## Accomplishments
End-to-end: form → deterministic verdict → bilingual AI explanation →
on-chain attestation — with the compliance decision verifiable by anyone on
the Solana explorer.

## What we learned
Compliance is the actual blocker for on-chain RWAs in Africa; deterministic
verification + AI explanation is a credible pattern for it; Solana's speed
and cost make per-invoice attestations practical.

## What's next
Cape Town (W3Node Real-World Assets track, Nov 12–14): land deeds as an
asset class, a South Africa rule pack, SPL-tokenized invoice purchases
gated on a valid ALLOW attestation.
