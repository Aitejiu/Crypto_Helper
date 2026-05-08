from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from crypto_helper.services.audit_service import write_audit_event
    from crypto_helper.services.kol_resolver import resolve_kol
    from crypto_helper.services.manager_agent_flow import handle_manager_request
    from crypto_helper.services.workflow_run_service import start_workflow_run

__all__ = [
    "resolve_kol",
    "handle_manager_request",
    "start_workflow_run",
    "write_audit_event",
]

_EXPORT_MAP = {
    "resolve_kol": ("crypto_helper.services.kol_resolver", "resolve_kol"),
    "handle_manager_request": (
        "crypto_helper.services.manager_agent_flow",
        "handle_manager_request",
    ),
    "start_workflow_run": (
        "crypto_helper.services.workflow_run_service",
        "start_workflow_run",
    ),
    "write_audit_event": ("crypto_helper.services.audit_service", "write_audit_event"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    module = import_module(module_name)
    return getattr(module, attr_name)
