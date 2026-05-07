from __future__ import annotations

import re
from collections.abc import Sequence

from crypto_helper.core.evidence_store import search_evidence
from crypto_helper.core.profile_service import get_profile
from crypto_helper.core.registry_service import require_kol
from crypto_helper.core.security_review import review_text
from crypto_helper.core.soul_store import get_soul
from crypto_helper.models.common import DomainError
from crypto_helper.models.evidence import EvidenceRef
from crypto_helper.models.persona import PersonaAnswer
from crypto_helper.models.registry import KOLStatus, KOLTier
from crypto_helper.models.security import SecurityAction

DISCLAIMER = "这是基于历史画像的模拟推理，不代表该 KOL 本人实时观点。"


def ask_persona(kol_query: str, question: str) -> PersonaAnswer:
    security = review_text(question)
    if security.action == SecurityAction.DENY:
        raise DomainError(
            security.reason,
            code="SECURITY_DENIED",
            metadata={"security": security.model_dump(mode="json")},
        )
    if security.action == SecurityAction.REQUIRE_APPROVAL:
        raise DomainError(
            security.reason,
            code="SECURITY_RESTRICTED",
            metadata={"security": security.model_dump(mode="json")},
        )
    entry = require_kol(kol_query)
    if entry.status == KOLStatus.DISABLED:
        raise DomainError(
            f"{entry.display_name} is disabled and unavailable for persona simulation.",
            code="KOL_DISABLED",
        )
    soul_payload = get_soul(entry.kol_id)
    profile_payload = get_profile(entry.kol_id)
    symbol = _extract_symbol(question, entry.allowed_symbols)
    evidence = search_evidence(kol_query=entry.kol_id, symbol=symbol, query=question, limit=5)
    profile = profile_payload["profile"]
    soul = soul_payload["soul"]
    limitations = list(evidence.limitations)
    limitations.extend(profile_payload["limitations"])
    limitations.extend(soul_payload["limitations"])
    if entry.status == KOLStatus.ARCHIVED:
        limitations.append(
            "This answer is restricted to historical analysis because the KOL is archived."
        )
    confidence = _compute_confidence(entry.tier, profile.reliability, len(evidence.items))
    reasoning = _build_reasoning(
        profile.trade_style, soul.reasoning_style.key_patterns, evidence.items
    )
    answer = _build_answer(entry.display_name, question, profile.trade_style, symbol, entry.status)
    metadata = {
        "kol_id": entry.kol_id,
        "symbol": symbol,
        "tier": entry.tier,
        "security_category": security.metadata.get("category"),
    }
    return PersonaAnswer(
        disclaimer=DISCLAIMER,
        answer=answer,
        reasoning=reasoning,
        evidence_refs=evidence.items,
        confidence=confidence,
        limitations=_dedupe(limitations),
        metadata=metadata,
    )


def _extract_symbol(question: str, allowed_symbols: list[str]) -> str | None:
    matches: list[str] = re.findall(r"\b[A-Z]{2,5}\b", question.upper())
    for match in matches:
        if match in allowed_symbols:
            return match
    return allowed_symbols[0] if allowed_symbols else None


def _compute_confidence(tier: KOLTier, reliability: float, evidence_count: int) -> float:
    confidence = reliability
    if tier == KOLTier.DYNAMIC:
        confidence -= 0.18
    if evidence_count < 3:
        confidence -= 0.12
    elif evidence_count >= 5:
        confidence += 0.05
    return round(min(max(confidence, 0.22), 0.9), 2)


def _build_reasoning(
    trade_style: list[str],
    reasoning_patterns: list[str],
    evidence_items: Sequence[EvidenceRef],
) -> str:
    style_text = ", ".join(trade_style) if trade_style else "limited style evidence"
    pattern_text = (
        ", ".join(reasoning_patterns[:3]) if reasoning_patterns else "conditional reasoning"
    )
    evidence_text = (
        "; ".join(item.summary for item in evidence_items[:2]) if evidence_items else "thin data"
    )
    return (
        f"Historical profile suggests {style_text}. Reasoning patterns emphasize {pattern_text}. "
        f"Most relevant evidence: {evidence_text}."
    )


def _build_answer(
    display_name: str,
    question: str,
    trade_style: list[str],
    symbol: str | None,
    status: KOLStatus,
) -> str:
    lowered = question.lower()
    symbol_text = symbol or "the referenced symbol"
    if status == KOLStatus.ARCHIVED:
        prefix = f"Historically, {display_name}'s archived profile suggests "
    else:
        prefix = f"{display_name}'s profile-based simulation suggests "
    if "break" in lowered or "跌破" in question:
        return (
            f"{prefix}treating a break around {symbol_text} as an invalidation test, waiting for "
            f"confirmation or reclaim before adding risk, and managing size with partial TP or "
            f"breakeven protection."
        )
    if "historical" in lowered or "历史" in question:
        return (
            f"{prefix}a historical style built around {', '.join(trade_style[:3])}, with decisions "
            f"framed as conditional scenarios instead of real-time calls."
        )
    return (
        f"{prefix}a cautious, evidence-backed view on {symbol_text}, leaning on "
        f"{', '.join(trade_style[:3]) if trade_style else 'limited historical traits'}."
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
