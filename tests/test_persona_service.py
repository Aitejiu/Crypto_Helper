from __future__ import annotations

import pytest

from crypto_helper.core.persona_service import ask_persona
from crypto_helper.models.common import DomainError


def test_kol_a_answer_contains_disclaimer(runtime_data_dir: object) -> None:
    del runtime_data_dir
    answer = ask_persona("KOL_A", "If BTC breaks 62000, what might this KOL infer?")
    assert "历史画像" in answer.disclaimer


def test_kol_a_answer_contains_evidence_refs(runtime_data_dir: object) -> None:
    del runtime_data_dir
    answer = ask_persona("KOL_A", "If BTC breaks 62000, what might this KOL infer?")
    assert answer.evidence_refs


def test_kol_x_confidence_lower_than_kol_a(runtime_data_dir: object) -> None:
    del runtime_data_dir
    answer_a = ask_persona("KOL_A", "If BTC breaks 62000, what might this KOL infer?")
    answer_x = ask_persona("KOL_X", "If BTC breaks 62000, what might this KOL infer?")
    assert answer_x.confidence < answer_a.confidence


def test_kol_z_not_found_refused(runtime_data_dir: object) -> None:
    del runtime_data_dir
    with pytest.raises(DomainError):
        ask_persona("KOL_Z", "What about BTC?")


def test_kol_disabled_refused(runtime_data_dir: object) -> None:
    del runtime_data_dir
    with pytest.raises(DomainError):
        ask_persona("KOL_DISABLED", "What about BTC?")


def test_kol_old_archived_historical_answer_allowed_with_limitation(
    runtime_data_dir: object,
) -> None:
    del runtime_data_dir
    answer = ask_persona("KOL_OLD", "historical BTC style")
    assert any("archived" in limitation.lower() for limitation in answer.limitations)
