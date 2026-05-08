from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="admin_promote_kols",
        workflow_name="Admin Promote KOLs",
        visibility="admin",
        public_callable=False,
        required_inputs=[],
        safety_level="admin_only",
        allowed_agents=["manager-admin"],
        allowed_tools=[],
        output_schema={"type": "promotion_summary"},
        fallback_behavior="require_private_admin_context",
        intent_aliases=["promote_kols", "admin_promote"],
        plan_steps=[
            "request_context",
            "safety_precheck",
            "workflow_guard",
            "tool_execution",
            "audit_log",
        ],
    )
