"""Tests for confidence scoring and cache."""

import tempfile
from pathlib import Path

import pytest

from schemas import ConfidenceScore
from cache import get_cached, set_cached, DB_PATH


def test_confidence_score_valid():
    c = ConfidenceScore(
        overall_score=85,
        source_reliability=80,
        evidence_coverage=90,
        consistency=85,
        high_confidence_insights=["Strong competitor data"],
        low_confidence_insights=["COGS estimate uncertain"],
        summary="Generally reliable.",
    )
    assert c.overall_score == 85


def test_confidence_score_bounds():
    with pytest.raises(Exception):
        ConfidenceScore(
            overall_score=101,
            source_reliability=80,
            evidence_coverage=90,
            consistency=85,
        )


def test_cache_hit_miss(monkeypatch, tmp_path):
    monkeypatch.setattr("cache.DB_PATH", tmp_path / "test.db")
    assert get_cached("coffee cup") is None
    set_cached("coffee cup", {"score": 90})
    assert get_cached("coffee cup")["score"] == 90
    assert get_cached("ceramic mug") is None  # different query -> exact-hash miss
