"""YAML rule-pack loader — fail loud on anything malformed."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

PACKS_DIR = Path(__file__).resolve().parents[1] / "packs"

_SEVERITIES = {"deny", "restrict"}


class Rule(BaseModel):
    id: str
    description: str
    severity: str
    check: str

    @model_validator(mode="after")
    def _shape(self) -> "Rule":
        if self.severity not in _SEVERITIES:
            raise ValueError(f"rule {self.id!r}: severity must be one of {_SEVERITIES}")
        if not self.check.strip():
            raise ValueError(f"rule {self.id!r}: check expression is empty")
        return self


class RulePack(BaseModel):
    pack_id: str
    jurisdiction: str
    asset_class: str
    rules: list[Rule] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> "RulePack":
        ids = [r.id for r in self.rules]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate rule ids in pack {self.pack_id!r}")
        return self


def load_pack(path: Path | None = None) -> tuple[RulePack, str]:
    """Load one YAML pack, validate it, and return (pack, sha256-hex)."""
    path = path or PACKS_DIR / "kenya_invoices.yaml"
    raw = path.read_bytes()
    pack = RulePack(**yaml.safe_load(raw))
    return pack, hashlib.sha256(raw).hexdigest()


# The evaluator compiles each rule's `check` into a tiny, whitelisted
# expression evaluator (no eval): only the variables and operators below.
_ALLOWED_OPS = re.compile(r"[a-zA-Z_][a-zA-Z0-9_.]*|==|!=|>=|<=|>|<|and\b|or\b|not\b|is\b|none\b|True\b|False\b|\(|\)|\[|\]|,|\d+\.?\d*|-|\+|\s+")


def check_expression(expr: str) -> str:
    """Reject anything outside the whitelisted expression grammar."""
    cleaned = _ALLOWED_OPS.sub("", expr)
    if cleaned.strip():
        raise ValueError(f"illegal token in check expression {expr!r}: {cleaned.strip()!r}")
    return expr
