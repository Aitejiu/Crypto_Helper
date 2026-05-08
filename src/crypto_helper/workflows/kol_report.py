from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="kol_report",
        workflow_name="KOL Report",
        visibility="public",
        public_callable=True,
        required_inputs=["kol_query"],
        safety_level="guarded",
        allowed_agents=["manager-agent", "report-agent"],
        allowed_tools=[
            "crypto_helper_registry_lookup",
            "crypto_helper_generate_report",
            "crypto_helper_query_trade_calls",
            "crypto_helper_query_events",
            "crypto_helper_query_opinions",
            "crypto_helper_search_evidence",
            "crypto_helper_security_review",
        ],
        output_schema={"type": "report_result"},
        fallback_behavior="return_report_with_limitations",
        intent_aliases=["report", "weekly_report", "kol_summary"],
        plan_steps=[
            "request_context",
            "safety_precheck",
            "kol_resolver",
            "workflow_guard",
            "tool_execution",
            "output_safety_postcheck",
        ],
    )
