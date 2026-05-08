from __future__ import annotations

import json
from pathlib import Path

from crypto_helper.core.data_loader import save_json_path
from crypto_helper.core.paths import ensure_runtime_data
from crypto_helper.models.registry import KOLRegistry
from crypto_helper.services.kol_resolver import resolve_kol


def test_resolve_kol_exact_match(runtime_data_dir: Path) -> None:
    del runtime_data_dir
    resolution = resolve_kol("KOL_A")
    assert resolution["status"] == "resolved"
    assert resolution["kol_id"] == "kol_a"


def test_resolve_kol_alias_match(runtime_data_dir: Path) -> None:
    del runtime_data_dir
    resolution = resolve_kol("AlphaTrend")
    assert resolution["status"] == "resolved"
    assert resolution["kol_id"] == "kol_a"


def test_resolve_kol_handle_match(runtime_data_dir: Path) -> None:
    runtime_dir = ensure_runtime_data()
    save_json_path(
        runtime_dir / "registry" / "platforms.json",
        {
            "platforms": {
                "kol_a": {
                    "telegram_handle": "@alpha_trend",
                }
            }
        },
    )

    resolution = resolve_kol("@alpha_trend", platform="telegram")

    assert resolution["status"] == "resolved"
    assert resolution["matched_by"] == "exact_telegram_handle"
    assert resolution["kol_id"] == "kol_a"


def test_resolve_kol_ambiguous(runtime_data_dir: Path) -> None:
    runtime_dir = ensure_runtime_data()
    registry_path = runtime_dir / "registry" / "kols.json"
    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    raw["kols"].append(
        {
            "kol_id": "kol_alpha_clone",
            "display_name": "Alpha Trend Clone",
            "aliases": ["AlphaClone"],
            "status": "active",
            "tier": "dynamic",
            "persona_mode": "runtime_only",
            "soul_path": "kols/kol_alpha_clone/soul.yaml",
            "profile_path": "kols/kol_alpha_clone/profile.json",
            "evidence_path": "kols/kol_alpha_clone/evidence.json",
            "allowed_symbols": ["BTC"],
            "risk_level": "unknown",
            "last_updated": "2026-05-08T00:00:00+00:00",
        }
    )
    registry_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    registry = KOLRegistry.model_validate(raw)

    resolution = resolve_kol("Alpha", registry=registry)

    assert resolution["status"] == "ambiguous"
    assert resolution["alternatives"]


def test_resolve_kol_not_found(runtime_data_dir: Path) -> None:
    del runtime_data_dir
    resolution = resolve_kol("NoSuchKol")
    assert resolution["status"] == "not_found"
    assert resolution["kol_id"] is None
