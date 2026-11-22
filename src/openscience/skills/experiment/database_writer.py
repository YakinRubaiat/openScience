"""Database writer skill: write/read pandas DataFrames to SQLite, upsert stub."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _to_frame(data: Any):
    import pandas as pd

    if isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, (list, dict)):
        return pd.DataFrame(data)
    raise ValueError("data must be a pandas DataFrame, list of dicts, or dict of columns")


def to_sqlite(
    data: Any = None,
    db_path: str = "",
    table: str = "data",
    if_exists: str = "replace",
    **kwargs: Any,
) -> dict[str, Any]:
    """Write a DataFrame (or records) to a SQLite table (create + insert)."""
    if if_exists not in ("replace", "append", "fail"):
        raise ValueError("if_exists must be one of: replace, append, fail")
    df = _to_frame(data)
    db_path = str(db_path)
    if not db_path:
        raise ValueError("db_path is required")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table, conn, if_exists=if_exists, index=False)
        n_rows = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    return result(
        db_path=db_path,
        table=table,
        n_rows_written=len(df),
        n_rows_total=int(n_rows),
        if_exists=if_exists,
    )


def read_table(
    db_path: str = "",
    table: str = "data",
    limit: int | None = None,
    where: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Read a SQLite table (optionally filtered) into a list of records."""
    import pandas as pd

    db_path = str(db_path)
    if not Path(db_path).exists():
        raise FileNotFoundError(f"No such database: {db_path}")
    query = f'SELECT * FROM "{table}"'
    if where:
        query += f" WHERE {where}"
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn)
    return result(
        db_path=db_path,
        table=table,
        n_rows=len(df),
        columns=list(df.columns),
        records=df.to_dict(orient="records"),
    )


def upsert_stub(
    data: Any = None,
    db_path: str = "",
    table: str = "data",
    key_columns: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Upsert rows by key columns (delete matching keys, then insert).

    A full ON CONFLICT upsert requires a unique index; this stub implements the
    delete+insert strategy which works on any existing table.
    """
    if not key_columns:
        raise ValueError("key_columns=[...] is required for upsert")
    df = _to_frame(data)
    missing = [c for c in key_columns if c not in df.columns]
    if missing:
        raise ValueError(f"key columns not present in data: {missing}")
    db_path = str(db_path)
    written = 0
    if len(df) == 0:
        return result(db_path=db_path, table=table, n_rows_upserted=0)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists:
            cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            table_cols = {c[1] for c in cols}
            missing = [c for c in key_columns if c not in table_cols]
            if missing:
                raise ValueError(f"key columns not present in table: {missing}")
            clause = " AND ".join(f'"{c}" = ?' for c in key_columns)
            for _, row in df.iterrows():
                conn.execute(
                    f'DELETE FROM "{table}" WHERE {clause}',
                    tuple(row[c] for c in key_columns),
                )
        df.to_sql(table, conn, if_exists="append", index=False)
        written = len(df)
    return result(db_path=db_path, table=table, n_rows_upserted=written, key_columns=key_columns)


run = skill_run(
    {
        "to_sqlite": to_sqlite,
        "read_table": read_table,
        "upsert_stub": upsert_stub,
    }
)

register_skill("database_writer", run)
