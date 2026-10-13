"""POF and native storage IR; open connectivity is never synthesized."""
from __future__ import annotations
from collections import defaultdict
from importlib import import_module
from pathlib import Path
import json
import re
from . import models
from ._core.pof import load_pof

OPEN_INTERFACES = ["LUT native input connections", "selected routing and legal alternatives", "effective IO modes and package pin wiring", "UFM port/control instance", "whole-design state/timing equivalence"]

def inspect(path: Path,selected_target: str | None=None):
    data = path.read_bytes()
    pof = load_pof(path,data=data)
    for tag in (2,8,0x11,0x18):
        if sum(packet.packet_id==tag for packet in pof.packets)>1:
            raise ValueError("Duplicate critical POF packet")
    crc = pof.terminator_crc()
    if crc is not None and pof.packets[-1].packet_id!=8:
        raise ValueError("POF terminator must be the final packet")
    if crc is not None and crc.crc_ok is False:
        raise ValueError("POF terminator CRC does not match")
    embedded=pof.text_packet(2)
    target=embedded
    binding="exact_embedded_part"
    if selected_target is not None:
        if re.fullmatch(r"5M\d+Z",embedded or ""):
            if not selected_target.startswith(embedded):raise ValueError("Selected target conflicts with embedded die")
            target=selected_target;binding="explicit_caller_target"
        elif selected_target!=embedded:raise ValueError("Selected target conflicts with embedded part")
    if not target or not any(row["kind"] == "lut" for row in models.catalog(target)):
        raise ValueError("POF device tag is not a published exact target")
    sections = {}
    for packet in (0x0011,0x0018):
        if not any(p.packet_id == packet for p in pof.packets):
            continue
        section = pof.section(packet)
        payload = pof.section_payload(packet)
        if section.bit_length != len(payload)*8:
            raise ValueError("Declared section geometry differs from payload")
        sections[f"0x{packet:04X}"] = {"bits":section.bit_length,"bytes":len(payload)}
    return pof, {"format":"maxvell.pof_summary.v1","target":target,"embedded_target":embedded,"target_binding":binding,"packet_count":pof.packet_count,"file_bytes":len(data),"packets":[{"tag":p.packet_id,"role":p.role,"header_offset":p.offset,"payload_offset":p.payload_offset,"payload_bytes":p.length} for p in pof.packets],"sections":sections,"crc_ok":None if crc is None else crc.crc_ok,"creator_and_comments_omitted":True}

def decode_lut(provider, payload):
    bits = provider.get("cfm_bits") or provider["geometry"]["serial_columns"]*provider["geometry"]["serial_rows"]
    if len(payload)*8 != bits:
        raise ValueError("LUT payload geometry differs")
    cells = defaultdict(dict)
    seen = set()
    for row in provider["rows"]:
        offset, ordinal = row["pof_payload_offset"],row["asmdb_lut_ordinal"]
        location = row["lc_location"]
        xor = row["native_serializer_xor"]
        if type(offset) is not int or not 0 <= offset < bits or offset in seen or type(ordinal) is not int or not 0 <= ordinal < 16 or type(xor) is not int or xor not in (0,1):
            raise ValueError("LUT storage binding differs")
        if ordinal in cells[location]:
            raise ValueError("Duplicate LUT cell/ordinal")
        seen.add(offset)
        cells[location][ordinal] = ((payload[offset//8] >> (offset%8)) & 1) ^ xor
    if any(set(rows) != set(range(16)) for rows in cells.values()):
        raise ValueError("LUT field is incomplete")
    return [{"native_location":location,"native_ordinal_mask":f"{sum(value<<i for i,value in sorted(rows.items())):04X}"} for location,rows in sorted(cells.items())]

def decode_semantic_lut(provider,payload):
    if len(payload)*8 != provider["geometry"]["serial_columns"]*provider["geometry"]["serial_rows"]:
        raise ValueError("LUT minterm payload geometry differs")
    cells = defaultdict(dict)
    seen = set()
    for row in provider["rows"]:
        offset = row["pof_payload_offset"]
        minterm = row["logical_minterm"]
        location = row["lc_location"]
        xor = row["polarity"]
        if type(offset) is not int or not 0 <= offset < len(payload)*8 or offset in seen or type(minterm) is not int or not 0 <= minterm < 16 or minterm in cells[location] or type(xor) is not int or xor not in (0,1):
            raise ValueError("LUT minterm binding differs")
        seen.add(offset)
        cells[location][minterm] = ((payload[offset//8] >> (offset%8)) & 1) ^ xor
    if any(set(values) != set(range(16)) for values in cells.values()):
        raise ValueError("LUT minterm field is incomplete")
    return [{"native_location":location,"logical_minterm_mask":f"{sum(value<<i for i,value in sorted(values.items())):04X}"} for location,values in sorted(cells.items())]

def decode_ufm(payload,provider):
    if len(payload)!=1024:
        raise ValueError("UFM content requires exactly 8192 bits")
    mapping = provider["layout"]["offset_by_logical_bit"]
    xor = provider["layout"]["xor_by_logical_bit"]
    if len(mapping)!=8192 or any(type(i) is not int for i in mapping) or set(mapping)!=set(range(8192)) or len(xor)!=8192 or any(type(i) is not int or i not in (0,1) for i in xor):
        raise ValueError("UFM mapping is not a complete bijection")
    words = [sum((((payload[mapping[w*16+b]//8] >> (mapping[w*16+b]%8)) & 1)^xor[w*16+b])<<b for b in range(16)) for w in range(512)]
    return {"format":"maxvell.ufm_content_ir.v1","address_space":"UFM","word_width":16,"word_count":512,"words":words,"logical_instances_created":0,"productive_emission_allowed":False}

def decode(path: Path, stages: list[str] | None = None,selected_target: str | None=None):
    pof,summary = inspect(path,selected_target)
    target = summary["target"]
    payload = pof.section_payload(0x0011)
    available = {row["kind"] for row in models.catalog(target)}
    requested = set(stages or sorted(available))
    if not requested <= available | {"ufm_content"}:
        raise ValueError("Requested decoder stage has no model for this target")
    results = {}
    for kind in sorted(requested - {"ufm_content"}):
        provider,record = models.load(target,kind)
        if record["cfm_bits"] != len(payload)*8:
            raise ValueError(f"CFM geometry differs for {kind}")
        results[kind] = decode_model(target,kind,provider,record,payload)
    if (stages is None or "ufm_content" in requested) and any(p.packet_id==0x0018 for p in pof.packets):
        provider,_ = models.load("*","ufm_content")
        results["ufm_content"] = decode_ufm(pof.section_payload(0x0018),provider)
    elif "ufm_content" in requested:
        raise ValueError("POF has no UFM content section")
    return {"format":"maxvell.storage_ir.v1","target":target,"input":summary,"stages":results,"unresolved_interfaces":OPEN_INTERFACES,"logical_nets_created":0,"productive_emission_allowed":False,"whole_design_equivalence":"unproved"}

def decode_model(target,kind,provider,record,payload):
    if kind in ('route_group_candidates','selector_qualification','lut_context_candidates'):
        from .research import decode as decode_research
        return decode_research(kind,provider,payload)
    if kind in ('ufm_source_sink_support','ufm_candidates'):
        from .ufm_support import decode as decode_ufm_support
        return decode_ufm_support(provider,payload)
    if kind in ("aload_sites","lut_topology","io_options"):
        from .scoped import decode as decode_scoped
        return decode_scoped(kind,provider,payload)
    if kind == "aload_candidates":
        from .scoped import bit,candidate_bindings
        if provider['cfm_bits'] != len(payload)*8:raise ValueError("ALOAD candidate geometry differs")
        return {"format":"maxvell.aload_candidate_ir.v2","offset_domain":"cfm_section_payload_lsb0",
                "candidate_bits":[{**r,"packet_payload_offset":r['payload_offset'],"payload_offset":offset,"raw_value":bit(payload,offset)} for r,offset in candidate_bindings(provider)],
                "canonical_ir_allowed":False,"productive_emission_allowed":False}
    if kind == "ufm_recipe":
        return {"format":"maxvell.ufm_recipe_catalog.v1","recipes":len(provider["recipes"]),"classification":"requires POF section headers and packet geometry; use ufm command","productive_emission_allowed":False}
    if kind == "functional":
        from .functional import selector_ir
        return selector_ir(target,payload,provider)
    if kind == "global_clock":
        from .functional import global_clock_ir
        return global_clock_ir(provider,payload)
    if kind == "lut":
        return {"cells":decode_lut(provider,payload),"input_connectivity":"unresolved","mask_order":"normalized native ordinal"}
    if kind == "lut_semantics":
        return {"cells":decode_semantic_lut(provider,payload),"input_connectivity":"unresolved","mask_order":"logical minterm"}
    if kind == "lc_bundle":
        from .analysis import lc_fields
        fields=lc_fields(target,payload,provider)
        return {"format":"maxvell.lc_bundle_ir.v1","fields":[{**f,"terms":[t+[payload[t[3]//8]>>(t[3]%8)&1,(payload[t[3]//8]>>(t[3]%8)&1)^t[4]] for t in f["terms"]]} for f in fields],"excluded_fields":provider["excluded_fields"],"productive_emission_allowed":False}
    module = import_module("maxvell._core." + record["decoder_module"])
    return getattr(module,record["decoder_function"])(provider,payload)

def write_json(path: Path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
