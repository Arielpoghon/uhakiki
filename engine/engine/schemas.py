"""Pydantic models — the typed core of the Uhakiki rules engine."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Party(BaseModel):
    name: str
    wallet: str
    kyc_verified: bool
    sanctions_hit: bool
    risk_score: float = Field(ge=0.0, le=1.0)  # mock source for the demo


class InvoiceSubmission(BaseModel):
    asset_id: str
    seller: Party
    buyer: Party
    amount_kes: float = Field(gt=0)
    days_until_due: int
    doc_sha256: Optional[str] = None


class TriggeredRule(BaseModel):
    rule_id: str
    description: str
    severity: Literal["deny", "restrict"]


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    RESTRICT = "RESTRICT"
    DENY = "DENY"


class ScreenResult(BaseModel):
    asset_id: str
    verdict: Verdict
    triggered_rules: list[TriggeredRule] = Field(default_factory=list)
    rule_pack_id: str
    rule_pack_hash: str  # sha256 hex of the YAML pack — reproducibility
    evaluated_at: datetime
