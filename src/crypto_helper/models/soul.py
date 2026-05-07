from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from crypto_helper.models.common import DomainModel


class IdentityBoundary(DomainModel):
    must_not_claim_real_identity: bool
    must_state_simulation: bool


class TradingSoul(DomainModel):
    style_traits: list[str] = Field(default_factory=list)
    preferred_setups: list[str] = Field(default_factory=list)
    risk_management: list[str] = Field(default_factory=list)


class ReasoningStyle(DomainModel):
    summary: str
    key_patterns: list[str] = Field(default_factory=list)


class LanguageSoul(DomainModel):
    tone: str
    disclaimers: list[str] = Field(default_factory=list)


class SafetyRules(DomainModel):
    no_direct_financial_advice: bool
    must_include_evidence: bool
    must_include_confidence: bool
    must_include_limitations: bool


class UpdatePolicy(DomainModel):
    auto_apply_threshold: float = 0.8
    manual_review_threshold: float = 0.6


class KOLSoul(DomainModel):
    kol_id: str
    identity_boundary: IdentityBoundary
    trading_soul: TradingSoul
    reasoning_style: ReasoningStyle
    language_soul: LanguageSoul
    safety_rules: SafetyRules
    update_policy: UpdatePolicy

    @model_validator(mode="after")
    def validate_hard_safety_rules(self) -> KOLSoul:
        if not self.identity_boundary.must_not_claim_real_identity:
            raise ValueError("identity boundary must forbid real identity claims")
        if not self.safety_rules.no_direct_financial_advice:
            raise ValueError("direct financial advice must remain disabled")
        if not self.safety_rules.must_include_evidence:
            raise ValueError("evidence is required")
        if not self.safety_rules.must_include_confidence:
            raise ValueError("confidence is required")
        if not self.safety_rules.must_include_limitations:
            raise ValueError("limitations are required")
        return self


class SoulPatch(DomainModel):
    patch_id: str
    kol_id: str
    observed_behavior: str
    summary: str
    confidence: float
    requires_review: bool
    trading_style_additions: list[str] = Field(default_factory=list)
    reasoning_pattern_additions: list[str] = Field(default_factory=list)
    identity_boundary_updates: dict[str, bool] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
