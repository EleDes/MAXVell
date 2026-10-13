"""Create two separate own-design Quartus experiments; invoke no vendor tools."""
# SPDX-License-Identifier: 0BSD
from pathlib import Path
import argparse
import json
import re


def prepare(out, target):
    if re.fullmatch(r"5M\d+Z[A-Z]\d+[ACI]\d", target) is None:
        raise ValueError("Supply an exact MAX V part")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Experiment output directory must be empty")
    source = Path(__file__).with_name("design.v").read_bytes()
    common = f'''set_global_assignment -name FAMILY "MAX V"
set_global_assignment -name DEVICE {target}
set_global_assignment -name TOP_LEVEL_ENTITY control_demo
set_global_assignment -name NUM_PARALLEL_PROCESSORS 1
set_global_assignment -name SEED 1
set_global_assignment -name VERILOG_FILE design.v
set_global_assignment -name SDC_FILE design.sdc
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name RESERVE_ALL_UNUSED_PINS "AS INPUT TRI-STATED"
'''
    if target == "5M1270ZT144C5":
        for port, pin in (("a", 4), ("b", 2), ("clk", 18), ("q0", 6), ("q1", 5)):
            common += f"set_location_assignment PIN_{pin} -to {port}\n"
            common += f'set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to {port}\n'
    controls = '''set_global_assignment -name VERILOG_MACRO MAXVELL_KEEP_STRUCTURE
set_global_assignment -name PHYSICAL_SYNTHESIS_COMBO_LOGIC OFF
set_global_assignment -name PHYSICAL_SYNTHESIS_REGISTER_DUPLICATION OFF
set_global_assignment -name PHYSICAL_SYNTHESIS_REGISTER_RETIMING OFF
set_global_assignment -name ADV_NETLIST_OPT_ALLOWED "NEVER ALLOW"
set_instance_assignment -name PRESERVE_REGISTER ON -to r0
set_instance_assignment -name PRESERVE_REGISTER ON -to r1
set_instance_assignment -name DONT_MERGE_REGISTER ON -to r0
set_instance_assignment -name DONT_MERGE_REGISTER ON -to r1
set_instance_assignment -name PRESERVE_FANOUT_FREE_NODE ON -to orphan
set_instance_assignment -name IMPLEMENT_AS_OUTPUT_OF_LOGIC_CELL ON -to probe_comb
'''
    timing = '''create_clock -name clk -period 20.000 [get_ports {clk}]
set_input_delay -clock clk -max 2.0 [get_ports {a b}]
set_input_delay -clock clk -min 0.5 [get_ports {a b}]
set_output_delay -clock clk -max 2.0 [get_ports {q0 q1}]
set_output_delay -clock clk -min 0.5 [get_ports {q0 q1}]
'''
    for name in ("baseline", "controlled"):
        folder = out / name
        folder.mkdir(parents=True)
        (folder / "design.v").write_bytes(source)
        (folder / "design.sdc").write_text(timing, encoding="ascii")
        (folder / f"{name}.qpf").write_text(f'PROJECT_REVISION = "{name}"\n', encoding="ascii")
        (folder / f"{name}.qsf").write_text(common + (controls if name == "controlled" else ""), encoding="ascii")
    return {"target": target, "projects": ["baseline", "controlled"], "quartus_invoked": False, "pins_locked": target == "5M1270ZT144C5", "placement_locked": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target", default="5M1270ZT144C5")
    args = parser.parse_args()
    print(json.dumps(prepare(args.out, args.target), sort_keys=True))
