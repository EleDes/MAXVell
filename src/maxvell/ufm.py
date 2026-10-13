"""Content extraction and explicitly bounded serial/parallel UFM recipes."""
import hashlib
import json
from pathlib import Path
from . import models
from .decode import inspect,decode_ufm,write_json

def recipe_projection(pof,signature_format):
    cfm=pof.section(17);ufm=pof.section(24)
    value={"format":signature_format,"device":pof.text_packet(2),"packet_ids":[p.packet_id for p in pof.packets],
        "packet_lengths":[p.length for p in pof.packets],"cfm_bit_length":cfm.bit_length,"cfm_header_hex":cfm.header_hex,
        "cfm_payload_sha256":cfm.payload_sha256,"ufm_bit_length":ufm.bit_length,"ufm_header_hex":ufm.header_hex}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def content(path,selected_target=None):
    pof,summary=inspect(Path(path),selected_target)
    return _content(pof,summary)

def _content(pof,summary):
    provider,_=models.load("*","ufm_content")
    result=decode_ufm(pof.section_payload(24),provider)
    return {**result,"target":summary["target"]}

def mif(words):
    if len(words)!=512 or any(type(v) is not int or not 0<=v<=65535 for v in words):raise ValueError("UFM requires 512 16-bit words")
    return 'WIDTH=16;\nDEPTH=512;\n\nADDRESS_RADIX=HEX;\nDATA_RADIX=HEX;\n\nCONTENT BEGIN\n'+''.join(f'  {i:03X} : {v:04X};\n' for i,v in enumerate(words))+'END;\n'

def classify(path,selected_target=None):
    pof,summary=inspect(Path(path),selected_target);target=summary["target"]
    result=_content(pof,summary)
    if not any(packet.packet_id==17 for packet in pof.packets):
        return {**result,"recipe_status":"no_cfm_section","recipe":None}
    try:value,_=models.load(target,"ufm_recipe")
    except ValueError:return {**result,"recipe_status":"no_target_recipe","recipe":None}
    rows=[r for r in value["recipes"] if recipe_projection(pof,r["signature_format"])==r["recipe_key"]]
    if len(rows)>1:raise ValueError("UFM recipe classification is ambiguous")
    return {**result,"recipe_status":"matched_cfm_recipe" if rows else "unrecognized_cfm_recipe","recipe":rows[0] if rows else None}

def emit(path,out,selected_target=None,bind_pins=False):
    return _emit_result(classify(path,selected_target),out,bind_pins)

def _emit_result(result,out,bind_pins=False):
    if result["recipe"] is None:raise ValueError("POF does not match an included target-specific UFM recipe")
    target=result["target"];recipe=result["recipe"]
    included=models.load(target,"ufm_recipe")[0]["recipes"]
    if result.get("recipe_status")!="matched_cfm_recipe" or recipe not in included:raise ValueError("UFM classification differs from included recipe")
    files={"top.v":recipe["verilog"],"ufm_init.mif":mif(result["words"]),"top.qpf":'PROJECT_REVISION = "top"\n',
        "top.qsf":f'set_global_assignment -name FAMILY "MAX V"\nset_global_assignment -name DEVICE {target}\nset_global_assignment -name TOP_LEVEL_ENTITY top\nset_global_assignment -name VERILOG_FILE top.v\nset_global_assignment -name MIF_FILE ufm_init.mif\n'}
    if bind_pins:
        import re
        pins=recipe.get("pin_bindings")
        if not pins or len(set(pins.values()))!=len(pins):raise ValueError("This UFM recipe has no unique included physical pin map")
        for port,pin in pins.items():
            if not re.fullmatch(r"[A-Za-z0-9_]+",port) or not re.fullmatch(r"PIN_[A-Z]{0,2}\d+",pin):raise ValueError("Invalid UFM pin binding")
            files["top.qsf"]+=f'set_location_assignment {pin} -to {port}\n'
    files['top.qsf']+='set_global_assignment -name NUM_PARALLEL_PROCESSORS 1\nset_global_assignment -name RESERVE_ALL_UNUSED_PINS "AS INPUT TRI-STATED"\n'
    out=Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):raise ValueError("UFM project output directory must be empty")
    out.mkdir(parents=True,exist_ok=True)
    for name,text in files.items():(out/name).write_text(text,encoding="ascii",newline="\n")
    manifest={"format":"maxvell.ufm_project.v1","target":target,"interface_kind":recipe["interface_kind"],
        "access_mode":recipe.get("access_mode"),"recipe_status":result["recipe_status"],
        "files":{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in files},
        "physical_pin_assignments_applied":bool(bind_pins),"compile_verified":False,"whole_design_equivalence_verified":False,
        "productive_emission_allowed":False,"scope":"Matched CFM recipe and recovered UFM content; explicit primitive interface, no inferred surrounding logic"}
    write_json(out/"manifest.json",manifest)
    return {k:v for k,v in manifest.items() if k!="files"}
