"""Verdict → plain-language explanation (English + Swahili).

Two modes:
- LLM mode (HAKI_LLM_KEY set): an OpenAI-compatible model rewrites the
  grounded template into flowing prose. The prompt forbids inventing facts.
- Deterministic mode (no key): a template built ONLY from the triggered
  rules — the same guardrail, zero cost, demo-safe.

Either way the model/explainer only sees what the rules engine already
decided. It can add tone; it can never add reasons.
"""
from __future__ import annotations

import os

import httpx

from engine.schemas import ScreenResult, TriggeredRule, Verdict

LLM_TIMEOUT_S = 12.0

# --- deterministic templates (grounded: only triggered rule ids/descriptions) ---

_EN_OPEN = {
    Verdict.ALLOW: "This invoice passed our compliance screening — verdict ALLOW.",
    Verdict.RESTRICT: "This invoice can proceed only after enhanced review — verdict RESTRICT.",
    Verdict.DENY: "This invoice was rejected by our compliance screening — verdict DENY.",
}
_SW_OPEN = {
    Verdict.ALLOW: "Hati hii imeshapita ukaguzi wetu wa kufuata sheria — hukumu: ALLOW (kubali).",
    Verdict.RESTRICT: "Hati hii inaweza kuendelea baada ya ukaguzi wa ziada — hukumu: RESTRICT (dhibiti).",
    Verdict.DENY: "Hati hii imekataliwa na ukaguzi wetu wa kufuata sheria — hukumu: DENY (kataa).",
}


def _template(result: ScreenResult) -> tuple[str, str]:
    en_lines, sw_lines = [], []
    en_lines.append(_EN_OPEN[Verdict(result.verdict)])
    sw_lines.append(_SW_OPEN[Verdict(result.verdict)])
    if result.triggered_rules:
        en_lines.append(
            "Reasons (from the Kenya invoice rule pack): "
            + "; ".join(f"{t.rule_id} — {t.description}" for t in result.triggered_rules)
            + "."
        )
        sw_lines.append(
            "Sababu (kutoka kwenye pack ya sheria za hati za Kenya): "
            + "; ".join(f"{t.rule_id} — {t.description}" for t in result.triggered_rules)
            + "."
        )
    else:
        en_lines.append("No rules were triggered: both parties are verified, the invoice "
                        "documents are complete, and it is within all limits.")
        sw_lines.append("Hakuna sheria iliyokiuka: pande zote mbili zimehakikiwa, hati zina "
                        "kamilifu zote, na kiasi kiko ndani ya mipaka.")
    en_lines.append("The verdict was produced by a deterministic rules engine; this "
                    "explanation only restates the rules that fired.")
    sw_lines.append("Hukumu hii ilitolewa na mfumo wa sheria; maelezo haya yanarudia "
                    "sheria zilizofanya kazi tu.")
    return "\n\n".join(en_lines), "\n\n".join(sw_lines)


_SYSTEM = (
    "You are Uhakiki's compliance explainer. Given a deterministic verdict and the "
    "triggered rules, explain to a small-business owner in plain language why the "
    "decision was made. Do not invent reasons beyond the triggered rules. Output JSON "
    "with keys explanation_en and explanation_sw."
)


def _llm(result: ScreenResult) -> tuple[str, str] | None:
    key = os.environ.get("HAKI_LLM_KEY", "").strip()
    if not key:
        return None
    base = os.environ.get("HAKI_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("HAKI_LLM_MODEL", "gpt-4o-mini")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _template(result)[0] + "\n\nRewrite this as "
                     "explanation_en and explanation_sw JSON. Keep every rule id."},
                ],
                "temperature": 0,
            },
            timeout=LLM_TIMEOUT_S,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        if not content:
            raise ValueError("empty LLM response")
        import json

        data = json.loads(content)
        en, sw = data["explanation_en"], data["explanation_sw"]
        # Grounding guardrail: every triggered rule id must appear verbatim.
        for t in result.triggered_rules:
            if t.rule_id not in en or t.rule_id not in sw:
                raise ValueError("LLM output dropped a triggered rule id")
        return en, sw
    except Exception:
        return None  # demo-safe: fall back to the grounded template


def explain_result(result: ScreenResult) -> dict:
    llm = _llm(result)
    en, sw = llm if llm else _template(result)
    return {
        "mode": "llm" if llm else "template",
        "explanation_en": en,
        "explanation_sw": sw,
    }
