"""DataFrame conversion service.

Converts an openpyxl Workbook into a pandas DataFrame using
the extracted ColumnSchema:
- Row 1 = column names (used as DataFrame headers)
- Rows 2-3 = metadata (type/example) — skipped
- Data starts from row 4 onwards
- Only columns present in the schema are included
"""

import pandas as pd
from openpyxl import Workbook

from app.models.template_models import ColumnSchema


class DataFrameConverter:
    """Converts Excel workbook content to a pandas DataFrame."""

    DATA_START_ROW = 4

    def convert(self, workbook: Workbook, schema: ColumnSchema) -> pd.DataFrame:
        """Convert the Excel workbook to a DataFrame using the extracted schema.

        Uses column names from the schema as DataFrame headers.
        Data is read starting from row 4 (rows 2-3 are metadata).
        Only columns defined in the schema are included.

        Args:
            workbook: An openpyxl Workbook loaded from the uploaded file.
            schema: The ColumnSchema extracted from the template header rows.

        Returns:
            A pandas DataFrame with schema column names as headers and
            data rows starting from row 4.
        """
        sheet = workbook.active

        # Build column index → name mapping from the schema
        col_indices = [col.index for col in schema.columns]
        col_names = [col.name for col in schema.columns]

        # Extract data rows starting from row 4
        rows: list[list] = []
        for row in sheet.iter_rows(min_row=self.DATA_START_ROW, values_only=False):
            row_data = []
            for col_idx in col_indices:
                cell = row[col_idx - 1]  # openpyxl is 1-indexed, list is 0-indexed
                row_data.append(cell.value)
            rows.append(row_data)

        # Filter out completely empty rows (all values are None)
        rows = [r for r in rows if any(v is not None for v in r)]

        return pd.DataFrame(rows, columns=col_names)
