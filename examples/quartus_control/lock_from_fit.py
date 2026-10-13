"""Copy this demo's source project and pin its three observed register locations."""
# SPDX-License-Identifier: 0BSD
from pathlib import Path
import argparse
import json
import re


def prepare(project, out):
    locations = {}
    for line in (project / "node_loc.loc").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 2 or re.fullmatch(r"LC_X\d+_Y\d+_N\d+", fields[1]) is None:
            raise ValueError("Unexpected fitted-node location record")
        if fields[0] in locations:
            raise ValueError("Duplicate fitted node")
        locations[fields[0]] = fields[1]
    if set(locations) != {"r0", "r1", "orphan"} or len(set(locations.values())) != 3:
        raise ValueError("Expected three distinct preserved register locations")
    qsf = (project / "controlled.qsf").read_text(encoding="ascii")
    if "set_location_assignment LC_" in qsf:
        raise ValueError("Source already contains logic-cell locks")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Locked project output directory must be empty")
    source = {name: (project / name).read_bytes() for name in ("design.v", "design.sdc", "controlled.qpf")}
    out.mkdir(parents=True, exist_ok=True)
    for name, raw in source.items():
        (out / name).write_bytes(raw)
    locks = "".join(f"set_location_assignment {location} -to {name}\n" for name, location in sorted(locations.items()))
    (out / "controlled.qsf").write_text(qsf + "\n" + locks, encoding="ascii")
    return {"project": "controlled", "logic_cell_locks": locations, "compiled_database_copied": False, "quartus_invoked": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.project, args.out), sort_keys=True))
