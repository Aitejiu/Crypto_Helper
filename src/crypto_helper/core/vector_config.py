from __future__ import annotations

import os
from dataclasses import dataclass

VECTOR_ENABLED_ENV = "CRYPTO_HELPER_VECTOR_ENABLED"
VECTOR_BACKEND_ENV = "CRYPTO_HELPER_VECTOR_BACKEND"
EMBEDDING_MODEL_ENV = "CRYPTO_HELPER_EMBEDDING_MODEL"

DEFAULT_VECTOR_BACKEND = "chroma"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"


@dataclass(frozen=True)
class VectorConfig:
    enabled: bool
    backend: str
    embedding_model: str


def load_vector_config() -> VectorConfig:
    return VectorConfig(
        enabled=_read_bool_env(VECTOR_ENABLED_ENV, default=False),
        backend=os.getenv(VECTOR_BACKEND_ENV, DEFAULT_VECTOR_BACKEND).strip()
        or DEFAULT_VECTOR_BACKEND,
        embedding_model=os.getenv(EMBEDDING_MODEL_ENV, DEFAULT_EMBEDDING_MODEL).strip()
        or DEFAULT_EMBEDDING_MODEL,
    )


def is_vector_enabled() -> bool:
    return load_vector_config().enabled


def get_vector_backend() -> str:
    return load_vector_config().backend


def get_embedding_model() -> str:
    return load_vector_config().embedding_model


def _read_bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default
