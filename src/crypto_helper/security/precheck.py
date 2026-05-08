from __future__ import annotations

from crypto_helper.request_context import RequestContext
from crypto_helper.security.policies import (
    ADMIN_ONLY_PHRASES,
    FABRICATED_EVIDENCE_PHRASES,
    IMPERSONATION_PHRASES,
    INVESTMENT_ADVICE_PHRASES,
    PRIVATE_EXPORT_PHRASES,
)
from crypto_helper.security.schemas import (
    SafetyAction,
    SafetyDecision,
    SafetyIssue,
    SafetyLevel,
)
from crypto_helper.services.audit_service import write_security_audit


def safety_precheck(request_context: RequestContext, user_message: str) -> SafetyDecision:
    lowered = user_message.lower()
    if _contains_any(lowered, PRIVATE_EXPORT_PHRASES):
        return _decision(
            action=SafetyAction.REFUSE,
            level=SafetyLevel.HIGH_RISK,
            reason="Private raw message export is not allowed.",
            issue_code="private_export",
        )
    if _contains_any(lowered, FABRICATED_EVIDENCE_PHRASES):
        return _decision(
            action=SafetyAction.REFUSE,
            level=SafetyLevel.HIGH_RISK,
            reason="Fabricating evidence or sources is not allowed.",
            issue_code="fabricated_evidence",
        )
    if _contains_any(lowered, IMPERSONATION_PHRASES):
        return _decision(
            action=SafetyAction.REFUSE,
            level=SafetyLevel.HIGH_RISK,
            reason="Impersonating a real KOL is not allowed.",
            issue_code="impersonation",
        )
    if _contains_any(lowered, ADMIN_ONLY_PHRASES):
        if request_context.is_admin_context:
            return _decision(
                action=SafetyAction.ALLOW,
                level=SafetyLevel.ADMIN_ONLY,
                reason="Admin-only request is allowed in admin context.",
                issue_code="admin_allowed",
            )
        decision = _decision(
            action=SafetyAction.REQUIRE_ADMIN,
            level=SafetyLevel.ADMIN_ONLY,
            reason="This workflow requires a private admin context.",
            issue_code="admin_only",
        )
        _record_security_block(request_context, "admin_only_request_blocked", decision)
        return decision
    if _contains_any(lowered, INVESTMENT_ADVICE_PHRASES):
        return _decision(
            action=SafetyAction.DOWNGRADE,
            level=SafetyLevel.HIGH_RISK,
            reason="Direct investment advice must be downgraded to historical risk analysis.",
            issue_code="investment_advice",
        )
    return _decision(
        action=SafetyAction.ALLOW,
        level=SafetyLevel.STANDARD,
        reason="Request passed safety precheck.",
        issue_code="allowed",
    )


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


def _record_security_block(
    request_context: RequestContext,
    event_type: str,
    decision: SafetyDecision,
) -> None:
    write_security_audit(
        event_type=event_type,
        actor="system",
        target_type="workflow_request",
        target_id=event_type,
        action=decision.action.value,
        request_context=request_context,
        after=decision.model_dump(mode="json"),
        status="blocked",
        error=decision.reason,
    )
