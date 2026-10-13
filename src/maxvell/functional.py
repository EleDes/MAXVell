"""POF-driven partial LUT/state reconstruction from included result models."""
from collections import defaultdict
from pathlib import Path
from . import models
from .analysis import lc_fields
from .decode import inspect
from ._core.native_lc_input_join import predict
from ._core.native_io_port_expressions import decode as decode_io
from ._core.native_pin_pad_mode import decode_modes
from ._core.native_route_predicate_frontier import evaluate as select_routes
from ._core.native_source_output_role import resolve as source_role, identity
from ._core.native_lut_chain_candidate import binding as chain_binding
from ._core.native_register_feedback_binding_v3 import binding as feedback_binding
from ._core.native_feedback_register import register
from ._core.native_state_control_compose_v2 import compose
from ._core.native_partial_cone_v3 import validate_chain_fields
from ._core.native_control_source import graph_context
from ._core import native_io_storage as io, native_cff_io_storage as cff
from ._core import state_control_project as project
from ._core.native_feedback_class_v3 import classify

def unpack(value):
    if isinstance(value,list):return [unpack(x) for x in value]
    if isinstance(value,dict):
        if set(value)=={"__tuple__"}:return tuple(unpack(x) for x in value["__tuple__"])
        if set(value)=={"__pairs__"}:
            pairs=[(unpack(k),unpack(v)) for k,v in value["__pairs__"]]
            result=dict(pairs)
            if len(result)!=len(pairs):raise ValueError("Duplicate encoding key")
            return result
        return {k:unpack(v) for k,v in value.items()}
    return value

def context(target,payload):
    value,record=models.load(target,"functional")
    value=unpack(value)
    if value["target"]!=target or value["cfm_bits"]!=len(payload)*8 or record["cfm_bits"]!=len(payload)*8:
        raise ValueError("Functional context target/geometry differs")
    providers={io.CAPABILITY_ID:models.load(target,"io_fields")[0],cff.CAPABILITY_ID:models.load(target,"cff_io")[0]}
    resources=models.load(target,"route_mux")[0]["resources"]
    if len({r[0] for r in resources})!=len(resources):raise ValueError("Duplicate native resource")
    return {**value,"fields":lc_fields(target,payload),"providers":providers,"resources":resources}

def selector_ir(target,payload,provider=None):
    value=context(target,payload)
    result=predict(value["fields"],payload,value["lc_tables"],value["input_mapping"],value["resources"])
    result["named_port_mapping_scope"]="Included native transform; candidate connectivity requires input-specific comparison"
    return result

def reconstruct(path:Path,output_pins=None,selected_target=None):
    pof,summary=inspect(path,selected_target);target=summary["target"];payload=pof.section_payload(17)
    value=context(target,payload);global_provider=models.load(target,"global_clock")[0]
    fields=defaultdict(list)
    for field in value["fields"]:fields[field["location"]].append(field)
    def cell(lc):
        fs=fields.get(lc,[]);luts=[f for f in fs if f["class"]=="LE_LUT_FUNCTION"]
        if len(luts)!=1:raise ValueError("LUT field absent")
        terms=sorted(luts[0]["terms"],key=lambda t:t[1])
        if [(t[0],t[1]) for t in terms]!=[(0,i) for i in range(16)]:raise ValueError("LUT term shape differs")
        # The native functional transform consumes the raw serialized mask.
        # Storage-normalized ordinal masks have a different contract.
        mask=sum(((payload[t[3]//8]>>(t[3]%8))&1)<<t[1] for t in terms)
        rows=predict(fs,payload,value["lc_tables"],value["input_mapping"],value["resources"])["rows"]
        chain=chain_binding(lc,fs,payload,rows,mask)
        if chain is not None:rows.append(chain)
        edge=feedback_binding(lc,fs,payload,rows,mask)
        if edge is not None:rows=[r for r in rows if r["predicted_port"]!="DATAC"]+[edge]
        return {"mask":mask,"lut_terms":terms,"inputs":rows}
    normal=decode_io(value["providers"][io.CAPABILITY_ID]["fields"],payload,value["io_tables"])
    modes=decode_modes(value["providers"][cff.CAPABILITY_ID],payload)
    routes=select_routes(value["compiled"],payload,{r[0]:r for r in value["resources"]})
    graph=graph_context(value,payload);encodings=value["clock_encoding"],value["control_encoding"]
    model=compose(normal,modes,value["resources"],routes["sink_results"],cell,
        lambda r:source_role(r,fields.get(identity(r)[0],[]),payload),
        lambda lc:register(value,payload,lc,global_provider,encodings,graph))
    validate_chain_fields(model,value["fields"])
    model.update(target=target,input=summary,artifact_kind="partial_functional_model",
        named_port_transform="native functional transform",
        startup_state="caller supplied",event_scope="settled binary single-input events",
        timing_equivalence_verified=False,compile_verified=False)
    from ._core.native_user_code_storage import decode_provider
    model["usercode"]=decode_provider(models.load(target,"usercode")[0],payload)["value"]
    if any(r['kind']=='io_options' for r in models.catalog(target)):
        from .scoped import decode as decode_scoped
        model['io_options']=decode_scoped('io_options',models.load(target,'io_options')[0],payload)
    if output_pins:
        from ._core.state_control_output_cone import extract
        model=extract(model,output_pins)
    model["control_class"]=classify(model)
    admission=project.check(model)
    model["assessment"]={"class_id":admission["class_id"],"metrics":admission["metrics"],"outputs":admission["outputs"]}
    return model

def global_clock_ir(provider,payload):
    from ._core.native_global_clock_v2 import mux_selection
    rows=[]
    for index in range(4):
        try:rows.append({**mux_selection(provider,payload,index),"status":"unique_selector"})
        except ValueError as exc:rows.append({"index":index,"status":"unresolved","reason":str(exc)})
    return {"format":"maxvell.global_clock_storage.v1","selectors":rows,"clock_connections_created":0,"productive_emission_allowed":False}
