"""Excel exporter service.

Builds a fresh ``.xlsx`` in memory from the column schema and the captured
records (ADR-0013, option B): row 1 holds the column names, rows 2+ hold the
data. The uploaded template's scaffolding rows — ``Tipo_Dato`` (row 2) and
``Ejemplo_Valor`` (row 3) — and any formatting are deliberately NOT reproduced;
the final file contains only the header and the real captured rows.
"""

from io import BytesIO

from openpyxl import Workbook

from app.models import ColumnSchema


class ExcelExporter:
    """Reconstructs the downloadable ``.xlsx`` from schema + records, in memory."""

    def build(self, schema: ColumnSchema, records: list[dict]) -> bytes:
        """Build the workbook and return its bytes.

        Args:
            schema: Column schema; defines the header names and column order.
            records: The captured rows as ``{column_name: value}`` dicts
                (``record_json`` shape), already ordered.

        Returns:
            The ``.xlsx`` file contents as bytes.
        """
        workbook = Workbook()
        sheet = workbook.active

        column_names = [col.name for col in schema.columns]

        # Row 1: the only header row — column names, nothing else.
        sheet.append(column_names)

        # Rows 2+: one row per record, values in schema column order. A column
        # missing from a record (or null) becomes an empty cell.
        for record in records:
            sheet.append(
                ["" if record.get(name) is None else record.get(name) for name in column_names]
            )

        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()
