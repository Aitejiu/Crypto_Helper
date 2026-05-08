from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="kol_persona",
        workflow_name="KOL Persona",
        visibility="public",
        required_inputs=["kol_query", "topic"],
        safety_level="guarded",
        allowed_agents=["manager-agent", "persona-runtime-agent"],
        allowed_tools=[
            "crypto_helper_registry_lookup",
            "crypto_helper_get_soul",
            "crypto_helper_get_profile",
            "crypto_helper_search_evidence",
            "crypto_helper_security_review",
        ],
        output_schema={"type": "persona_answer"},
        fallback_behavior="refuse_or_return_low_confidence_simulation",
        intent_aliases=["persona", "kol_view", "historical_simulation"],
    )
