from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel


class SecurityAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REDACT = "redact"
    REQUIRE_APPROVAL = "require_approval"


class SecurityDecision(DomainModel):
    action: SecurityAction
    risk_level: str
    reason: str
    rewritten_safe_intent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
