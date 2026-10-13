"""Emit explicit LUT-only project drafts with named unresolved input ports."""
from pathlib import Path
import re
from .decode import write_json
from . import models

def emit_lut(ir,out: Path,cell: str | None = None,view="logical"):
    if ir.get("format")!="maxvell.storage_ir.v1" or ir.get("productive_emission_allowed") is not False:
        raise ValueError("An explicitly partial storage IR is required")
    if view not in ('logical','retained-topology'):raise ValueError('Unknown LUT truth view')
    if view=='retained-topology':
        data=ir.get('stages',{}).get('lut_topology',{})
        if data.get('input_topology_verified') is not False or data.get('source_connectivity_proved') is not False:raise ValueError('Explicit topology limits required')
        cells=[{'native_location':r['quartus_lc'],'logical_minterm_mask':r['retained_topology_mask']} for r in data.get('cells',[])]
    else:cells = ir.get("stages",{}).get("lut_semantics",{}).get("cells",[])
    selected = [row for row in cells if cell is None or row["native_location"]==cell]
    if not selected:
        raise ValueError("No checked logical-minterm LUT model for the requested cell/target")
    target=ir.get("target","")
    if view=='logical' and target not in ("5M40ZE64C5","5M80ZE64C5"):
        raise ValueError("No logical-minterm emission model for this exact target")
    allowed=set(models.load(target,'lut_topology')[0]['cells']) if view=='retained-topology' else {row["lc_location"] for row in models.load(target,"lut_semantics")[0]["rows"]}
    modules=[]
    locations=set()
    for index,row in enumerate(selected):
        mask = row["logical_minterm_mask"]
        location=row["native_location"]
        if not re.fullmatch(r"[0-9A-F]{4}",mask) or location not in allowed or location in locations:
            raise ValueError("Invalid LUT mask")
        locations.add(location)
        modules.append(f"// Native location: {location}; no Quartus placement binding.\nmodule maxvell_lut_{index}(input wire [3:0] unresolved_native_input, output wire native_combout);\n  localparam [15:0] MASK = 16'h{mask};\n  assign native_combout = MASK[unresolved_native_input];\nendmodule\n")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory must be empty")
    out.mkdir(parents=True,exist_ok=True)
    (out/"cells.v").write_text("// Explicit partial draft; whole-design equivalence is unproved.\n"+"\n".join(modules),encoding="utf-8")
    # One cell is the project top; additional cell modules are separate interfaces.
    (out/"partial.qpf").write_text('PROJECT_REVISION = "partial"\n',encoding="utf-8")
    (out/"partial.qsf").write_text(f'set_global_assignment -name FAMILY "MAX V"\nset_global_assignment -name DEVICE {target}\nset_global_assignment -name TOP_LEVEL_ENTITY maxvell_lut_0\nset_global_assignment -name VERILOG_FILE cells.v\n',encoding="utf-8")
    summary={"format":"maxvell.partial_project.v1","target":target,"cell_modules":len(selected),"project_top":"maxvell_lut_0","closed_path":"one LUT truth table between explicit native inputs and native_combout","unresolved_interfaces":["input net sources","output sink wiring","package pins","Quartus LC placement","other logic/state"],"productive_emission_allowed":False,"whole_design_equivalence":"unproved","quartus_compile":"not_run"}
    with (out/'partial.qsf').open('a',encoding='utf-8') as handle:
        handle.write('set_global_assignment -name NUM_PARALLEL_PROCESSORS 1\nset_global_assignment -name RESERVE_ALL_UNUSED_PINS "AS INPUT TRI-STATED"\n')
    summary['truth_view']=view
    if view=='retained-topology':summary['scope']='Conditional cell truth tables under retained input relabels; source wiring and new-input topology unverified'
    write_json(out/"project.json",summary)
    return summary
