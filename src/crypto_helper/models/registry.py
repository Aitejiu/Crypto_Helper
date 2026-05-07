from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from crypto_helper.models.common import DomainModel


class KOLStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class KOLTier(StrEnum):
    CORE = "core"
    DYNAMIC = "dynamic"


class PersonaMode(StrEnum):
    DEDICATED_OR_RUNTIME = "dedicated_or_runtime"
    RUNTIME_ONLY = "runtime_only"


class KOLRegistryEntry(DomainModel):
    kol_id: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    status: KOLStatus
    tier: KOLTier
    persona_mode: PersonaMode
    soul_path: str
    profile_path: str
    evidence_path: str
    allowed_symbols: list[str] = Field(default_factory=list)
    risk_level: str
    last_updated: datetime


class KOLRegistry(DomainModel):
    kols: list[KOLRegistryEntry] = Field(default_factory=list)
