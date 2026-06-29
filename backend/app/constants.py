"""Cross-layer constants for the capture/extraction flow (ADR-0013)."""

# A capture session is a short burst: the user narrates a handful of rows and
# downloads the result. After this many records the session auto-finalizes and
# accepts no more extractions.
MAX_ROWS_PER_SESSION = 5

# Row of the first data record in the exported sheet. The export reconstructs the
# .xlsx from the schema with a single header row of column names on row 1, so the
# first data record lands on row 2.
FIRST_DATA_ROW = 2

# Allowed length of a single audio recording, in seconds. This is the current
# (free) tier cap; a future paid tier can raise the maximum (see todo.md). The
# limit is enforced both client-side (auto-stop in the recorder) and server-side
# (AudioValidator) so an uploaded file cannot bypass it.
MIN_AUDIO_DURATION_SECONDS = 1.0
MAX_AUDIO_DURATION_SECONDS = 20.0
