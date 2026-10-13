from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sqlite3
import sys
from . import models
from .decode import decode,inspect,write_json
from .emit import emit_lut

def demo(out: Path):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Demo output directory must be empty")
    out.mkdir(parents=True,exist_ok=True)
    target="5M40ZE64C5"
    provider,record=models.load(target,"lut_semantics")
    payload=bytearray(record["cfm_bits"]//8)
    location=sorted({row["lc_location"] for row in provider["rows"]})[0]
    mask=0x6996
    for row in provider["rows"]:
        if row["lc_location"]==location:
            value=((mask >> row["logical_minterm"]) & 1)^row["polarity"]
            if value:payload[row["pof_payload_offset"]//8] |= 1 << (row["pof_payload_offset"]%8)
    section=bytearray(12)
    struct.pack_into("<I",section,6,len(payload)*8)
    packets=[(2,target.encode()+b"\0"),(0x11,bytes(section)+payload)]
    raw=b"POF\0"+struct.pack("<II",1,len(packets))+b"".join(struct.pack("<HI",tag,len(value))+value for tag,value in packets)
    path=out/"synthetic.pof"
    path.write_bytes(raw)
    ir=decode(path,["lut","lut_semantics","usercode"])
    write_json(out/"storage_ir.json",ir)
    result=emit_lut(ir,out/"partial_project",location)
    actual=next(row["logical_minterm_mask"] for row in ir["stages"]["lut_semantics"]["cells"] if row["native_location"]==location)
    if actual!=f"{mask:04X}":
        raise ValueError("Synthetic end-to-end LUT decode differs")
    return {"synthetic":True,"target":target,"logical_mask":actual,"decoded_cell":location,"cell_modules":result["cell_modules"],"hardware_validation":False}

def main(argv=None):
    parser=argparse.ArgumentParser(prog="maxvell",description="Self-contained MAX V result decoders and partial reconstruction tools")
    from . import __version__
    parser.add_argument("--version",action="version",version=f"MAXVell {__version__}")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("status",help="Bounded snapshot status")
    p=sub.add_parser("models",help="List model families/targets");p.add_argument("--target");p.add_argument("--out",type=Path)
    p=sub.add_parser("query",help="Read the included schema, bounded SQL results or a verified model")
    q=p.add_subparsers(dest="query_kind",required=True)
    q.add_parser("schema")
    s=q.add_parser("sql");s.add_argument("statement");s.add_argument("--params",default="[]");s.add_argument("--limit",type=int,default=50);s.add_argument("--out",type=Path)
    s=q.add_parser("model");s.add_argument("--target",required=True);s.add_argument("--kind",required=True);s.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("coverage",help="Unique mapped/unmapped CFM offsets");p.add_argument("--target",required=True);p.add_argument("--out",type=Path);p.add_argument("--svg",type=Path)
    p=sub.add_parser("inspect",help="POF structure without creator/comments");p.add_argument("pof",type=Path)
    p=sub.add_parser("decode",help="Decode to typed storage IR");p.add_argument("pof",type=Path);p.add_argument("--stages",help="Comma-separated stages; default all available");p.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("analyze",help="Native route/role/control candidates");p.add_argument("pof",type=Path);p.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("reconstruct",help="POF to partial functional IR and optional Quartus draft");p.add_argument("pof",type=Path);p.add_argument("--output-pin",action="append");p.add_argument("--out",type=Path,required=True);p.add_argument("--project",type=Path)
    p=sub.add_parser("emit-project",help="Partial functional IR to Quartus draft");p.add_argument("ir",type=Path);p.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("ufm",help="Recover UFM words/MIF and classify bounded CFM recipes");p.add_argument("pof",type=Path);p.add_argument("--target");p.add_argument("--out",type=Path,required=True);p.add_argument("--mif",type=Path);p.add_argument("--project",type=Path)
    p=sub.add_parser("simulate",help="Step an explicit sequential model");p.add_argument("model",type=Path);p.add_argument("stimulus",type=Path);p.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("emit-lut",help="LUT-only partial project draft");p.add_argument("ir",type=Path);p.add_argument("--cell");p.add_argument("--out",type=Path,required=True)
    p.add_argument('--view',choices=('logical','retained-topology'),default='logical',help='Explicit truth view; retained topology does not prove source wiring')
    p=sub.add_parser("demo",help="Synthetic POF -> IR -> partial project");p.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("demo-functional",help="Synthetic feedback POF -> functional IR -> partial project");p.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("validate",help="Integrity/privacy/schema checks");p.add_argument("--out",type=Path)
    for name in ("inspect","decode","analyze","reconstruct"):
        sub.choices[name].add_argument("--target",help="Exact part when the POF contains only a die name")
    for name in ("reconstruct","emit-project","ufm"):
        sub.choices[name].add_argument("--bind-pins",action="store_true",help="Apply only included exact-target physical pin bindings to the draft")
    args=parser.parse_args(argv)
    if args.command in ("reconstruct","ufm") and args.bind_pins and args.project is None:
        parser.error("--bind-pins requires --project")
    try:
        if args.command=="status":result=models.status()
        elif args.command=="models":
            rows=models.catalog(args.target)
            if args.target and not rows:raise ValueError("Unsupported exact target")
            if args.out:write_json(args.out,{"models":rows})
            result={"model_rows":len(rows),"targets":len({r['target'] for r in rows}),"kinds":sorted({r['kind'] for r in rows})}
        elif args.command=="query":
            from .query import schema,sql
            if args.query_kind=="schema":result=schema()
            elif args.query_kind=="model":
                value,record=models.load(args.target,args.kind);write_json(args.out,value)
                result={"target":args.target,"kind":args.kind,"format":value["format"],"stored_json_bytes":record["json_bytes"],"checksum_verified":True}
            else:
                result=sql(args.statement,json.loads(args.params),args.limit,1048576 if args.out else 16384)
                if args.out:
                    write_json(args.out,result);result={k:v for k,v in result.items() if k not in ("rows","columns")}
        elif args.command=="inspect":_,result=inspect(args.pof,args.target)
        elif args.command=="coverage":
            from .coverage import coverage,svg
            result=coverage(args.target)
            if args.out:write_json(args.out,result)
            if args.svg:
                args.svg.parent.mkdir(parents=True,exist_ok=True);args.svg.write_text(svg(result),encoding="utf-8")
            result={k:v for k,v in result.items() if k not in ("unmapped_ranges","families")}
        elif args.command=="decode":
            ir=decode(args.pof,args.stages.split(",") if args.stages else None,args.target);write_json(args.out,ir)
            result={"target":ir["target"],"stages":sorted(ir["stages"]),"logical_nets_created":0,"productive_emission_allowed":False}
        elif args.command=="analyze":
            from .analysis import analyze
            ir=analyze(args.pof,args.target);write_json(args.out,ir)
            result={"target":ir["target"],"route_candidates":ir["routes"]["pair_count"],"cell_count":len(ir["controls"]),"productive_emission_allowed":False}
        elif args.command=="reconstruct":
            from .functional import reconstruct
            ir=reconstruct(args.pof,args.output_pin,args.target)
            result={"target":ir["target"],**ir["assessment"]["metrics"],"productive_emission_allowed":False}
            if args.project:
                from .project import emit
                result["project"]=emit(ir,args.project,args.bind_pins)
            write_json(args.out,ir)
        elif args.command=="emit-project":
            from .project import emit
            result=emit(json.loads(args.ir.read_text(encoding="utf-8")),args.out,args.bind_pins)
        elif args.command=="ufm":
            from .ufm import classify,mif,_emit_result
            ir=classify(args.pof,args.target)
            result={"target":ir["target"],"word_count":ir["word_count"],"recipe_status":ir["recipe_status"],"productive_emission_allowed":False}
            if args.project:result["project"]=_emit_result(ir,args.project,args.bind_pins)
            write_json(args.out,ir)
            if args.mif:
                args.mif.parent.mkdir(parents=True,exist_ok=True);args.mif.write_text(mif(ir["words"]),encoding="ascii",newline="\n")
        elif args.command=="simulate":
            from .simulation import simulate
            result=simulate(json.loads(args.model.read_text(encoding="utf-8")),json.loads(args.stimulus.read_text(encoding="utf-8")))
            write_json(args.out,result)
            result={"steps":len(result["steps"]),"independent_equivalence_proved":False}
        elif args.command=="emit-lut":result=emit_lut(json.loads(args.ir.read_text()),args.out,args.cell,args.view)
        elif args.command=="demo":result=demo(args.out)
        elif args.command=="demo-functional":
            from .examples import demo_functional
            result=demo_functional(args.out)
        else:
            from .validation import validate
            result=validate()
            if args.out:write_json(args.out,result)
            if result["status"]!="passed":print(json.dumps(result));return 1
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as error:
        print(str(error),file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0
