from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel


class SafetyLevel(StrEnum):
    STANDARD = "standard"
    GUARDED = "guarded"
    HIGH_RISK = "high_risk"
    ADMIN_ONLY = "admin_only"


class SafetyAction(StrEnum):
    ALLOW = "allow"
    REFUSE = "refuse"
    DOWNGRADE = "downgrade"
    REQUIRE_ADMIN = "require_admin"


class SafetyIssue(DomainModel):
    code: str
    message: str
    severity: SafetyLevel
    metadata: dict[str, Any] = Field(default_factory=dict)


class SafetyDecision(DomainModel):
    action: SafetyAction
    safety_level: SafetyLevel
    reason: str
    issues: list[SafetyIssue] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
