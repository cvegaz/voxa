"""Unit tests for PromptBuilder service."""

from datetime import date

import pytest

from app.models import ColumnDef, ColumnSchema
from app.services import PromptBuilder


@pytest.fixture
def builder():
    """Create a PromptBuilder instance."""
    return PromptBuilder()


@pytest.fixture
def single_column_schema():
    """Schema with a single column."""
    return ColumnSchema(
        columns=[
            ColumnDef(
                index=1,
                name="Nombre",
                data_type="texto",
                example_value="Juan Pérez",
            )
        ]
    )


@pytest.fixture
def multi_column_schema():
    """Schema with multiple columns."""
    return ColumnSchema(
        columns=[
            ColumnDef(
                index=1,
                name="Nombre",
                data_type="texto",
                example_value="Juan Pérez",
            ),
            ColumnDef(
                index=2,
                name="Edad",
                data_type="número entero",
                example_value="35",
            ),
            ColumnDef(
                index=3,
                name="Fecha de nacimiento",
                data_type="fecha DD/MM/YYYY",
                example_value="15/03/1989",
            ),
        ]
    )


class TestPromptBuilderBuild:
    """Tests for PromptBuilder.build() method."""

    def test_contains_system_intro(self, builder, single_column_schema):
        """The prompt starts with the system introduction."""
        prompt = builder.build(
            enriched_context="Contexto de prueba",
            schema=single_column_schema,
            transcribed_text="Hola mundo",
        )
        assert "Eres un asistente de extracción de datos" in prompt

    def test_contains_enriched_context(self, builder, single_column_schema):
        """The prompt includes the enriched context."""
        context = "Este es el contexto enriquecido de la sesión"
        prompt = builder.build(
            enriched_context=context,
            schema=single_column_schema,
            transcribed_text="Texto de prueba",
        )
        assert context in prompt

    def test_contains_transcribed_text(self, builder, single_column_schema):
        """The prompt includes the transcribed text."""
        text = "Mi nombre es Juan y tengo 35 años"
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text=text,
        )
        assert text in prompt

    def test_contains_all_column_names(self, builder, multi_column_schema):
        """The prompt includes all column names from the schema."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=multi_column_schema,
            transcribed_text="Texto",
        )
        for col in multi_column_schema.columns:
            assert col.name in prompt

    def test_contains_all_column_data_types(self, builder, multi_column_schema):
        """The prompt includes all column data types from the schema."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=multi_column_schema,
            transcribed_text="Texto",
        )
        for col in multi_column_schema.columns:
            assert col.data_type in prompt

    def test_contains_all_column_example_values(self, builder, multi_column_schema):
        """The prompt includes all column example values from the schema."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=multi_column_schema,
            transcribed_text="Texto",
        )
        for col in multi_column_schema.columns:
            assert col.example_value in prompt

    def test_schema_table_header_present(self, builder, single_column_schema):
        """The prompt includes the schema table header."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        assert "| # | Nombre | Tipo de dato | Ejemplo |" in prompt

    def test_schema_table_rows_indexed(self, builder, multi_column_schema):
        """Each column row in the schema table uses the column index."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=multi_column_schema,
            transcribed_text="Texto",
        )
        assert "| 1 | Nombre | texto | Juan Pérez |" in prompt
        assert "| 2 | Edad | número entero | 35 |" in prompt
        assert "| 3 | Fecha de nacimiento | fecha DD/MM/YYYY | 15/03/1989 |" in prompt

    def test_json_instructions_present(self, builder, single_column_schema):
        """The prompt includes JSON response instructions."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        assert "Responde ÚNICAMENTE con un JSON válido" in prompt

    def test_json_structure_contains_all_columns(self, builder, multi_column_schema):
        """The JSON example structure includes all column names."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=multi_column_schema,
            transcribed_text="Texto",
        )
        assert '"Nombre": "valor extraído"' in prompt
        assert '"Edad": "valor extraído"' in prompt
        assert '"Fecha de nacimiento": "valor extraído"' in prompt

    def test_contains_extraction_instructions(self, builder, single_column_schema):
        """The prompt includes key extraction instructions."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        assert "Identifica en el texto transcrito el valor correspondiente a CADA columna" in prompt
        assert 'usa un string vacío ""' in prompt
        assert "Respeta el tipo de dato indicado para cada columna" in prompt

    def test_distinguishes_absent_from_unmentioned(self, builder, single_column_schema):
        """The prompt instructs to use zero/absence (not empty) when the text
        explicitly states something is absent, vs. empty when not mentioned."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        # Not mentioned → empty string.
        assert 'Si la columna no se menciona en el texto, usa un string vacío ""' in prompt
        # Explicitly absent → zero/none value per data type.
        assert "no hay, no existe o es ninguno" in prompt
        assert '0 para números, "no" para booleanos' in prompt

    def test_contains_few_shot_examples(self, builder, single_column_schema):
        """The prompt includes few-shot examples demonstrating the
        absent-vs-unmentioned distinction (numeric 0 and boolean "no")."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        assert "Ejemplos ilustrativos" in prompt
        # Numeric absence → "0", unmentioned → "".
        assert '"CanchasTenis": "0"' in prompt
        assert '"Horario": ""' in prompt
        # Boolean absence → "no".
        assert '"Alberca": "no"' in prompt

    def test_injects_current_date_for_yearless_dates(self, builder, single_column_schema):
        """The prompt states the current date and tells the model to use the
        current year when a narrated date omits the year (so it does not invent
        one, e.g. defaulting to 2023)."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="La charla fue el 17 de septiembre",
            today=date(2026, 3, 15),
        )
        assert "La fecha actual es 15/03/2026" in prompt
        assert "usa el año actual (2026)" in prompt

    def test_english_prompt_when_language_en(self, builder, multi_column_schema):
        """With language='en' the prompt is built in English; default stays Spanish."""
        prompt = builder.build(
            enriched_context="Context",
            schema=multi_column_schema,
            transcribed_text="Text",
            today=date(2026, 3, 15),
            language="en",
        )
        assert "You are a data-extraction assistant" in prompt
        assert "| # | Name | Data type | Example |" in prompt
        assert '"extracted value"' in prompt
        assert "use the current year (2026)" in prompt
        # No Spanish scaffolding leaks into the English prompt.
        assert "asistente de extracción" not in prompt
        assert "valor extraído" not in prompt

    def test_defaults_to_spanish(self, builder, single_column_schema):
        """Omitting language keeps the Spanish prompt."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        assert "Eres un asistente de extracción de datos" in prompt

    def test_sections_separated_by_dividers(self, builder, single_column_schema):
        """The prompt sections are separated by standalone --- dividers."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        # Count standalone "---" lines (not part of table separators like |---|)
        standalone_dividers = [
            line for line in prompt.split("\n") if line.strip() == "---"
        ]
        assert len(standalone_dividers) == 3

    def test_transcribed_text_section_label(self, builder, single_column_schema):
        """The transcribed text section has its label."""
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        assert "Texto transcrito del audio:" in prompt

    def test_max_columns_schema(self, builder):
        """The prompt works correctly with the maximum number of columns (8)."""
        columns = [
            ColumnDef(
                index=i,
                name=f"Col{i}",
                data_type="texto",
                example_value=f"ejemplo{i}",
            )
            for i in range(1, 9)
        ]
        schema = ColumnSchema(columns=columns)
        prompt = builder.build(
            enriched_context="Contexto",
            schema=schema,
            transcribed_text="Texto largo de prueba",
        )
        for col in columns:
            assert col.name in prompt
            assert col.data_type in prompt
            assert col.example_value in prompt

    def test_returns_string(self, builder, single_column_schema):
        """The build method returns a string."""
        result = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text="Texto",
        )
        assert isinstance(result, str)

    def test_special_characters_in_text(self, builder, single_column_schema):
        """The prompt handles special characters in the transcribed text."""
        text = 'El precio es $1,500.00 y la fecha es "15/03/2024"'
        prompt = builder.build(
            enriched_context="Contexto",
            schema=single_column_schema,
            transcribed_text=text,
        )
        assert text in prompt
