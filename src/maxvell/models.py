"""Read the self-contained, immutable publication snapshot."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import sqlite3
import zlib

DATABASE = Path(__file__).parent / "data" / "results.sqlite"

@contextmanager
def connect(path: Path = DATABASE):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    try:
        yield connection
    finally:
        connection.close()

def catalog(target: str | None = None):
    with connect() as connection:
        sql = "SELECT target,kind,cfm_bits FROM model_catalog"
        rows = connection.execute(sql + (" WHERE target=?" if target else "") + " ORDER BY target,kind", (target,) if target else ())
        return [dict(row) for row in rows]

def load(target: str, kind: str):
    with connect() as connection:
        row = connection.execute("SELECT b.content_sha256,b.json_bytes,b.zlib_json,c.cfm_bits,c.decoder_module,c.decoder_function FROM model_catalog c JOIN model_blobs b USING(content_sha256) WHERE c.target=? AND c.kind=?", (target,kind)).fetchone()
    if row is None:
        raise ValueError(f"No {kind} model for exact target {target}")
    raw = zlib.decompress(row["zlib_json"])
    if len(raw) != row["json_bytes"] or hashlib.sha256(raw).hexdigest() != row["content_sha256"]:
        raise ValueError("Published model content checksum differs")
    def restore(value):
        if isinstance(value, dict):
            return {key: restore(item) for key,item in value.items()}
        if isinstance(value,list):
            return [restore(item) for item in value]
        return target if value == "@TARGET@" else value
    return restore(json.loads(raw)), dict(row)

def status():
    with connect() as connection:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        counts = {name:connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("mapping_results","model_catalog","model_blobs")}
        kinds = [dict(row) for row in connection.execute("SELECT kind,COUNT(*) AS targets FROM model_catalog GROUP BY kind ORDER BY kind")]
    return {"format":"maxvell.public_status.v2","metadata":metadata,"counts":counts,"model_kinds":kinds,"public_productive_grant":False,"whole_design_equivalence":"unproved"}
