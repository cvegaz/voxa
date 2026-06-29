"""Unit tests for the date_normalizer service."""

import pytest

from app.services.date_normalizer import is_date_type, normalize_date_value


class TestIsDateType:
    """Tests for detecting date-typed columns."""

    @pytest.mark.parametrize(
        "data_type",
        ["fecha", "fecha DD/MM/YYYY", "Fecha", "FECHA dd/mm/aaaa", "date", "Date (ISO)"],
    )
    def test_date_types_are_detected(self, data_type):
        assert is_date_type(data_type) is True

    @pytest.mark.parametrize(
        "data_type",
        ["texto", "número entero", "booleano", "number", ""],
    )
    def test_non_date_types_are_rejected(self, data_type):
        assert is_date_type(data_type) is False


class TestNormalizeDateValue:
    """Tests for reformatting date values to DD-mmm-YYYY."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("17/09/2026", "17-sep-2026"),
            ("17-09-2026", "17-sep-2026"),
            ("17.09.2026", "17-sep-2026"),
            ("2026-09-17", "17-sep-2026"),
            ("2026/09/17", "17-sep-2026"),
            ("5/1/2026", "05-ene-2026"),
            ("17/09/26", "17-sep-2026"),
        ],
    )
    def test_numeric_formats(self, value, expected):
        assert normalize_date_value(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("17 de septiembre de 2026", "17-sep-2026"),
            ("17 de sep del 2026", "17-sep-2026"),
            ("17 sep 2026", "17-sep-2026"),
            ("1 de enero de 2020", "01-ene-2020"),
            ("31 de diciembre de 1999", "31-dic-1999"),
        ],
    )
    def test_textual_spanish_formats(self, value, expected):
        assert normalize_date_value(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("17/09/2026 10:30", "17-sep-2026"),
            ("2026-09-17T10:30:00", "17-sep-2026"),
        ],
    )
    def test_time_component_is_dropped(self, value, expected):
        assert normalize_date_value(value) == expected

    def test_already_normalized_is_stable(self):
        # Idempotent: an already-formatted value is left as-is.
        assert normalize_date_value("17-sep-2026") == "17-sep-2026"

    @pytest.mark.parametrize("value", ["", "   "])
    def test_empty_returns_unchanged(self, value):
        assert normalize_date_value(value) == value

    @pytest.mark.parametrize(
        "value",
        ["no es una fecha", "Madrid", "42", "32/01/2026", "17 de foo de 2026"],
    )
    def test_unparseable_returns_unchanged(self, value):
        # Unrecognized or invalid dates are preserved verbatim, never corrupted.
        assert normalize_date_value(value) == value
