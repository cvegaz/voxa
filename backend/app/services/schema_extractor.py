"""Schema extraction service.

Extracts column schema from an already-validated Excel workbook:
- Row 1 = column names (Nombre_Columna)
- Row 2 = data types (Tipo_Dato)
- Row 3 = example values (Ejemplo_Valor)

Only columns with a non-empty name in row 1 are included.
"""

from openpyxl import Workbook

from app.models import ColumnDef, ColumnSchema


class SchemaExtractor:
    """Extracts column schema from the first 3 rows of an Excel workbook."""

    def extract(self, workbook: Workbook) -> ColumnSchema:
        """Read rows 1-3 and build the column schema.

        The workbook is assumed to have already passed validation
        (via ExcelValidator), so rows 1-3 are structurally complete.

        Args:
            workbook: An openpyxl Workbook already loaded and validated.

        Returns:
            ColumnSchema containing the list of ColumnDef entries.
        """
        sheet = workbook.active
        columns: list[ColumnDef] = []

        for cell in sheet[1]:
            name_value = cell.value
            if name_value is None or str(name_value).strip() == "":
                continue

            col_idx = cell.column
            data_type = sheet.cell(row=2, column=col_idx).value
            example_value = sheet.cell(row=3, column=col_idx).value

            columns.append(
                ColumnDef(
                    index=col_idx,
                    name=str(name_value).strip(),
                    data_type=str(data_type).strip() if data_type is not None else "",
                    example_value=str(example_value).strip() if example_value is not None else "",
                )
            )

        return ColumnSchema(columns=columns)
