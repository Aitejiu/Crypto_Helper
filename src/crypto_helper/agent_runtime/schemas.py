from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel
from crypto_helper.request_context import RequestContext


class WorkerExecutionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class QueueStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class DelegationTask(DomainModel):
    task_id: str
    created_at: datetime
    workflow_run_id: str
    workflow_id: str
    source_agent: str
    target_agent: str
    request_context: RequestContext
    inputs: dict[str, Any] = Field(default_factory=dict)
    suggested_tools: list[str] = Field(default_factory=list)
    priority: int = 100
    status: QueueStatus = QueueStatus.PENDING


class WorkerExecutionResult(DomainModel):
    task_id: str
    target_agent: str
    status: WorkerExecutionStatus
    output_payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    completed_at: datetime
    error: str | None = None
