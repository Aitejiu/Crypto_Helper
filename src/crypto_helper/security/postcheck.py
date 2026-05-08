from __future__ import annotations

import json
from typing import Any

from crypto_helper.request_context import RequestContext
from crypto_helper.security.policies import (
    FABRICATED_EVIDENCE_PHRASES,
    IMPERSONATION_PHRASES,
    INVESTMENT_ADVICE_PHRASES,
    PRIVATE_EXPORT_PHRASES,
    REALTIME_CLAIM_PHRASES,
)
from crypto_helper.security.schemas import (
    SafetyAction,
    SafetyDecision,
    SafetyIssue,
    SafetyLevel,
)


def output_safety_postcheck(
    request_context: RequestContext,
    workflow_id: str,
    draft_answer: Any,
) -> SafetyDecision:
    del request_context, workflow_id
    text = _draft_to_text(draft_answer).lower()
    if _contains_any(text, PRIVATE_EXPORT_PHRASES):
        return _decision(
            action=SafetyAction.REFUSE,
            level=SafetyLevel.HIGH_RISK,
            reason="Output must not expose private raw messages.",
            issue_code="private_export_output",
        )
    if _contains_any(text, IMPERSONATION_PHRASES):
        return _decision(
            action=SafetyAction.REFUSE,
            level=SafetyLevel.HIGH_RISK,
            reason="Output must not impersonate a real KOL.",
            issue_code="impersonation_output",
        )
    if _contains_any(text, REALTIME_CLAIM_PHRASES):
        return _decision(
            action=SafetyAction.REFUSE,
            level=SafetyLevel.HIGH_RISK,
            reason="Output must not claim to represent a KOL's real-time viewpoint.",
            issue_code="realtime_claim_output",
        )
    if _contains_any(text, FABRICATED_EVIDENCE_PHRASES):
        return _decision(
            action=SafetyAction.REFUSE,
            level=SafetyLevel.HIGH_RISK,
            reason="Output must not fabricate evidence or sources.",
            issue_code="fabricated_evidence_output",
        )
    if _contains_any(text, INVESTMENT_ADVICE_PHRASES):
        return _decision(
            action=SafetyAction.DOWNGRADE,
            level=SafetyLevel.HIGH_RISK,
            reason="Output must not contain direct trading or investment instructions.",
            issue_code="investment_advice_output",
        )
    return _decision(
        action=SafetyAction.ALLOW,
        level=SafetyLevel.STANDARD,
        reason="Output passed safety postcheck.",
        issue_code="postcheck_allowed",
    )


def _draft_to_text(draft_answer: Any) -> str:
    if isinstance(draft_answer, str):
        return draft_answer
    return json.dumps(draft_answer, ensure_ascii=False, sort_keys=True)


def _decision(
    *,
    action: SafetyAction,
    level: SafetyLevel,
    reason: str,
    issue_code: str,
) -> SafetyDecision:
    return SafetyDecision(
        action=action,
        safety_level=level,
        reason=reason,
        issues=[
            SafetyIssue(
                code=issue_code,
                message=reason,
                severity=level,
            )
        ],
    )


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)
