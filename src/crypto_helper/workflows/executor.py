from __future__ import annotations

from typing import Any

from crypto_helper.models.common import DomainError
from crypto_helper.request_context import RequestContext
from crypto_helper.workflows.registry import WorkflowRegistry
from crypto_helper.workflows.schemas import WorkflowExecutionPlan


class WorkflowExecutor:
    def __init__(self, registry: WorkflowRegistry) -> None:
        self.registry = registry

    def build_plan(
        self,
        request_context: RequestContext,
        workflow_id: str,
        inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecutionPlan:
        workflow = self.registry.get(workflow_id)
        payload = inputs or {}
        missing = [field for field in workflow.required_inputs if field not in payload]
        if missing:
            raise DomainError(
                f"Missing required workflow inputs: {', '.join(missing)}",
                code="WORKFLOW_MISSING_INPUTS",
                metadata={"workflow_id": workflow_id, "missing_inputs": missing},
            )
        validated_inputs = {
            field: payload[field] for field in workflow.required_inputs if field in payload
        }
        extra_inputs = {key: value for key, value in payload.items() if key not in validated_inputs}
        if extra_inputs:
            validated_inputs.update(extra_inputs)
        return WorkflowExecutionPlan(
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.workflow_name,
            request_context=request_context,
            validated_inputs=validated_inputs,
            allowed_agents=workflow.allowed_agents,
            allowed_tools=workflow.allowed_tools,
            output_schema=workflow.output_schema,
            fallback_behavior=workflow.fallback_behavior,
            safety_level=workflow.safety_level,
        )
