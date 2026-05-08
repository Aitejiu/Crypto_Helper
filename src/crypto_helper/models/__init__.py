from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from crypto_helper.models.common import DomainError
    from crypto_helper.models.evidence import (
        EvidenceRef,
        EvidenceSearchResult,
        KOLOpinion,
        MarketNews,
        TradeCall,
        TradeCallEvent,
    )
    from crypto_helper.models.persona import KOLProfile, PersonaAnswer
    from crypto_helper.models.registry import (
        KOLRegistry,
        KOLRegistryEntry,
        KOLStatus,
        KOLTier,
        PersonaMode,
    )
    from crypto_helper.models.report import ReportResult
    from crypto_helper.models.security import SecurityAction, SecurityDecision
    from crypto_helper.models.soul import KOLSoul, SoulPatch
    from crypto_helper.models.stats import KOLPerformance, KOLRankingItem, StatsResult

__all__ = [
    "DomainError",
    "EvidenceRef",
    "EvidenceSearchResult",
    "KOLOpinion",
    "KOLPerformance",
    "KOLProfile",
    "KOLRankingItem",
    "KOLRegistry",
    "KOLRegistryEntry",
    "KOLSoul",
    "KOLStatus",
    "KOLTier",
    "MarketNews",
    "PersonaAnswer",
    "PersonaMode",
    "ReportResult",
    "SecurityAction",
    "SecurityDecision",
    "SoulPatch",
    "StatsResult",
    "TradeCall",
    "TradeCallEvent",
]

_EXPORT_MAP = {
    "DomainError": ("crypto_helper.models.common", "DomainError"),
    "EvidenceRef": ("crypto_helper.models.evidence", "EvidenceRef"),
    "EvidenceSearchResult": ("crypto_helper.models.evidence", "EvidenceSearchResult"),
    "KOLOpinion": ("crypto_helper.models.evidence", "KOLOpinion"),
    "MarketNews": ("crypto_helper.models.evidence", "MarketNews"),
    "TradeCall": ("crypto_helper.models.evidence", "TradeCall"),
    "TradeCallEvent": ("crypto_helper.models.evidence", "TradeCallEvent"),
    "KOLProfile": ("crypto_helper.models.persona", "KOLProfile"),
    "PersonaAnswer": ("crypto_helper.models.persona", "PersonaAnswer"),
    "KOLRegistry": ("crypto_helper.models.registry", "KOLRegistry"),
    "KOLRegistryEntry": ("crypto_helper.models.registry", "KOLRegistryEntry"),
    "KOLStatus": ("crypto_helper.models.registry", "KOLStatus"),
    "KOLTier": ("crypto_helper.models.registry", "KOLTier"),
    "PersonaMode": ("crypto_helper.models.registry", "PersonaMode"),
    "ReportResult": ("crypto_helper.models.report", "ReportResult"),
    "SecurityAction": ("crypto_helper.models.security", "SecurityAction"),
    "SecurityDecision": ("crypto_helper.models.security", "SecurityDecision"),
    "KOLSoul": ("crypto_helper.models.soul", "KOLSoul"),
    "SoulPatch": ("crypto_helper.models.soul", "SoulPatch"),
    "KOLPerformance": ("crypto_helper.models.stats", "KOLPerformance"),
    "KOLRankingItem": ("crypto_helper.models.stats", "KOLRankingItem"),
    "StatsResult": ("crypto_helper.models.stats", "StatsResult"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    module = import_module(module_name)
    return getattr(module, attr_name)
