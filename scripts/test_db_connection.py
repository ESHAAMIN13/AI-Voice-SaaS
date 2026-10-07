"""Standalone Supabase connection test (Phase 9). Does not use Django."""

from pathlib import Path

import environ
import psycopg

ROOT = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(ROOT / "backend" / ".env")


def main():
    try:
        url = env("DATABASE_URL")
    except Exception:
        print("FAIL: DATABASE_URL is missing in backend/.env")
        return 1

    try:
        with psycopg.connect(url, connect_timeout=15, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute("select current_database(), version()")
                db_name, version = cur.fetchone()
        print("OK: connected to Supabase PostgreSQL")
        print("database:", db_name)
        print("server  :", version.split(",")[0])
        return 0
    except Exception as exc:
        print("FAIL:", type(exc).__name__)
        print(str(exc).strip().splitlines()[0])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())