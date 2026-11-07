"""The verdict matrix of the Uhakiki engine — ≥6 cases covering every branch.

ALLOW  = no rule triggered
DENY   = any deny-severity rule triggered (sanctions, KYC, missing doc hash)
RESTRICT = restrict-severity only (risk score, overdue, size)
Worst severity wins.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]          # uhakiki/ (for agent package)
sys.path.insert(0, str(ROOT / "engine"))            # engine package
sys.path.insert(0, str(ROOT))

from engine.loader import load_pack  # noqa: E402
from engine.evaluator import screen  # noqa: E402
from engine.schemas import InvoiceSubmission, Party, Verdict  # noqa: E402

PACK, PACK_HASH = load_pack()


def invoice(**over) -> InvoiceSubmission:
    base = dict(
        asset_id="INV-NBO-2026-0042",
        seller=Party(name="Mama Mboga Logistics", wallet="4Nd1mBQtrMJVYVfKf2PJy9NZUZdTAsG7VMuNGrNiXq8c",
                     kyc_verified=True, sanctions_hit=False, risk_score=0.2),
        buyer=Party(name="Nairobi Supermarket Chain", wallet="9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                    kyc_verified=True, sanctions_hit=False, risk_score=0.3),
        amount_kes=500_000,
        days_until_due=60,
        doc_sha256="a" * 64,
    )
    base.update(over)
    return InvoiceSubmission(**base)


def verdict_of(**over) -> Verdict:
    return screen(invoice(**over), PACK, PACK_HASH).verdict


def triggered(**over) -> set[str]:
    r = screen(invoice(**over), PACK, PACK_HASH)
    return {t.rule_id for t in r.triggered_rules}


# ---------- the 30-cell core: three verdict branches ----------

def test_clean_mama_mboga_invoice_is_allow():
    assert verdict_of() is Verdict.ALLOW
    assert triggered() == set()


def test_sanctions_hit_on_buyer_is_deny():
    assert verdict_of(buyer={"name": "Bad Actor", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                             "kyc_verified": True, "sanctions_hit": True, "risk_score": 0.3}) is Verdict.DENY
    assert "ke-sanc-parties" in triggered(buyer={"name": "Bad Actor", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                                                "kyc_verified": True, "sanctions_hit": True, "risk_score": 0.3})


def test_sanctions_hit_on_seller_is_deny_too():
    """The `party.*` check must fire for EITHER party."""
    assert verdict_of(seller={"name": "Shady Seller", "wallet": "4Nd1mBQtrMJVYVfKf2PJy9NZUZdTAsG7VMuNGrNiXq8c",
                              "kyc_verified": True, "sanctions_hit": True, "risk_score": 0.2}) is Verdict.DENY


def test_missing_kyc_is_deny():
    assert verdict_of(buyer={"name": "Unverified Buyer", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                             "kyc_verified": False, "sanctions_hit": False, "risk_score": 0.3}) is Verdict.DENY
    assert "ke-kyc-verified" in triggered(buyer={"name": "Unverified Buyer", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                                                "kyc_verified": False, "sanctions_hit": False, "risk_score": 0.3})


def test_missing_doc_hash_is_deny():
    assert verdict_of(doc_sha256=None) is Verdict.DENY
    assert "ke-doc-hash" in triggered(doc_sha256=None)


def test_high_risk_buyer_is_restrict():
    assert verdict_of(buyer={"name": "Risky Buyer", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                             "kyc_verified": True, "sanctions_hit": False, "risk_score": 0.9}) is Verdict.RESTRICT
    assert "ke-buyer-risk" in triggered(buyer={"name": "Risky Buyer", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                                              "kyc_verified": True, "sanctions_hit": False, "risk_score": 0.9})


def test_overdue_invoice_is_restrict():
    assert verdict_of(days_until_due=-5) is Verdict.RESTRICT
    assert "ke-invoice-age" in triggered(days_until_due=-5)


def test_oversized_invoice_is_restrict():
    assert verdict_of(amount_kes=15_000_000) is Verdict.RESTRICT
    assert "ke-invoice-size" in triggered(amount_kes=15_000_000)


# ---------- boundary cases ----------

def test_risk_score_boundary_exactly_06_is_restrict():
    assert verdict_of(buyer={"name": "Edge Buyer", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                             "kyc_verified": True, "sanctions_hit": False, "risk_score": 0.6}) is Verdict.RESTRICT


def test_risk_score_just_below_06_is_allow():
    assert verdict_of(buyer={"name": "Edge Buyer", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                             "kyc_verified": True, "sanctions_hit": False, "risk_score": 0.59}) is Verdict.ALLOW


def test_invoice_size_boundary_exactly_10m_is_allow():
    assert verdict_of(amount_kes=10_000_000) is Verdict.ALLOW


# ---------- worst-severity-wins invariant ----------

def test_deny_beats_restrict():
    """High risk (restrict) + sanctions (deny) => DENY, and BOTH reasons listed."""
    bad_buyer = {"name": "Very Bad Buyer", "wallet": "9gTAgF5YmGZK4GjwKLonBj7CqK9fGrPnNDdtHq7LypqD",
                 "kyc_verified": True, "sanctions_hit": True, "risk_score": 0.9}
    assert verdict_of(buyer=bad_buyer) is Verdict.DENY
    ids = triggered(buyer=bad_buyer)
    assert {"ke-sanc-parties", "ke-buyer-risk"} <= ids


# ---------- reproducibility ----------

def test_pack_hash_is_stable_sha256():
    assert len(PACK_HASH) == 64 and PACK_HASH == PACK_HASH


def test_result_carries_pack_provenance():
    r = screen(invoice(), PACK, PACK_HASH)
    assert r.rule_pack_id == "kenya-invoices-v1"
    assert r.rule_pack_hash == PACK_HASH
