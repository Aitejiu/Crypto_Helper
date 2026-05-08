from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="daily_market_report",
        workflow_name="Daily Market Report",
        visibility="public",
        required_inputs=[],
        safety_level="standard",
        allowed_agents=["manager-agent", "report-agent"],
        allowed_tools=[
            "crypto_helper_generate_daily_market_report",
            "crypto_helper_get_market_summary",
            "crypto_helper_query_news",
            "crypto_helper_query_opinions",
            "crypto_helper_security_review",
        ],
        output_schema={"type": "report_result"},
        fallback_behavior="return_market_snapshot_with_limitations",
        intent_aliases=["daily_market", "market_report", "today_market"],
    )
