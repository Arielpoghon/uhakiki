"""Deterministic evaluator — pure functions, no LLM anywhere in this module.

Each rule's `check` expression is validated against an AST whitelist (no
eval of arbitrary code), then evaluated against the submission scope.
Semantics: a rule TRIGGERS when its check is False (violation); the final
verdict is DENY if any deny-severity rule triggered, else RESTRICT if any
restrict-severity rule triggered, else ALLOW.
"""
from __future__ import annotations

import ast
import re

from .loader import Rule, RulePack
from .schemas import InvoiceSubmission, ScreenResult, TriggeredRule, Verdict

_TRUE_WARMUP = re.compile(r"\bfalse\b|\btrue\b|\bnone\b")

_ALLOWED_NODES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.Name,
    ast.Attribute,
    ast.Constant,
    ast.Load,
)

_ROOTS = {"invoice", "buyer", "seller", "party"}


def _normalize(expr: str) -> str:
    return _TRUE_WARMUP.sub(
        lambda m: {"false": "False", "true": "True", "none": "None"}[m.group(0)],
        expr,
    )


def _validate(tree: ast.AST, expr: str) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"illegal syntax {type(node).__name__!r} in check {expr!r}")
        if isinstance(node, ast.Name) and node.id not in _ROOTS:
            raise ValueError(f"unknown variable {node.id!r} in check {expr!r}")


def _get(obj: object, name: str) -> object:
    value = getattr(obj, name)
    if callable(value):
        raise ValueError(f"attribute {name!r} is callable — methods are not allowed in checks")
    return value


def _eval_node(node: ast.AST, scope: dict) -> object:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, scope)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return scope[node.id]
    if isinstance(node, ast.Attribute):
        return _get(_eval_node(node.value, scope), node.attr)
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, scope) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.UnaryOp):
        return not _eval_node(node.operand, scope)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, scope)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, scope)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right  # type: ignore[operator]
            elif isinstance(op, ast.LtE):
                ok = left <= right  # type: ignore[operator]
            elif isinstance(op, ast.Gt):
                ok = left > right  # type: ignore[operator]
            elif isinstance(op, ast.GtE):
                ok = left >= right  # type: ignore[operator]
            elif isinstance(op, ast.Is):
                ok = left is right
            elif isinstance(op, ast.IsNot):
                ok = left is not right
            else:  # pragma: no cover — AST whitelist keeps this unreachable
                raise ValueError("illegal comparison operator")
            if not ok:
                return False
            left = right
        return True
    raise ValueError(f"illegal syntax {type(node).__name__!r}")  # pragma: no cover


def _check_passes(rule: Rule, invoice: InvoiceSubmission) -> bool:
    """True = compliant. `party.*` checks are evaluated for BOTH parties:
    the rule triggers if either party violates it."""
    code = _normalize(rule.check)
    tree = ast.parse(code, mode="eval")
    _validate(tree, rule.check)

    base = {"invoice": invoice, "buyer": invoice.buyer, "seller": invoice.seller}
    if "party." in rule.check:
        return all(
            bool(_eval_node(tree, {**base, "party": p}))
            for p in (invoice.seller, invoice.buyer)
        )
    return bool(_eval_node(tree, base))


def screen(invoice: InvoiceSubmission, pack: RulePack, pack_hash: str) -> ScreenResult:
    """Run every rule; worst severity wins. DENY > RESTRICT > ALLOW."""
    triggered: list[TriggeredRule] = []
    for rule in pack.rules:
        if not _check_passes(rule, invoice):
            triggered.append(
                TriggeredRule(rule_id=rule.id, description=rule.description, severity=rule.severity)
            )

    if any(t.severity == "deny" for t in triggered):
        verdict = Verdict.DENY
    elif any(t.severity == "restrict" for t in triggered):
        verdict = Verdict.RESTRICT
    else:
        verdict = Verdict.ALLOW

    return ScreenResult(
        asset_id=invoice.asset_id,
        verdict=verdict,
        triggered_rules=triggered,
        rule_pack_id=pack.pack_id,
        rule_pack_hash=pack_hash,
        evaluated_at=datetime_now(),
    )


def datetime_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
