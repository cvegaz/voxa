"""Database migration runner.

Applies, in order, the .sql files in the ``migrations/`` folder that have not
yet been applied, and keeps a record of which ones have already run in a
``schema_migrations`` table.

Why keep a record? Because this project's migrations are NOT idempotent: for
example, ``003`` runs ``ALTER TABLE ... ADD COLUMN`` and several
``CREATE INDEX`` statements without ``IF NOT EXISTS``. Running them again would
fail. By recording each applied file, later startups simply skip the ones that
already ran. This way the container can start as many times as it wants without
breaking the database.

It runs automatically when the backend container starts (see the service's
``command`` in docker-compose.yml), right before uvicorn.
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# Load backend/.env the same way the app does. The app gets this for free from
# app/__init__.py, but this script deliberately does NOT import the app package
# (it must be able to run before the app is importable), so it loads the file
# itself. load_dotenv does not override variables that are already set, so the
# values injected by Docker Compose still win inside the container.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# Same variable the app uses (app/database.py). In Docker it will point to the
# "db" service, not localhost.
DATABASE_URL = os.getenv("DATABASE_URL")

# scripts/migrate.py -> parent = scripts/ -> parent.parent = backend root
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def connect_with_retry(retries: int = 15, delay: float = 2.0) -> asyncpg.Connection:
    """Postgres can take a few seconds to accept connections after starting.

    Even though compose waits for the DB to be "healthy", we retry for
    robustness: this is a standard pattern to avoid startup races between
    containers.
    """
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return await asyncpg.connect(DATABASE_URL)
        except (OSError, asyncpg.PostgresError) as exc:
            last_error = exc
            print(f"  BD no lista (intento {attempt}/{retries}): {exc}")
            await asyncio.sleep(delay)
    raise SystemExit(f"No se pudo conectar a la base de datos: {last_error}")


async def main() -> None:
    if not DATABASE_URL:
        raise SystemExit("Falta la variable de entorno DATABASE_URL")

    conn = await connect_with_retry()
    try:
        # Log table: one row per migration that has already been applied.
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM schema_migrations")
        }

        # Alphabetical order = version order (001, 002, 003...).
        # We exclude the *_rollback.sql files (only used to undo by hand).
        files = sorted(
            p
            for p in MIGRATIONS_DIR.glob("*.sql")
            if not p.stem.endswith("_rollback")
        )

        for path in files:
            if path.name in applied:
                print(f"  ya aplicada  {path.name}")
                continue

            sql = path.read_text(encoding="utf-8")
            # Transaction: either the whole migration is applied and recorded,
            # or nothing is applied. Never a half-finished state.
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)",
                    path.name,
                )
            print(f"  APLICADA     {path.name}")

        print("Migraciones al día.")
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
