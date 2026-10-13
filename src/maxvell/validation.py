"""Bounded checks for the shipped snapshot; no experiment archive required."""
from __future__ import annotations
from importlib import import_module
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import zlib
from . import models
from .decode import decode_model,decode_ufm

PATTERNS={
    "local_user_path":re.compile(r"(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/(?:home|Users)/[A-Za-z0-9_-]+/|\\\\[A-Za-z0-9_-]+\\[A-Za-z0-9_$-]+(?:\\|/|$))"),
    "email":re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "network_address":re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])|(?<![\w])(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}(?![\w])"),
    "credential":re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"),
}
TABLES={'devices', 'model_blobs', 'metadata', 'model_catalog', 'mapping_results'}
CATALOG_KINDS={'aload_candidates': 1, 'cff_io': 92, 'device_fields': 92, 'functional': 92, 'global_clock': 92, 'h4_v4': 92, 'input_selectors': 92, 'io_fields': 92, 'lc_bundle': 92, 'le_lab_controls': 92, 'lut': 92, 'lut_semantics': 2, 'outside_legal': 48, 'remaining_mux': 92, 'route_mux': 92, 'source_exclusions': 92, 'ufm_content': 1, 'ufm_recipe': 7, 'usercode': 92}
CATALOG_KINDS.update(aload_sites=1,lut_topology=2,io_options=8,ufm_source_sink_support=1,ufm_candidates=1)
CATALOG_KINDS.update(route_group_candidates=1,selector_qualification=1,lut_context_candidates=1)
COUNTS={'devices': 7, 'mapping_results': 3149, 'model_blobs': 185, 'model_catalog': 1363, 'metadata': 4}
EXCLUDED_KEYS={"source_refs","source_ref","source_hashes","source_artifact_sha256","pof_sha256","ir_ref","provider_ref","previous_provider_refs","command","argv","path","input_sha256","evidence_refs","observed_role_scope"}

def privacy_categories(text):
    return [name for name,pattern in PATTERNS.items() if pattern.search(text)]

def forbidden_keys(value):
    if isinstance(value,dict):
        return any(k in EXCLUDED_KEYS or k.endswith("_ref") or k.endswith("_sha256") or forbidden_keys(v) for k,v in value.items())
    if isinstance(value,list):return any(forbidden_keys(v) for v in value)
    return False

def model_privacy(value):
    strings=set();pending=[value]
    while pending:
        item=pending.pop()
        if isinstance(item,dict):strings.update(item);pending.extend(item.values())
        elif isinstance(item,list):pending.extend(item)
        elif isinstance(item,str):strings.add(item)
    return any(privacy_categories(text) for text in strings)

def validate():
    failures=[];checked=0;json_bytes=0;headers={}
    with models.connect() as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0]!="ok":failures.append("database integrity")
        if connection.execute("PRAGMA foreign_key_check").fetchall():failures.append("database foreign keys")
        tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables!=TABLES:failures.append("database table allowlist")
        for name,count in COUNTS.items():
            if name not in tables or connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]!=count:failures.append("table population: "+name)
        kinds=dict(connection.execute("SELECT kind,COUNT(*) FROM model_catalog GROUP BY kind"))
        if kinds!=CATALOG_KINDS:failures.append("model target populations")
        if connection.execute("SELECT COUNT(DISTINCT target) FROM model_catalog WHERE target!='*'").fetchone()[0]!=92:failures.append("exact target population")
        schema_sql=(models.DATABASE.parent/"schema.sql").read_text(encoding="utf-8")
        with sqlite3.connect(":memory:") as expected:
            expected.executescript(schema_sql)
            actual={name:[tuple(r) for r in connection.execute(f"PRAGMA table_info({name})")] for name in tables}
            wanted={name:expected.execute(f"PRAGMA table_info({name})").fetchall() for name in TABLES}
            if actual!=wanted:failures.append("database column allowlist")
        for name in tables-{"model_blobs"}:
            for row in connection.execute(f"SELECT * FROM {name}"):
                if any(privacy_categories(v) for v in row if isinstance(v,str)):
                    failures.append("database text privacy: "+name);break
        rows=connection.execute("SELECT content_sha256,json_bytes,zlib_json FROM model_blobs ORDER BY content_sha256").fetchall()
        reps=connection.execute("SELECT MIN(target),kind,content_sha256 FROM model_catalog GROUP BY kind,content_sha256 ORDER BY kind,content_sha256").fetchall()
        catalog=connection.execute("SELECT target,kind,cfm_bits,decoder_module,decoder_function FROM model_catalog ORDER BY target,kind").fetchall()
    for digest,length,blob in rows:
        raw=zlib.decompress(blob);json_bytes+=len(raw)
        if len(raw)!=length or hashlib.sha256(raw).hexdigest()!=digest:failures.append("model checksum")
        text=raw.decode("utf-8");value=json.loads(text)
        if model_privacy(value):failures.append("model text privacy")
        if forbidden_keys(value):failures.append("model metadata allowlist")
        headers[digest]=(value.get("target"),value.get("cfm_bits"),value.get("geometry"))
    for target,kind,bits,module,function in catalog:
        if target!="*" and re.fullmatch(r"5M\d+Z[A-Z]\d+[ACI]\d",target) is None:failures.append("target syntax")
        with models.connect() as connection:
            digest=connection.execute("SELECT content_sha256 FROM model_catalog WHERE target=? AND kind=?",(target,kind)).fetchone()[0]
        model_target,model_bits,geometry=headers[digest]
        if model_bits is None and geometry:model_bits=geometry["serial_columns"]*geometry["serial_rows"]
        if model_target not in (None,"@TARGET@",target) or model_bits!=bits:failures.append("model target/geometry: "+kind)
        if kind not in ("lut","lut_semantics","lc_bundle","ufm_content","functional","global_clock","ufm_recipe","aload_candidates","aload_sites","lut_topology","io_options","ufm_source_sink_support","ufm_candidates","route_group_candidates","selector_qualification","lut_context_candidates"):
            if not module or not function or not callable(getattr(import_module("maxvell._core."+module),function,None)):failures.append("decoder entry point: "+kind)
    for target,kind,digest in reps:
        provider,record=models.load(target,kind)
        try:
            for byte in (0,255):
                payload=bytes([byte])*(record["cfm_bits"]//8)
                if kind=="ufm_content":result=decode_ufm(payload,provider)
                else:result=decode_model(target,kind,provider,record,payload)
                if result.get("productive_emission_allowed",False) is not False:raise ValueError("decoder widened productive grant")
            checked+=1
        except (ValueError,KeyError,TypeError,IndexError) as error:failures.append(f"model decoder {target}/{kind}: {error}")
    snapshot=json.loads((models.DATABASE.parent/"snapshot.json").read_text(encoding="utf-8"))
    if snapshot["database_bytes"]!=models.DATABASE.stat().st_size or snapshot["table_counts"]!=COUNTS:failures.append("snapshot metadata")
    package=Path(__file__).parent
    files=0
    for path in package.rglob("*"):
        if path.is_file() and path.suffix in (".py",".json",".sql") and "__pycache__" not in path.parts:
            files+=1
            if privacy_categories(path.read_text(encoding="utf-8")):failures.append("package text privacy: "+path.relative_to(package).as_posix())
    return {"format":"maxvell.validation.v1","status":"passed" if not failures else "failed","failures":sorted(set(failures)),"catalog_rows":len(catalog),"unique_model_decoders_checked":checked,"model_patterns":["all zero","all one"],"model_json_bytes_checked":json_bytes,"package_text_files_checked":files,"database_bytes":models.DATABASE.stat().st_size,"privacy_scope":"schema/text/decompressed models; heuristic detection","hardware_validation":False,"independent_equivalence_proved":False}
