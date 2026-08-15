"""Monthly funnel report for the public demo (ADR-0019 §7).

Answers the questions that make a month a decision instead of an anecdote:

    Sessions started ......... did anyone show up?
    Aha rate ................. did they get the product to work?
    Downloads ................ did they get value out of it?
    Leads .................... did anyone want to keep talking?
    Walls .................... were the caps too tight, or is this real demand?
    Spend .................... what did the month cost?
    Cost per lead ............ is the demo a marketing asset or a leak?

That last one is the number that decides whether to keep the demo running.

Deliberately a script and not a dashboard, and deliberately not a third-party
analytics tool: adding Google Analytics or PostHog to a page that processes voice
means an external tracker, a consent problem, and a bad look for a product whose
promise is that your data is yours. For a one-month probe, SQL is enough.

    cd backend && .venv/bin/python scripts/funnel_report.py            # this month
    cd backend && .venv/bin/python scripts/funnel_report.py 2026-08-01 # from a date
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def _pct(part: int, whole: int) -> str:
    return f"{(100 * part / whole):5.1f}%" if whole else "    — "


async def main(since: datetime) -> None:
    if not DATABASE_URL:
        print("Falta la variable de entorno DATABASE_URL")
        raise SystemExit(1)

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        funnel = await conn.fetchrow(
            """
            SELECT
                COUNT(*)                                          AS started,
                COUNT(first_narration_at)                         AS narrated,
                COUNT(downloaded_at)                              AS downloaded,
                COUNT(*) FILTER (WHERE wall_kind = 'trial')       AS wall_trial,
                COUNT(*) FILTER (WHERE wall_kind = 'budget')      AS wall_budget
            FROM template_sessions
            WHERE created_at >= $1
            """,
            since,
        )
        spend = await conn.fetchval(
            "SELECT COALESCE(SUM(estimated_cost_usd), 0) FROM usage_ledger "
            "WHERE created_at >= $1",
            since,
        )
        leads = await conn.fetch(
            "SELECT capture_point, COUNT(*) AS n FROM demo_leads "
            "WHERE created_at >= $1 GROUP BY capture_point ORDER BY capture_point",
            since,
        )
        platforms = await conn.fetch(
            """
            SELECT
                COALESCE(client_platform, 'desconocido') AS platform,
                COALESCE(client_browser, 'desconocido')  AS browser,
                COUNT(*)                  AS sessions,
                COUNT(first_narration_at) AS narrated
            FROM template_sessions
            WHERE created_at >= $1
            GROUP BY 1, 2
            ORDER BY sessions DESC
            """,
            since,
        )
        # The industry signal: column names come straight out of schema_json, so
        # there is no second copy to drift (ADR-0019 §7). Names only — never the
        # values the user narrated.
        industries = await conn.fetch(
            """
            SELECT col->>'name' AS column_name, COUNT(*) AS n
            FROM template_sessions,
                 LATERAL jsonb_array_elements(schema_json->'columns') AS col
            WHERE created_at >= $1
            GROUP BY 1
            ORDER BY n DESC
            LIMIT 20
            """,
            since,
        )
    finally:
        await conn.close()

    started = funnel["started"]
    total_leads = sum(row["n"] for row in leads)

    print(f"\nVoxa — demo público, desde {since:%Y-%m-%d}\n")
    print("EMBUDO")
    print(f"  Sesiones iniciadas      {started:6d}")
    print(f"  Llegaron a narrar       {funnel['narrated']:6d}   {_pct(funnel['narrated'], started)}  <- tasa del 'ajá'")
    print(f"  Descargaron             {funnel['downloaded']:6d}   {_pct(funnel['downloaded'], started)}")
    print(f"  Toparon con el cupo     {funnel['wall_trial']:6d}")
    print(f"  Toparon con presupuesto {funnel['wall_budget']:6d}   <- si crece, los topes van cortos")

    print("\nPROSPECTOS")
    for row in leads:
        print(f"  {row['capture_point']:<22}{row['n']:6d}")
    if not leads:
        print("  (ninguno)")

    print("\nCOSTO")
    print(f"  Gasto estimado          ${float(spend):8.4f}")
    if total_leads:
        print(f"  Costo por prospecto     ${float(spend) / total_leads:8.4f}  <- el número que decide")
    else:
        print("  Costo por prospecto            —   (sin prospectos todavía)")

    print("\nPLATAFORMAS  (una tasa de 'ajá' baja aquí = algo roto, no desinterés)")
    for row in platforms:
        print(
            f"  {row['platform']:<10}{row['browser']:<14}"
            f"{row['sessions']:5d} ses.  {_pct(row['narrated'], row['sessions'])} narró"
        )
    if not platforms:
        print("  (sin datos)")

    print("\nSEÑAL DE INDUSTRIA  (nombres de columnas más frecuentes)")
    for row in industries:
        print(f"  {row['column_name']:<30}{row['n']:4d}")
    if not industries:
        print("  (sin datos)")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        start = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    asyncio.run(main(start))
