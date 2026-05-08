from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from crypto_helper.models.persona import PersonaAnswer
from crypto_helper.models.registry import KOLStatus, KOLTier
from crypto_helper.models.security import SecurityAction, SecurityDecision
from crypto_helper.models.soul import (
    IdentityBoundary,
    KOLSoul,
    LanguageSoul,
    ReasoningStyle,
    SafetyRules,
    TradingSoul,
    UpdatePolicy,
)
from crypto_helper.models.vector import VectorDocument, VectorIndexStatus, VectorSearchResult


def test_kol_status_enum() -> None:
    assert KOLStatus.ACTIVE.value == "active"


def test_kol_tier_enum() -> None:
    assert KOLTier.DYNAMIC.value == "dynamic"


def test_kol_soul_hard_safety_validations() -> None:
    with pytest.raises(ValidationError):
        KOLSoul(
            kol_id="kol_bad",
            identity_boundary=IdentityBoundary(
                must_not_claim_real_identity=False,
                must_state_simulation=True,
            ),
            trading_soul=TradingSoul(),
            reasoning_style=ReasoningStyle(summary="bad"),
            language_soul=LanguageSoul(tone="bad"),
            safety_rules=SafetyRules(
                no_direct_financial_advice=True,
                must_include_evidence=True,
                must_include_confidence=True,
                must_include_limitations=True,
            ),
            update_policy=UpdatePolicy(),
        )


def test_persona_answer_requires_disclaimer() -> None:
    with pytest.raises(ValidationError):
        PersonaAnswer(
            disclaimer="",
            answer="x",
            reasoning="y",
            confidence=0.5,
        )


def test_security_decision_action_enum() -> None:
    decision = SecurityDecision(
        action=SecurityAction.ALLOW,
        risk_level="low",
        reason="ok",
    )
    assert decision.action == SecurityAction.ALLOW


def test_vector_document_model() -> None:
    document = VectorDocument(
        doc_id="doc_1",
        evidence_id="evidence_1",
        kol_id="kol_a",
        display_name="KOL_A",
        symbol="BTC",
        source_type="opinion",
        timestamp=datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
        channel_scope="imported_channel:test",
        confidence=0.82,
        text="KOL: KOL_A\nSymbol: BTC\nSummary: reclaim then continuation",
    )
    assert document.doc_id == "doc_1"
    assert document.display_name == "KOL_A"


def test_vector_search_result_model() -> None:
    result = VectorSearchResult(
        doc_id="doc_1",
        evidence_id="evidence_1",
        score=0.91,
        source_type="news",
        summary="Important SOL market update.",
    )
    assert result.score == 0.91
    assert result.source_type == "news"


def test_vector_index_status_model() -> None:
    status = VectorIndexStatus(
        index_path="./crypto_helper_data/vector_index/chroma",
        document_count=12,
        embedding_model="BAAI/bge-m3",
        backend="chroma",
        enabled=True,
    )
    assert status.backend == "chroma"
    assert status.enabled is True
