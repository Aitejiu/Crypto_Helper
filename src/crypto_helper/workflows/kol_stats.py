from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="kol_stats",
        workflow_name="KOL Stats",
        visibility="public",
        required_inputs=["kol_query"],
        safety_level="standard",
        allowed_agents=["manager-agent", "report-agent"],
        allowed_tools=[
            "crypto_helper_registry_lookup",
            "crypto_helper_get_kol_performance",
            "crypto_helper_get_active_symbols",
            "crypto_helper_compare_kols",
        ],
        output_schema={"type": "stats_result"},
        fallback_behavior="return_historical_stats_only",
        intent_aliases=["stats", "performance", "compare"],
    )
