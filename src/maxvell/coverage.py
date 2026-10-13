"""Set-based storage accounting; never a functional-completion percentage."""
from html import escape
from . import models

def ranges(offsets):
    result=[]
    for offset in sorted(offsets):
        if result and result[-1][0]+result[-1][1]==offset:result[-1][1]+=1
        else:result.append([offset,1])
    return result

def family_offsets(target,kind,provider=None):
    provider=provider or models.load(target,kind)[0]
    if kind in ('route_group_candidates','selector_qualification','lut_context_candidates'):
        from .research import offsets as research_offsets
        return research_offsets(kind,provider)
    if kind in ("lut","lut_semantics"):return {r["pof_payload_offset"] for r in provider["rows"]}
    if kind=="input_selectors":return {r[5] for r in provider["rows"]}
    if kind in ("usercode","h4_v4","route_mux","remaining_mux","source_exclusions"):return {r[1] for r in provider["bindings"]}
    if kind=="cff_io":return {r[0] for r in provider["bindings"].values()}
    if kind in ("le_lab_controls","device_fields","io_fields","outside_legal","global_clock"):return {t[3] for f in provider["fields"] for t in f["terms"]}
    if kind=="lc_bundle":return {t[3] for f in provider["extensions"] for t in f["terms"]}
    if kind=="functional":
        from .functional import unpack
        value=unpack(provider)
        return {offset for row in value["compiled"] for key in ("destination","assembled") for offset,bit in row[key]}
    if kind=="legacy_fields":return {t[3] for f in provider["fields"] for t in f["terms"]}
    if kind=="ufm_recipe":return set()
    if kind=="aload_candidates":
        from .scoped import candidate_bindings
        return {offset for row,offset in candidate_bindings(provider)}
    if kind=="aload_sites":return {o for s in provider['sites'] for o in [s['payload_offset'],*s['lut_offsets']]}
    if kind=="lut_topology":return {t[0] for terms in provider['cells'].values() for t in terms}
    if kind=="io_options":return {s['offset'] for s in provider['fields']}|{s[0] for s in provider['signature']}
    if kind in ('ufm_source_sink_support','ufm_candidates'):
        from .ufm_support import offsets as ufm_offsets
        return ufm_offsets(provider)
    raise ValueError("Unknown storage accounting family: "+kind)

def offsets(target):
    specs=models.catalog(target)
    if not specs:raise ValueError("Unsupported exact target")
    sizes={r["cfm_bits"] for r in specs}
    if len(sizes)!=1:raise ValueError("Model CFM sizes conflict")
    bits=sizes.pop();families={r["kind"]:family_offsets(target,r["kind"]) for r in specs}
    if any(type(n) is not int or not 0<=n<bits for values in families.values() for n in values):raise ValueError("Storage accounting offset outside CFM")
    return bits,families,set().union(*families.values())

def coverage(target):
    bits,families,union=offsets(target)
    return {"format":"maxvell.storage_coverage.v1","target":target,"cfm_bits":bits,"mapped_storage_bits":len(union),
        "unmapped_storage_bits":bits-len(union),"mapped_storage_percent":round(100*len(union)/bits,3),
        "families":{k:len(v) for k,v in sorted(families.items())},"unmapped_ranges":ranges(set(range(bits))-union),
        "ufm_content_bits":8192,"counting_rule":"Union of serialized offsets addressed by included technical models; families overlap",
        "functional_completion_percent":None,"whole_design_equivalence":"unproved"}

def svg(report):
    total=report["cfm_bits"];mapped=report["mapped_storage_bits"];width=700*mapped/total
    title=escape(report["target"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 220" role="img" aria-labelledby="title desc">
<title id="title">{title} CFM storage accounting</title><desc id="desc">{mapped} of {total} serialized bits are addressed by included models. This does not measure functional reconstruction.</desc>
<rect width="800" height="220" fill="#f8fafc"/><g font-family="sans-serif" fill="#14283d">
<text x="50" y="45" font-size="24">{title} · CFM storage</text>
<rect x="50" y="70" width="700" height="40" rx="4" fill="#dce3eb"/><rect x="50" y="70" width="{width:.3f}" height="40" rx="4" fill="#087e8b"/>
<text x="50" y="140" font-size="17">Mapped: {mapped:,} / {total:,} bits ({100*mapped/total:.2f}%)</text>
<text x="50" y="168" font-size="17">Unmapped: {total-mapped:,} bits · UFM content: 8,192 separate bits</text>
<text x="50" y="198" font-size="14">Overlapping families are counted once. Functional completeness is not implied.</text></g></svg>'''
