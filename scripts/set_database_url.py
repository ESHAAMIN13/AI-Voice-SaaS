"""Safely write DATABASE_URL into backend/.env (Phase 9 helper)."""

import getpass
from pathlib import Path
from urllib.parse import quote

ENV_PATH = Path(__file__).resolve().parent.parent / "backend" / ".env"


def main():
    host = input("Pooler host (aws-...pooler.supabase.com): ").strip()
    ref = input("Project reference (code after 'postgres.'): ").strip()
    password = getpass.getpass("Database password (hidden while typing): ")

    ref = ref.removeprefix("postgres.")
    if "pooler.supabase.com" not in host:
        print("STOP: host must end with pooler.supabase.com (use Session pooler).")
        return 1
    if password.startswith("[") or password.endswith("]"):
        print("STOP: remove the [ ] brackets, type only the real password.")
        return 1

    safe_password = quote(password, safe="")
    url = f"postgres://postgres.{ref}:{safe_password}@{host}:5432/postgres"

    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not line.startswith("DATABASE_URL=")]
    lines.append(f"DATABASE_URL={url}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")

    print("DATABASE_URL updated in backend/.env (password not shown).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())