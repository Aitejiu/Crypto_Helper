from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="admin_archive_kol",
        workflow_name="Admin Archive KOL",
        visibility="admin",
        public_callable=False,
        required_inputs=["kol_query"],
        safety_level="admin_only",
        allowed_agents=["manager-admin"],
        allowed_tools=["crypto_helper_registry_lookup", "crypto_helper_registry_archive_mock"],
        output_schema={"type": "registry_mutation_result"},
        fallback_behavior="require_private_admin_context",
        intent_aliases=["archive_kol", "admin_archive"],
        plan_steps=[
            "request_context",
            "safety_precheck",
            "kol_resolver",
            "workflow_guard",
            "tool_execution",
            "audit_log",
        ],
    )
