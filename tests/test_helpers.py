"""Tests for pure helper functions in sync_service.py."""

from datetime import datetime, timezone
from app.services.sync_service import _ms_to_dt, _flatten_readability, _flatten_complexity


class TestMsToDt:
    """Test epoch-ms → datetime conversion."""

    def test_zero_epoch(self):
        result = _ms_to_dt(0)
        assert result == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_known_timestamp(self):
        # 2024-01-01 00:00:00 UTC = 1704067200000 ms
        result = _ms_to_dt(1704067200000)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo == timezone.utc

    def test_preserves_millisecond_precision(self):
        result = _ms_to_dt(1704067200123)
        assert result.microsecond == 123000


class TestFlattenReadability:
    """Test readability dict flattening with optional prefix."""

    def test_none_input_returns_empty(self):
        assert _flatten_readability(None) == {}

    def test_empty_dict_returns_empty(self):
        assert _flatten_readability({}) == {}

    def test_without_prefix(self):
        r = {
            "version": 1,
            "sampleTextLength": 500,
            "sentenceCount": 10,
            "wordCount": 80,
            "fleschReadingEase": 65.2,
            "fleschKincaidGrade": 8.1,
            "smogIndex": 9.0,
            "colemanLiauIndex": 10.5,
            "automatedReadabilityIndex": 7.3,
            "gunningFog": 11.2,
            "daleChallReadabilityScore": 6.8,
            "lix": 42.0,
            "rix": 3.5,
            "textStandard": "8th and 9th grade",
            "textMedian": 8.5,
        }
        result = _flatten_readability(r)
        assert result["readability_version"] == 1
        assert result["sample_text_length"] == 500
        assert result["flesch_reading_ease"] == 65.2
        assert result["text_standard"] == "8th and 9th grade"
        assert result["text_median"] == 8.5

    def test_with_prefix(self):
        r = {"version": 1, "wordCount": 50, "fleschReadingEase": 70.0}
        result = _flatten_readability(r, "resp_")
        assert "resp_readability_version" in result
        assert result["resp_readability_version"] == 1
        assert result["resp_word_count"] == 50
        assert result["resp_flesch_reading_ease"] == 70.0

    def test_missing_keys_return_none(self):
        r = {"version": 1}
        result = _flatten_readability(r)
        assert result["readability_version"] == 1
        assert result["word_count"] is None
        assert result["flesch_reading_ease"] is None


class TestFlattenComplexity:
    """Test complexity dict flattening with optional prefix."""

    def test_none_input_returns_empty(self):
        assert _flatten_complexity(None) == {}

    def test_empty_dict_returns_empty(self):
        assert _flatten_complexity({}) == {}

    def test_without_prefix(self):
        c = {
            "gradeConsensus": 8.5,
            "complexityBand": "moderate",
            "reasonCodes": ["high-fog", "low-flesch-ease"],
        }
        result = _flatten_complexity(c)
        assert result["grade_consensus"] == 8.5
        assert result["complexity_band"] == "moderate"
        assert result["reason_codes"] == "high-fog,low-flesch-ease"

    def test_with_prefix(self):
        c = {"gradeConsensus": 5.0, "complexityBand": "easy"}
        result = _flatten_complexity(c, "resp_")
        assert result["resp_grade_consensus"] == 5.0
        assert result["resp_complexity_band"] == "easy"

    def test_reason_codes_none(self):
        c = {"gradeConsensus": 3.0, "complexityBand": "very-easy"}
        result = _flatten_complexity(c)
        assert result["reason_codes"] is None

    def test_reason_codes_string(self):
        c = {"gradeConsensus": 12.0, "complexityBand": "hard", "reasonCodes": "high-fog"}
        result = _flatten_complexity(c)
        assert result["reason_codes"] == "high-fog"
