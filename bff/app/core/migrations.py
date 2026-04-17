from pathlib import Path
from typing import List, Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .config import settings
from .db import engine


def _migrations_root() -> Path:
    root = Path(settings.MIGRATIONS_DIR)
    if root.is_absolute():
        return root
    # /app/app/core -> /app
    return Path(__file__).resolve().parents[2] / root


def _list_migration_files() -> List[Path]:
    root = _migrations_root()
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".sql"])


def _split_sql_statements(sql_script: str) -> List[str]:
    statements: List[str] = []
    current: List[str] = []
    for raw_line in sql_script.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        current.append(raw_line)
        if line.endswith(";"):
            statements.append("\n".join(current).strip())
            current = []
    if current:
        statements.append("\n".join(current).strip())
    return statements


def _ensure_tracking_table(db_engine: Engine) -> None:
    dialect = db_engine.dialect.name
    if dialect in {"mysql", "mariadb"}:
        create_sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """
    else:
        create_sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """
    with db_engine.begin() as conn:
        conn.execute(text(create_sql))


def _applied_versions(db_engine: Engine) -> Sequence[str]:
    _ensure_tracking_table(db_engine)
    with db_engine.connect() as conn:
        rows = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version ASC")).fetchall()
    return [r[0] for r in rows]


def pending_versions(db_engine: Engine = engine) -> List[str]:
    files = _list_migration_files()
    applied = set(_applied_versions(db_engine))
    return [file.stem for file in files if file.stem not in applied]


def apply_pending_migrations(db_engine: Engine = engine) -> List[str]:
    files = _list_migration_files()
    applied = set(_applied_versions(db_engine))
    applied_now: List[str] = []

    for migration_file in files:
        version = migration_file.stem
        if version in applied:
            continue

        script = migration_file.read_text(encoding="utf-8")
        statements = _split_sql_statements(script)
        if not statements:
            continue

        with db_engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
            conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version},
            )
        applied_now.append(version)
    return applied_now


if __name__ == "__main__":
    applied_versions = apply_pending_migrations(engine)
    if applied_versions:
        print("Applied migrations:")
        for version in applied_versions:
            print(f"- {version}")
    else:
        print("No pending migrations.")
