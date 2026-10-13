"""Bounded, read-only access to the published database and model contents."""
import json
import math
import sqlite3
from . import models

TABLES = {"metadata", "devices", "mapping_results", "model_catalog"}
FUNCTIONS = {"abs", "avg", "coalesce", "count", "ifnull", "instr", "length", "lower", "ltrim", "max", "min", "nullif", "replace", "round", "rtrim", "substr", "substring", "sum", "total", "trim", "typeof", "upper"}

def schema():
    with models.connect() as db:
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        tables = {name: {"rows": db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0],
                         "columns": [{"name": r[1], "type": r[2], "primary_key": r[5]} for r in db.execute(f"PRAGMA table_info({name})")]} for name in names}
    return {"format": "maxvell.database_schema.v1", "tables": tables}

def sql(statement, parameters=(), limit=50, max_bytes=16384):
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Query limit must be between 1 and 1000")
    if not isinstance(parameters, (list, tuple)) or any(type(v) not in (str, int, float, type(None)) for v in parameters):
        raise ValueError("Query parameters must be a JSON array of strings, numbers or null")
    if any(type(v) is int and not -(1 << 63) <= v < (1 << 63) or type(v) is float and not math.isfinite(v) for v in parameters):
        raise ValueError("Query numbers must be finite and integers must fit SQLite's 64-bit range")
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError("An SQL query is required")
    def authorize(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and first in TABLES:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and second.lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    budget = 2000
    def progress():
        nonlocal budget
        budget -= 1
        return budget < 0
    try:
        with models.connect() as db:
            db.set_authorizer(authorize)
            db.set_progress_handler(progress, 1000)
            cursor = db.execute(statement, parameters)
            columns = [d[0] for d in cursor.description]
            if len(set(columns)) != len(columns):
                raise ValueError("Duplicate query columns; give them distinct SQL aliases")
            rows = cursor.fetchmany(limit + 1)
    except sqlite3.DatabaseError as error:
        raise ValueError(f"Read-only query rejected: {error}") from error
    result = {"format": "maxvell.database_query.v1", "columns": columns,
              "rows": [dict(row) for row in rows[:limit]], "row_count": min(len(rows), limit),
              "truncated": len(rows) > limit, "limit": limit}
    if len(json.dumps(result, sort_keys=True, allow_nan=False).encode("utf-8")) > max_bytes:
        raise ValueError("Query output exceeds the byte bound; select fewer rows/columns or use --out")
    return result
