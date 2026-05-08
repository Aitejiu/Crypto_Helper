from __future__ import annotations

from crypto_helper.models.common import DomainError
from crypto_helper.workflows.admin_import import build_workflow as build_admin_import_workflow
from crypto_helper.workflows.admin_promote_kols import (
    build_workflow as build_admin_promote_kols_workflow,
)
from crypto_helper.workflows.admin_refresh_profile import (
    build_workflow as build_admin_refresh_profile_workflow,
)
from crypto_helper.workflows.daily_market_report import (
    build_workflow as build_daily_market_report_workflow,
)
from crypto_helper.workflows.evidence_lookup import (
    build_workflow as build_evidence_lookup_workflow,
)
from crypto_helper.workflows.kol_lookup import build_workflow as build_kol_lookup_workflow
from crypto_helper.workflows.kol_persona import build_workflow as build_kol_persona_workflow
from crypto_helper.workflows.kol_report import build_workflow as build_kol_report_workflow
from crypto_helper.workflows.kol_stats import build_workflow as build_kol_stats_workflow
from crypto_helper.workflows.schemas import WorkflowDefinition
from crypto_helper.workflows.security_refusal import (
    build_workflow as build_security_refusal_workflow,
)


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        self._workflows[workflow.workflow_id] = workflow
        return workflow

    def get(self, workflow_id: str) -> WorkflowDefinition:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise DomainError(
                f"Workflow not found: {workflow_id}",
                code="WORKFLOW_NOT_FOUND",
                metadata={"workflow_id": workflow_id},
            )
        return workflow

    def list_public_workflows(self) -> list[WorkflowDefinition]:
        return [
            workflow for workflow in self._sorted_workflows() if workflow.visibility == "public"
        ]

    def list_admin_workflows(self) -> list[WorkflowDefinition]:
        return [workflow for workflow in self._sorted_workflows() if workflow.visibility == "admin"]

    def find(
        self,
        *,
        intent: str | None = None,
        workflow_id: str | None = None,
    ) -> WorkflowDefinition | None:
        if workflow_id is not None:
            return self._workflows.get(workflow_id)
        if intent is None:
            return None
        normalized_intent = intent.strip().lower()
        for workflow in self._sorted_workflows():
            if normalized_intent == workflow.workflow_id:
                return workflow
            if normalized_intent in {alias.lower() for alias in workflow.intent_aliases}:
                return workflow
        return None

    def load_default_workflows(self) -> None:
        for workflow in _default_workflows():
            self.register(workflow)

    def _sorted_workflows(self) -> list[WorkflowDefinition]:
        return sorted(self._workflows.values(), key=lambda workflow: workflow.workflow_id)


def _default_workflows() -> list[WorkflowDefinition]:
    return [
        build_kol_lookup_workflow(),
        build_kol_list_workflow(),
        build_kol_persona_workflow(),
        build_kol_report_workflow(),
        build_kol_stats_workflow(),
        build_evidence_lookup_workflow(),
        build_daily_market_report_workflow(),
        build_admin_import_workflow(),
        build_admin_refresh_profile_workflow(),
        build_admin_promote_kols_workflow(),
        build_security_refusal_workflow(),
    ]


def build_kol_list_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="kol_list",
        workflow_name="KOL List",
        visibility="public",
        required_inputs=[],
        safety_level="standard",
        allowed_agents=["manager-agent"],
        allowed_tools=["crypto_helper_registry_list", "crypto_helper_registry_get_active"],
        output_schema={"type": "registry_list_result"},
        fallback_behavior="return_active_kol_list",
        intent_aliases=["list_kols", "tracked_kols"],
    )
