"""Base Pydantic model that bridges Python snake_case and JSON camelCase.

The frontend (TypeScript) speaks camelCase; Python is idiomatic in snake_case.
Instead of renaming fields, we translate only at the API boundary:

- ``alias_generator=to_camel``: every field gets a camelCase alias. FastAPI
  serializes responses by alias by default, so JSON comes out camelCase.
- ``populate_by_name=True``: models can still be built with snake_case field
  names in Python, and request bodies are accepted in BOTH camelCase (alias)
  and snake_case (field name). This keeps existing internal code working.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """API-facing base model: snake_case in Python, camelCase in JSON."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
