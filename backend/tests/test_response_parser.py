"""Unit tests for the ResponseParser service."""

import json

import pytest

from app.models import ColumnDef, ColumnSchema
from app.services.exceptions import LLMInvalidResponseError
from app.services.response_parser import ResponseParser


@pytest.fixture
def parser():
    """Create a ResponseParser instance."""
    return ResponseParser()


@pytest.fixture
def sample_schema():
    """Create a sample ColumnSchema with 3 columns."""
    return ColumnSchema(
        columns=[
            ColumnDef(index=1, name="Nombre", data_type="texto", example_value="Juan Pérez"),
            ColumnDef(index=2, name="Edad", data_type="número entero", example_value="30"),
            ColumnDef(index=3, name="Ciudad", data_type="texto", example_value="Madrid"),
        ]
    )


class TestValidJSON:
    """Tests for valid JSON responses with all expected keys."""

    def test_parse_all_keys_present(self, parser, sample_schema):
        """All keys matching schema columns are correctly parsed."""
        raw = json.dumps({"Nombre": "Ana", "Edad": "25", "Ciudad": "Barcelona"})
        result = parser.parse(raw, sample_schema)

        assert result == {"Nombre": "Ana", "Edad": "25", "Ciudad": "Barcelona"}

    def test_parse_returns_string_values(self, parser, sample_schema):
        """Numeric values are converted to strings."""
        raw = json.dumps({"Nombre": "Pedro", "Edad": 42, "Ciudad": "Lima"})
        result = parser.parse(raw, sample_schema)

        assert result["Edad"] == "42"
        assert isinstance(result["Edad"], str)

    def test_parse_preserves_all_schema_columns(self, parser, sample_schema):
        """Result has exactly the same keys as the schema columns."""
        raw = json.dumps({"Nombre": "Ana", "Edad": "25", "Ciudad": "Barcelona"})
        result = parser.parse(raw, sample_schema)

        expected_keys = {"Nombre", "Edad", "Ciudad"}
        assert set(result.keys()) == expected_keys


class TestMissingKeys:
    """Tests for JSON responses with missing keys."""

    def test_missing_key_gets_empty_string(self, parser, sample_schema):
        """Missing keys are assigned empty strings."""
        raw = json.dumps({"Nombre": "Ana", "Ciudad": "Barcelona"})
        result = parser.parse(raw, sample_schema)

        assert result["Edad"] == ""

    def test_multiple_missing_keys(self, parser, sample_schema):
        """Multiple missing keys each get empty strings."""
        raw = json.dumps({"Nombre": "Ana"})
        result = parser.parse(raw, sample_schema)

        assert result["Nombre"] == "Ana"
        assert result["Edad"] == ""
        assert result["Ciudad"] == ""


class TestNullValues:
    """Tests for JSON responses with null values."""

    def test_null_value_gets_empty_string(self, parser, sample_schema):
        """Null values are replaced with empty strings."""
        raw = json.dumps({"Nombre": "Ana", "Edad": None, "Ciudad": "Barcelona"})
        result = parser.parse(raw, sample_schema)

        assert result["Edad"] == ""

    def test_multiple_null_values(self, parser, sample_schema):
        """Multiple null values all become empty strings."""
        raw = json.dumps({"Nombre": None, "Edad": None, "Ciudad": None})
        result = parser.parse(raw, sample_schema)

        assert result == {"Nombre": "", "Edad": "", "Ciudad": ""}


class TestExtraKeys:
    """Tests for JSON responses with extra keys not in schema."""

    def test_extra_keys_are_discarded(self, parser, sample_schema):
        """Extra keys not in the schema are ignored."""
        raw = json.dumps({
            "Nombre": "Ana",
            "Edad": "25",
            "Ciudad": "Barcelona",
            "extra_field": "should be ignored",
            "another_extra": 123,
        })
        result = parser.parse(raw, sample_schema)

        assert "extra_field" not in result
        assert "another_extra" not in result
        assert len(result) == 3

    def test_only_extra_keys_returns_all_empty(self, parser, sample_schema):
        """If response only has extra keys, all schema columns get empty strings."""
        raw = json.dumps({"unknown_field": "value", "other": "data"})
        result = parser.parse(raw, sample_schema)

        assert result == {"Nombre": "", "Edad": "", "Ciudad": ""}


class TestInvalidJSON:
    """Tests for responses that are not valid JSON."""

    def test_invalid_json_raises_error(self, parser, sample_schema):
        """Non-JSON string raises LLMInvalidResponseError."""
        with pytest.raises(LLMInvalidResponseError):
            parser.parse("this is not json", sample_schema)

    def test_incomplete_json_raises_error(self, parser, sample_schema):
        """Incomplete JSON raises LLMInvalidResponseError."""
        with pytest.raises(LLMInvalidResponseError):
            parser.parse('{"Nombre": "Ana"', sample_schema)

    def test_empty_string_raises_error(self, parser, sample_schema):
        """Empty string raises LLMInvalidResponseError."""
        with pytest.raises(LLMInvalidResponseError):
            parser.parse("", sample_schema)

    def test_json_array_raises_error(self, parser, sample_schema):
        """JSON array (not object) raises LLMInvalidResponseError."""
        with pytest.raises(LLMInvalidResponseError):
            parser.parse('["Nombre", "Edad"]', sample_schema)

    def test_json_string_raises_error(self, parser, sample_schema):
        """JSON string (not object) raises LLMInvalidResponseError."""
        with pytest.raises(LLMInvalidResponseError):
            parser.parse('"just a string"', sample_schema)


class TestEmptyJSONObject:
    """Tests for empty JSON object responses."""

    def test_empty_object_returns_all_empty_strings(self, parser, sample_schema):
        """Empty JSON object produces dict with empty strings for all columns."""
        raw = json.dumps({})
        result = parser.parse(raw, sample_schema)

        assert result == {"Nombre": "", "Edad": "", "Ciudad": ""}
        assert len(result) == 3

    def test_empty_object_single_column_schema(self, parser):
        """Empty JSON with single column schema returns one empty string."""
        schema = ColumnSchema(
            columns=[
                ColumnDef(index=1, name="Campo", data_type="texto", example_value="ejemplo"),
            ]
        )
        raw = json.dumps({})
        result = parser.parse(raw, schema)

        assert result == {"Campo": ""}
