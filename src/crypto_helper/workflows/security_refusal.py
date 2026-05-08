from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="security_refusal",
        workflow_name="Security Refusal",
        visibility="public",
        required_inputs=["user_message"],
        safety_level="high_risk",
        allowed_agents=["manager-agent", "security-agent"],
        allowed_tools=["crypto_helper_security_review"],
        output_schema={"type": "security_decision"},
        fallback_behavior="return_safe_alternative",
        intent_aliases=["security", "refusal", "unsafe_request"],
    )
