# Uhakiki program tests

The LiteSVM-based suite (`uhakuki.rs.disabled`) documents the intended
behavior: issue/upsert/revoke/auth/seed-limit — 6 tests. It is currently
**disabled**: Anchor 1.2's rustup-managed sbf toolchain and the litesvm 0.18
type world (Address vs compat Pubkey) don't unify cleanly on this machine.

The program's behavior is instead verified end-to-end against a live
validator: `scripts/demo_e2e.sh` deploys `target/deploy/uhakiki.so` to a
local test validator, screens the Mama Mboga invoice through the rules
engine, attests on-chain via the Python client, and reads the verdict back
from the account data — the same flow the DevNet demo uses.
