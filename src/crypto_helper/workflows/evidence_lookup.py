from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="evidence_lookup",
        workflow_name="Evidence Lookup",
        visibility="public",
        public_callable=True,
        required_inputs=["kol_query"],
        safety_level="standard",
        allowed_agents=["manager-agent", "persona-runtime-agent", "report-agent"],
        allowed_tools=[
            "crypto_helper_registry_lookup",
            "crypto_helper_search_evidence",
            "crypto_helper_query_trade_calls",
            "crypto_helper_query_events",
            "crypto_helper_query_opinions",
            "crypto_helper_query_news",
        ],
        output_schema={"type": "evidence_search_result"},
        fallback_behavior="return_evidence_limitations",
        intent_aliases=["evidence", "why", "supporting_data"],
        plan_steps=[
            "request_context",
            "safety_precheck",
            "kol_resolver",
            "workflow_guard",
            "tool_execution",
            "output_safety_postcheck",
        ],
    )
