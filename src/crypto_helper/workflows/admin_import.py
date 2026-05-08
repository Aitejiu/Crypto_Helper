from __future__ import annotations

from crypto_helper.workflows.schemas import WorkflowDefinition


def build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="admin_import_pending",
        workflow_name="Admin Import Pending",
        visibility="admin",
        required_inputs=[],
        safety_level="admin_only",
        allowed_agents=["manager-admin"],
        allowed_tools=[],
        output_schema={"type": "import_summary"},
        fallback_behavior="require_private_admin_context",
        intent_aliases=["admin_import", "process_pending", "import_pending"],
    )
