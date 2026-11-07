"""On-chain attestation writer — builds and sends issue_attestation to DevNet.

The instruction discriminator and borsh layout mirror the Anchor program in
program/programs/uhakiki/src. The payer key comes from UHAKIKI_ATTESTER_KEY
(base58 secret or a solana-keygen JSON file path) — never committed.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

import httpx
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

RPC_URL = os.environ.get("UHAKIKI_RPC_URL", "https://api.devnet.solana.com")
PROGRAM_ID = Pubkey.from_string("FEvabxdQJsdDaQuHi9fzWH7MvUygpMUS7DWUtmQkGVtd")
SEED = b"attestation"
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")

VERDICT_INDEX = {"ALLOW": 0, "RESTRICT": 1, "DENY": 2}


def _discriminator(name: str) -> bytes:
    return hashlib.sha256(f"global:{name}".encode()).digest()[:8]


def _borsh_string(s: str) -> bytes:
    raw = s.encode("utf-8")
    return len(raw).to_bytes(4, "little") + raw


def _load_keypair() -> Keypair:
    raw = os.environ.get("UHAKIKI_ATTESTER_KEY", "").strip()
    if not raw:
        raise RuntimeError(
            "UHAKIKI_ATTESTER_KEY not set — expected a base58 secret key "
            "or a path to a solana-keygen JSON file"
        )
    if raw.startswith("[") or raw.endswith(".json"):
        if raw.endswith(".json"):
            arr = json.loads(open(raw).read())
        else:
            arr = json.loads(raw)
        return Keypair.from_bytes(bytes(arr))
    return Keypair.from_base58_string(raw)


def _rpc(http: httpx.Client, method: str, params: list) -> dict:
    resp = http.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"RPC error: {body['error']}")
    return body["result"]


def attest(result) -> dict:
    """Send issue_attestation for a ScreenResult. Returns explorer links."""
    kp = _load_keypair()
    http = httpx.Client(timeout=30)

    asset_id = result.asset_id
    # PDA seeds mirror the program: asset_id is hashed (seed length cap 32)
    id_hash = hashlib.sha256(asset_id.encode("utf-8")).digest()
    pda, bump = Pubkey.find_program_address([SEED, bytes(kp.pubkey()), id_hash], PROGRAM_ID)

    data = _discriminator("issue_attestation")
    data += _borsh_string(asset_id)
    data += bytes([VERDICT_INDEX[result.verdict.value]])
    data += bytes.fromhex(result.rule_pack_hash)
    data += _borsh_string("https://uhakiki.demo/rationale/" + asset_id)
    data += bytes(kp.pubkey())  # issuer_ref — trace to the off-chain run

    accounts = [
        AccountMeta(kp.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pda, is_signer=False, is_writable=True),
        AccountMeta(SYSTEM_PROGRAM, is_signer=False, is_writable=False),
    ]
    ix = Instruction(PROGRAM_ID, bytes(data), accounts)

    blockhash_raw = _rpc(http, "getLatestBlockhash", [])["value"]["blockhash"]
    blockhash = hashlib.sha256(base64.b64decode(blockhash_raw)).digest()  # placeholder replaced below
    # solders accepts the base58 blockhash directly via Hash:
    from solders.hash import Hash

    blockhash = Hash.from_string(blockhash_raw)
    msg = Message.new_with_blockhash([ix], kp.pubkey(), blockhash)
    tx = Transaction([kp], msg, blockhash)
    import base64 as _b64

    encoded = _b64.b64encode(bytes(tx)).decode()
    signature = _rpc(http, "sendTransaction",
                     [encoded, {"encoding": "base64", "skip_preflight": False}])
    return {
        "mode": "onchain",
        "signature": signature,
        "attestation_pda": str(pda),
        "explorer_url": f"https://explorer.solana.com/tx/{signature}?cluster=devnet",
        "pda_url": f"https://explorer.solana.com/account/{pda}?cluster=devnet",
    }
