from __future__ import annotations

from typing import Any, Literal

from crypto_helper.models.common import DomainModel
from crypto_helper.request_context import RequestContext

WorkflowVisibility = Literal["public", "admin"]


class WorkflowDefinition(DomainModel):
    workflow_id: str
    workflow_name: str
    visibility: WorkflowVisibility
    public_callable: bool = True
    required_inputs: list[str]
    safety_level: str
    allowed_agents: list[str]
    allowed_tools: list[str]
    output_schema: dict[str, Any]
    fallback_behavior: str
    intent_aliases: list[str] = []
    plan_steps: list[str] = []


class WorkflowExecutionPlan(DomainModel):
    workflow_id: str
    workflow_name: str
    request_context: RequestContext
    validated_inputs: dict[str, Any]
    allowed_agents: list[str]
    allowed_tools: list[str]
    output_schema: dict[str, Any]
    fallback_behavior: str
    safety_level: str
    plan_steps: list[str]
