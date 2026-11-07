"""Seed data for the Uhakiki demo — Mama Mboga Logistics scenario.

Clean path:   ALLOW (verified buyer, no sanctions, docs complete)
Flipped path: DENY  (sanctioned buyer) — the contrast judges remember.
"""
CLEAN_INVOICE = {
    "asset_id": "INV-NBO-2026-0042",
    "seller": {
        "name": "Mama Mboga Logistics",
        "wallet": "4Nd1mBQtrMJVYVfKf2PJy9NZUZdTAsG7VMuNGrNiXq8c",
        "kyc_verified": True,
        "sanctions_hit": False,
        "risk_score": 0.2,
    },
    "buyer": {
        "name": "Nairobi Supermarket Chain",
        "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
        "kyc_verified": True,
        "sanctions_hit": False,
        "risk_score": 0.3,
    },
    "amount_kes": 500_000,
    "days_until_due": 60,
    "doc_sha256": "3f2a9c8e77b1d4c25e6a0b9d8c7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e",
}

def sanctioned_buyer(invoice: dict) -> dict:
    flipped = dict(invoice)
    flipped["buyer"] = {
        "name": "Sanctioned Buyer (demo)",
        "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
        "kyc_verified": True,
        "sanctions_hit": True,
        "risk_score": 0.9,
    }
    return flipped

if __name__ == "__main__":
    import json, sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "engine"))
    from engine.evaluator import screen
    from engine.loader import load_pack
    from engine.schemas import InvoiceSubmission

    pack, pack_hash = load_pack()
    clean = InvoiceSubmission(**CLEAN_INVOICE)
    dirty = InvoiceSubmission(**sanctioned_buyer(CLEAN_INVOICE))
    print("CLEAN scenario  :", screen(clean, pack, pack_hash).verdict.value)
    print("SANCTIONS buyer :", screen(dirty, pack, pack_hash).verdict.value)
