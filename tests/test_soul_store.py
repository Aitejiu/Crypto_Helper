from __future__ import annotations

from datetime import datetime

import pytest

from crypto_helper.core.data_loader import append_jsonl
from crypto_helper.core.soul_store import apply_soul_patch_mock, generate_soul_patch_mock, get_soul
from crypto_helper.models.common import DomainError
from crypto_helper.models.soul import SoulPatch


def test_get_kol_a_soul(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = get_soul("KOL_A")
    assert payload["soul"].kol_id == "kol_a"


def test_get_kol_x_soul(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = get_soul("KOL_X")
    assert payload["soul"].kol_id == "kol_x"


def test_generate_patch(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = generate_soul_patch_mock(
        "KOL_A", "recent evidence shows more move SL to breakeven behavior"
    )
    assert payload["patch"].patch_id.startswith("patch_")


def test_low_confidence_patch_requires_review(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = generate_soul_patch_mock("KOL_A", "maybe changed")
    assert payload["patch"].requires_review is True


def test_invalid_identity_patch_rejected(runtime_data_dir: object) -> None:
    del runtime_data_dir
    patch = SoulPatch(
        patch_id="patch_bad_identity",
        kol_id="kol_a",
        observed_behavior="malicious",
        summary="bad patch",
        confidence=0.9,
        requires_review=False,
        identity_boundary_updates={"must_not_claim_real_identity": False},
        created_at=datetime.fromisoformat("2026-05-07T00:00:00+00:00"),
    )
    append_jsonl(
        "audit/soul_patches.jsonl",
        {
            "event": "generated",
            "timestamp": "2026-05-07T00:00:00+00:00",
            "kol_id": "kol_a",
            "patch": patch.model_dump(mode="json"),
            "mock_only": True,
        },
    )
    with pytest.raises(DomainError):
        apply_soul_patch_mock("KOL_A", "patch_bad_identity")
