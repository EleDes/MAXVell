"""Non-promoting native configuration candidates from included models."""
from collections import defaultdict
from pathlib import Path
from . import models
from .decode import inspect
from ._core.native_lc_field_bundle import validate_fields
from ._core.native_route_predicate_frontier import compile_predicates,evaluate
from ._core.native_aload_predicate import predict as aload
from ._core.native_sync_normalization import predict as sync
from ._core.native_source_output_role import resolve

def lc_fields(target,payload,bundle=None):
    bundle=bundle or models.load(target,"lc_bundle")[0]
    lut=models.load(target,"lut")[0]
    selectors=models.load(target,"input_selectors")[0]
    controls=models.load(target,"le_lab_controls")[0]
    grouped=defaultdict(list)
    for row in lut["rows"]:
        grouped[row["lc_location"]].append([0,row["asmdb_lut_ordinal"],row["native_address"],row["pof_payload_offset"],row["native_serializer_xor"]])
    fields=[{"location":loc,"class":"LE_LUT_FUNCTION","index":"none","shape":[16],"terms":sorted(rows),"sentinels":[]} for loc,rows in grouped.items()]
    grouped=defaultdict(list)
    for loc,index,stage,ordinal,address,offset,xor in selectors["rows"]:
        grouped[loc,str(index)].append([stage,ordinal,address,offset,xor])
    fields.extend({"location":loc,"class":"LE_LUT_INPUT","index":index,"shape":[6,3],"terms":sorted(rows),"sentinels":[]} for (loc,index),rows in grouped.items())
    fields.extend(controls["fields"])
    if bundle["retained_field_count"] != len(fields):raise ValueError("Retained LC field population differs")
    fields.extend(bundle["extensions"])
    ids,bits=validate_fields(fields,len(payload)*8)
    excluded={(f["location"],f["class"],f["index"]) for f in bundle["excluded_fields"]}
    if bundle["cfm_bits"]!=len(payload)*8 or len(ids)!=bundle["full_field_count"] or len(bits)!=bundle["unique_bits"] or len(excluded)!=len(bundle["excluded_fields"]) or ids & excluded or len(ids)+len(excluded)!=bundle["expected_field_count"]:
        raise ValueError("Full LC bundle population differs")
    return fields

def route_candidates(target,payload):
    bindings={};fields=[];excluded=[];resources={};exclusions={}
    for kind in ("route_mux","h4_v4","remaining_mux","source_exclusions"):
        provider,record=models.load(target,kind)
        from .decode import decode_model
        decode_model(target,kind,provider,record,payload)
        for row in provider["resources"]:
            if row[0] in resources and resources[row[0]]!=row:raise ValueError("Native resource domains conflict")
            resources[row[0]]=row
        for address,offset,xor in provider["bindings"]:
            if address in bindings and bindings[address]!=(offset,xor):raise ValueError("Native route bindings conflict")
            bindings[address]=(offset,xor)
        if kind == "source_exclusions":
            exclusions={gid:[] for gid in provider["no_source_exclusion_gids"]}
            for f in provider["fields"]:exclusions.setdefault(f["source_gid"],[]).append(f["bits"])
            for f in provider["excluded_fields"]:exclusions.pop(f["source_gid"],None)
        else:
            fields.extend(provider["fields"]);excluded.extend(provider["excluded_fields"])
    rows=compile_predicates(fields,exclusions,bindings,len(payload)*8)
    for f in excluded:
        rows.append({"source_gid":f["source_gid"],"sink_gid":f["sink_gid"],"constant_destination":False,"source_conditions_known":False,"destination":[],"assembled":[],"destination_missing":[-1],"assembled_missing":[-1]})
    result=evaluate(rows,payload,resources)
    result["excluded_candidate_count"]=len(excluded)
    result["unique_match_meaning"]="configuration candidate; not a proved logical connection"
    return result,resources

def analyze(path: Path,selected_target=None):
    pof,summary=inspect(path,selected_target);target=summary["target"];payload=pof.section_payload(0x11)
    fields=lc_fields(target,payload)
    routes,resources=route_candidates(target,payload)
    roles=[]
    for resource in resources.values():
        if resource[1] in (43,45):
            try:roles.append(resolve(resource,fields,payload))
            except ValueError:continue
    controls=[]
    for lc in sorted({f["location"] for f in fields if f["class"]=="LE_LUT_FUNCTION"}):
        row={"native_lc":lc}
        for label,reader in (("aload",aload),("sync",sync)):
            try:row[label]=reader(fields,payload,lc)
            except (ValueError,KeyError) as error:row[label]={"status":"unresolved","reason":str(error)}
        controls.append(row)
    return {"format":"maxvell.candidate_ir.v1","target":target,"input":summary,"routes":routes,"source_roles":roles,"controls":controls,"named_port_order_proved":False,"logical_nets_created":0,"productive_emission_allowed":False,"whole_design_equivalence":"unproved"}
