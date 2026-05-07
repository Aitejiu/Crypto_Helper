from __future__ import annotations

from typing import Any

from crypto_helper.models.security import SecurityAction, SecurityDecision


def review_text(text: str, context: dict[str, Any] | None = None) -> SecurityDecision:
    lowered = text.lower()
    ctx = context or {}
    if _contains_any(
        lowered,
        [
            "ignore previous",
            "ignore all rules",
            "忽略之前所有规则",
            "忽略所有规则",
            "prompt injection",
        ],
    ):
        return SecurityDecision(
            action=SecurityAction.DENY,
            risk_level="high",
            reason="Prompt injection or rule bypass attempt detected.",
            rewritten_safe_intent="Request a compliant historical analysis instead.",
            metadata={"category": "prompt_injection"},
        )
    if _contains_any(
        lowered,
        [
            "export private",
            "raw private",
            "私密频道原始消息",
            "导出原始消息",
            "private raw messages",
        ],
    ):
        return SecurityDecision(
            action=SecurityAction.DENY,
            risk_level="high",
            reason="Private raw message export is not allowed.",
            rewritten_safe_intent="Request a redacted summary of approved evidence instead.",
            metadata={"category": "private_export"},
        )
    if _contains_any(lowered, ["ignore permissions", "忽略权限", "bypass permissions", "绕过权限"]):
        return SecurityDecision(
            action=SecurityAction.DENY,
            risk_level="high",
            reason="Permission bypass requests are not allowed.",
            rewritten_safe_intent="Request a scoped summary using approved data sources.",
            metadata={"category": "permission_bypass"},
        )
    if _contains_any(
        lowered,
        ["i am kol_", "pretend to be", "impersonate", "我是 kol_", "我是kol_", "冒充"],
    ):
        return SecurityDecision(
            action=SecurityAction.DENY,
            risk_level="high",
            reason="Impersonation of a real KOL is not allowed.",
            rewritten_safe_intent=(
                "Request a profile-based simulation grounded in historical evidence."
            ),
            metadata={"category": "impersonation"},
        )
    if _contains_any(lowered, ["place order", "下单", "开多", "开空", "buy now", "sell now"]):
        return SecurityDecision(
            action=SecurityAction.DENY,
            risk_level="high",
            reason="Real trade execution is outside scope.",
            rewritten_safe_intent="Request a historical risk scenario summary instead.",
            metadata={"category": "trade_execution"},
        )
    if _contains_any(lowered, ["梭哈", "all in", "should i buy", "要不要买", "该不该买"]):
        return SecurityDecision(
            action=SecurityAction.REQUIRE_APPROVAL,
            risk_level="high",
            reason="Direct investment advice must be downgraded to historical risk analysis.",
            rewritten_safe_intent="Provide a historical risk summary and scenario analysis only.",
            metadata={"category": "financial_advice"},
        )
    if ctx.get("target_kol_exists") is False:
        return SecurityDecision(
            action=SecurityAction.DENY,
            risk_level="medium",
            reason="The requested KOL does not exist in the registry.",
            rewritten_safe_intent="Request analysis for a tracked KOL instead.",
            metadata={"category": "unknown_kol"},
        )
    return SecurityDecision(
        action=SecurityAction.ALLOW,
        risk_level="low",
        reason="Request is compatible with historical, profile-based analysis.",
        rewritten_safe_intent=None,
        metadata={"category": "allowed"},
    )


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)
