"""Render explicit partial projects without operational-store dependencies."""
from pathlib import Path
import hashlib
import re
from . import models
from .decode import write_json
from ._core import state_control_project as native
from ._core.native_feedback_class_v3 import classify

def emit(model,out:Path,bind_pins=False):
    target=model.get("target")
    if not isinstance(target,str) or not re.fullmatch(r"5M\d+Z[A-Z]\d+[ACI]\d",target) or not models.catalog(target):
        raise ValueError("Unsupported exact target")
    if model.get("productive_emission_allowed") is not False or model.get("original_equivalence_verified") is not False:
        raise ValueError("Explicit partial-model flags required")
    admission=native.check(model)
    classify(model)
    files={"recovered.v":native.render(model),"recovered.qpf":'PROJECT_REVISION = "recovered"\n',
        "recovered.qsf":f'set_global_assignment -name FAMILY "MAX V"\nset_global_assignment -name DEVICE {target}\nset_global_assignment -name TOP_LEVEL_ENTITY recovered\nset_global_assignment -name VERILOG_FILE recovered.v\n'}
    if "usercode" in model:
        value=model["usercode"]
        if type(value) is not int or not 0<=value<=0xffffffff:raise ValueError("USER_CODE must be a 32-bit integer")
        files["recovered.qsf"]+=f'set_global_assignment -name USE_CHECKSUM_AS_USERCODE Off\nset_global_assignment -name STRATIX_JTAG_USER_CODE {value:08X}\n'
    files['recovered.qsf']+='set_global_assignment -name NUM_PARALLEL_PROCESSORS 1\nset_global_assignment -name RESERVE_ALL_UNUSED_PINS "AS INPUT TRI-STATED"\n'
    if bind_pins:
        provider=models.load(target,"io_fields")[0]
        allowed={pad["location"]:pad["package_pin_names"][0] for pad in provider["pads"] if pad["bonded"] and len(pad["package_pin_names"])==1}
        for pin in model["pins"]:
            identity=pin["pin"]
            if not re.fullmatch(r"[A-Z]{0,2}\d+",identity) or allowed.get(pin.get("native_io"))!=identity:raise ValueError("Physical pin binding does not match the exact target model")
            files["recovered.qsf"]+=f'set_location_assignment PIN_{identity} -to p_{identity}\n'
    option_lines=[]
    if bind_pins and 'io_options' in model:
        from .scoped import qsf_lines
        option_lines=qsf_lines(model['io_options'],models.load(target,'io_options')[0],model['pins'])
        files['recovered.qsf']+=''.join(option_lines)
    out=Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):raise ValueError("Project output directory must be empty")
    out.mkdir(parents=True,exist_ok=True)
    for name,text in files.items():(out/name).write_text(text,encoding="ascii",newline="\n")
    write_json(out/"model.json",model)
    manifest={"format":"maxvell.partial_project.v1","target":target,"artifact_kind":"partial_functional_project",
        "files":{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in (*files,"model.json")},
        "class_id":admission["class_id"],"metrics":admission["metrics"],"outputs":admission["outputs"],"boundaries":model["boundaries"],
        "compile_verified":False,"original_equivalence_verified":False,"productive_emission_allowed":False,
        "physical_pin_assignments_applied":bool(bind_pins),"startup_state_inferred":False,"timing_equivalence_verified":False}
    manifest['io_option_assignments_applied']=len(option_lines)
    write_json(out/"manifest.json",manifest)
    return {k:manifest[k] for k in ("artifact_kind","target","metrics","compile_verified","original_equivalence_verified","physical_pin_assignments_applied")}
