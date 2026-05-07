from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class DomainError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.metadata = metadata or {}

    def to_response(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": self.message,
            "code": self.code,
            "metadata": to_jsonable(self.metadata),
        }


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return TypeAdapter(Any).dump_python(value, mode="json")


def ok_response(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        payload = {key: to_jsonable(value) for key, value in data.items()}
    else:
        payload = {"result": to_jsonable(data)}
    payload["ok"] = True
    return payload
