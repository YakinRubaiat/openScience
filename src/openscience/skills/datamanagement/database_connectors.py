"""database_connectors skill: sqlite3-backed data access (stdlib only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return sqlite3.connect(str(path))


def read_sqlite(db_path: str, table: str | None = None,
                query: str | None = None,
                max_rows: int | None = None) -> dict[str, Any]:
    """Read a table or run a SELECT query against a sqlite database."""
    if not table and not query:
        raise ValueError("read_sqlite requires 'table' or 'query'")
    with _connect(db_path) as conn:
        sql = query or f"SELECT * FROM {_quote_ident(table)}"  # type: ignore[arg-type]
        if max_rows is not None and "limit" not in sql.lower():
            sql = f"{sql.rstrip().rstrip(';')} LIMIT {int(max_rows)}"
        df = pd.read_sql_query(sql, conn)
    return result(
        n_rows=int(len(df)),
        n_cols=int(df.shape[1]),
        columns=[str(c) for c in df.columns],
        data=df.to_dict("records"),
    )


def write_sqlite(db_path: str, table: str, data: Any,
                 if_exists: str = "fail") -> dict[str, Any]:
    """Write records to a sqlite table (creates the database if needed)."""
    if if_exists not in ("fail", "replace", "append"):
        raise ValueError("if_exists must be one of: fail, replace, append")
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    with sqlite3.connect(str(db_path)) as conn:
        df.to_sql(table, conn, index=False, if_exists=if_exists)
        n = conn.execute(
            f"SELECT COUNT(*) FROM {_quote_ident(table)}"  # noqa: S608 - quoted ident
        ).fetchone()[0]
    return result(table=table, n_written=int(len(df)), n_rows_total=int(n),
                  db_path=str(db_path))


def list_tables(db_path: str) -> dict[str, Any]:
    """List all user tables in a sqlite database with row counts."""
    with _connect(db_path) as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        counts = {
            t: conn.execute(f"SELECT COUNT(*) FROM {_quote_ident(t)}").fetchone()[0]
            for t in tables
        }
    return result(db_path=str(db_path), tables=tables,
                  row_counts={t: int(n) for t, n in counts.items()})


def _quote_ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe table name {name!r}")
    return f'"{name}"'


_OPS = {"read_sqlite": read_sqlite, "write_sqlite": write_sqlite, "list_tables": list_tables}

run = skill_run(_OPS)
register_skill("database_connectors", run)
