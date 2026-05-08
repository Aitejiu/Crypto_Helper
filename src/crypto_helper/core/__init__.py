from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from crypto_helper.core import (
        data_loader,
        evidence_store,
        paths,
        persona_service,
        profile_service,
        registry_service,
        report_service,
        security_review,
        soul_store,
        stats_service,
        vector_config,
    )

__all__ = [
    "data_loader",
    "evidence_store",
    "paths",
    "persona_service",
    "profile_service",
    "registry_service",
    "report_service",
    "security_review",
    "soul_store",
    "stats_service",
    "vector_config",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    return import_module(f"crypto_helper.core.{name}")
