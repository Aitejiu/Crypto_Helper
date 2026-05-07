from __future__ import annotations

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
