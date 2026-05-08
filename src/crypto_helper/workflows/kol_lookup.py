from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="kol_lookup",
        workflow_name="KOL Lookup",
        visibility="public",
        required_inputs=["kol_query"],
        safety_level="standard",
        allowed_agents=["manager-agent"],
        allowed_tools=["crypto_helper_registry_lookup"],
        output_schema={"type": "kol_lookup_result"},
        fallback_behavior="return_not_found_or_suggestions",
        intent_aliases=["lookup", "find_kol", "resolve_kol"],
    )
