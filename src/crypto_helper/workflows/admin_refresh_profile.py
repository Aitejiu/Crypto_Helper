from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="admin_refresh_profile",
        workflow_name="Admin Refresh Profile",
        visibility="admin",
        required_inputs=["kol_query"],
        safety_level="admin_only",
        allowed_agents=["manager-admin"],
        allowed_tools=[
            "crypto_helper_registry_lookup",
            "crypto_helper_get_profile",
            "crypto_helper_query_trade_calls",
            "crypto_helper_query_events",
            "crypto_helper_query_opinions",
            "crypto_helper_search_evidence",
        ],
        output_schema={"type": "profile_refresh_result"},
        fallback_behavior="require_private_admin_context",
        intent_aliases=["refresh_profile", "admin_profile_refresh"],
    )
