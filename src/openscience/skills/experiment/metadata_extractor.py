"""Metadata extractor skill: parse filenames, csv/tsv headers, infer column roles."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_KV_PATTERN = re.compile(r"([A-Za-z][A-Za-z0-9]*)=([^=_\-.]+)")
_TOKEN_PATTERN = re.compile(r"([A-Za-z]+)(\d+)")


def from_filename(
    filename: str = "",
    keys: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Parse ``key=value`` pairs (and trailing ``tokenNNN`` tokens) from a filename.

    Example: ``"sample=Patient12_group=treated_batch=3_reads.fastq.gz"``
    -> {"sample": "Patient12", "group": "treated", "batch": "3"}
    """
    name = Path(filename).name
    # strip common multi-part extensions
    for ext in (".fastq.gz", ".fq.gz", ".tar.gz"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    else:
        name = Path(name).stem

    meta: dict[str, str] = {}
    for m in _KV_PATTERN.finditer(name):
        meta[m.group(1)] = m.group(2)
    remainder = _KV_PATTERN.sub("", name)
    for tok in re.split(r"[^A-Za-z0-9]+", remainder):
        m = _TOKEN_PATTERN.fullmatch(tok or "")
        if m and (keys is None or m.group(1) in keys):
            meta.setdefault(m.group(1), m.group(2))
    return result(filename=filename, metadata=meta, n_fields=len(meta))


def from_header(
    path: str = "",
    n_lines: int = 5,
    delimiter: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Extract header info from the first ``n_lines`` lines of a csv/tsv file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {path}")
    raw_lines: list[str] = []
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= n_lines:
                break
            raw_lines.append(line.rstrip("\n"))
    if not raw_lines:
        return result(path=str(p), delimiter=None, columns=[], n_lines_read=0)

    if delimiter is None:
        try:
            dialect = csv.Sniffer().sniff("\n".join(raw_lines), delimiters=",\t;|")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = "\t" if "\t" in raw_lines[0] else ","
    columns = next(csv.reader([raw_lines[0]], delimiter=delimiter)) if raw_lines else []
    return result(
        path=str(p),
        delimiter=delimiter,
        columns=[c.strip() for c in columns],
        n_columns=len(columns),
        n_lines_read=len(raw_lines),
        preview=raw_lines,
    )


def infer_column_roles(
    data: Any = None,
    columns: list[str] | None = None,
    categorical_threshold: int = 20,
    **kwargs: Any,
) -> dict[str, Any]:
    """Infer column roles (id/numeric/categorical/datetime) via heuristics.

    ``data`` is a pandas DataFrame, dict of columns, or list of dicts. When
    only ``columns=[names]`` is given, roles are guessed from names alone.
    """
    if data is None and columns is not None:
        roles = {}
        for name in columns:
            lname = name.lower()
            if lname in ("id", "index") or lname.endswith("_id") or lname.endswith("id"):
                roles[name] = "id"
            elif "date" in lname or "time" in lname:
                roles[name] = "datetime"
            else:
                roles[name] = "unknown"
        return result(roles=roles, inference="names-only")

    if hasattr(data, "dtypes"):  # pandas DataFrame
        import pandas as pd

        roles: dict[str, Any] = {}
        for col in data.columns:
            s = data[col]
            info: dict[str, Any] = {}
            if pd.api.types.is_bool_dtype(s):
                role = "categorical"
            elif pd.api.types.is_numeric_dtype(s):
                role = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(s):
                role = "datetime"
            else:
                non_null = s.dropna()
                try:
                    parsed = pd.to_datetime(non_null, errors="raise")
                    role = "datetime"
                    del parsed
                except (ValueError, TypeError):
                    nunique = non_null.nunique()
                    role = (
                        "id"
                        if nunique == len(non_null) and len(non_null) > 0
                        else ("categorical" if nunique <= categorical_threshold else "text")
                    )
            info["role"] = role
            if role == "categorical":
                info["n_unique"] = int(s.dropna().nunique())
            roles[str(col)] = info
        return result(roles=roles, n_columns=len(roles))

    if isinstance(data, dict):
        columns = list(data)
        rows = [{k: v[i] for k, v in data.items()} for i in range(len(next(iter(data.values()), [])))]
    elif isinstance(data, list):
        rows = data
        columns = list(rows[0]) if rows else []
    else:
        raise ValueError("data must be a DataFrame, dict of columns, or list of dicts")

    roles = {}
    for col in columns:
        vals = [r.get(col) for r in rows if r.get(col) is not None]
        nunique = len({str(v) for v in vals})
        name_is_id = col.lower() in ("id", "index") or col.lower().endswith("_id")
        is_numeric = bool(vals) and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals
        )
        is_dt = bool(vals) and all(
            isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?", v)
            for v in vals
        )
        if name_is_id:
            role = "id"
        elif is_dt:
            role = "datetime"
        elif is_numeric:
            role = "numeric"
        elif (
            nunique == len(vals)
            and len(vals) > categorical_threshold
            and all(isinstance(v, str) for v in vals)
        ):
            role = "id"
        elif nunique <= categorical_threshold:
            role = "categorical"
        else:
            role = "text"
        roles[col] = {"role": role, "n_unique": nunique}
    return result(roles=roles, n_columns=len(roles), n_rows=len(rows))


_PII_PATTERNS: dict[str, str] = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
}


def redact(
    text: Any = "",
    kinds: list[str] | None = None,
    replacement: str = "[REDACTED]",
    columns: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Redact PII (email/phone/ssn) from text, or named columns of records.

    - ``text`` a string: redact pattern ``kinds`` (default: all).
    - ``text`` a list of dicts / DataFrame: redact ``columns`` entirely
      (replace every value with ``replacement``).
    """
    import pandas as pd  # noqa: F401 - only needed for isinstance check below

    if isinstance(text, str):
        kinds = kinds or list(_PII_PATTERNS)
        unknown = [k for k in kinds if k not in _PII_PATTERNS]
        if unknown:
            raise ValueError(f"unknown redaction kinds {unknown}; use {sorted(_PII_PATTERNS)}")
        out = text
        counts: dict[str, int] = {}
        for kind in kinds:
            pattern = _PII_PATTERNS[kind]
            out, n = re.subn(pattern, replacement, out)
            counts[kind] = n
        return result(
            redacted_text=out,
            n_redacted=sum(counts.values()),
            counts=counts,
            kinds=kinds,
        )

    if not columns:
        raise ValueError("columns=[...] is required to redact records")
    df = pd.DataFrame(text)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"columns not present: {missing}")
    for c in columns:
        df[c] = replacement
    return result(
        redacted_columns=columns,
        n_rows=len(df),
        records=df.to_dict(orient="records"),
    )


run = skill_run(
    {
        "from_filename": from_filename,
        "from_header": from_header,
        "infer_column_roles": infer_column_roles,
        "redact": redact,
    }
)

register_skill("metadata_extractor", run)
