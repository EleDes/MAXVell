"""Own exact-scope support models; no promotion of unknown functions."""
# SPDX-License-Identifier: 0BSD
import re


def bit(payload, offset):
    if type(offset) is not int or not 0 <= offset < len(payload)*8:
        raise ValueError("Scoped field offset outside payload")
    return (payload[offset//8] >> (offset%8)) & 1


def candidate_bindings(provider):
    """Normalize the v1 inventory's packet offsets past its 12-byte CFM prefix."""
    if provider['format'] != 'maxvell.aload_candidates.v1':
        raise ValueError("Unknown ALOAD candidate offset domain")
    rows = provider['candidate_bits']
    if any(type(r['payload_offset']) is not int for r in rows):
        raise ValueError("ALOAD candidate bindings differ")
    bindings = [(r,r['payload_offset']-96) for r in rows]
    offsets = {offset for row,offset in bindings}
    if len(offsets)!=len(rows) or any(not 0<=offset<provider['cfm_bits'] for offset in offsets):
        raise ValueError("ALOAD candidate bindings differ")
    return bindings


def decode(kind, provider, payload):
    if provider['cfm_bits'] != len(payload)*8:
        raise ValueError("Scoped model geometry differs")
    if kind == 'aload_sites':
        sites = provider['sites']
        if len(sites)!=1252 or len({s['quartus_lc'] for s in sites}) != len(sites) or len({s['payload_offset'] for s in sites})!=len(sites):
            raise ValueError("Duplicate ALOAD site")
        observations, nodes, edges = [], [], []
        for site in sites:
            lc, offsets = site['quartus_lc'], site['lut_offsets']
            if not re.fullmatch(r'LC_X\d+_Y\d+_N\d+', lc) or len(set(offsets)) != 16:
                raise ValueError("ALOAD site/LUT population differs")
            mask = sum(bit(payload,o) << i for i,o in enumerate(offsets))
            value = bit(payload,site['payload_offset'])
            if mask in (0,65535):
                continue
            state = 'positive' if value else 'unresolved'
            observations.append({'quartus_lc':lc,'raw_value':value,'connectivity_state':state})
            if value:
                source, sink = 'le_async_load_path:'+lc, 'le_input:'+lc+':ALOAD'
                nodes.extend([{'id':source,'kind':'le_async_load_data_path','quartus_lc':lc,'source_identity':'unresolved'},
                              {'id':sink,'kind':'le_input_port','quartus_lc':lc,'port':'ALOAD'}])
                edges.append({'src':source,'dst':sink,'kind':'le_async_load_active_high_aload_connectivity'})
        return {'format':'maxvell.aload_site_support_ir.v1','observations':observations,'nodes':nodes,'edges':edges,
                'canonical_support_ir_allowed':True,'canonical_functional_ir_allowed':False,
                'source_identity_proved':False,'event_behavior_proved':False,'negative_means_absent':False,
                'productive_emission_allowed':False}
    if kind == 'lut_topology':
        if len(provider['cells'])!=provider['cell_count']:
            raise ValueError("Topology cell population differs")
        cells = []
        for lc, terms in sorted(provider['cells'].items()):
            if len(terms)!=16 or {t[1] for t in terms}!=set(range(16)) or {t[2] for t in terms}!=set(range(16)) or len({t[0] for t in terms})!=16:
                raise ValueError("Topology minterm relabel is not bijective")
            physical = sum(bit(payload,o) << p for o,p,s in terms)
            semantic = sum(bit(payload,o) << s for o,p,s in terms)
            cells.append({'quartus_lc':lc,'physical_mask':f'{physical:04X}','retained_topology_mask':f'{semantic:04X}'})
        return {'format':'maxvell.retained_topology_lut_ir.v1','cells':cells,'scope':provider['scope'],
                'input_topology_verified':False,'source_connectivity_proved':False,'logical_nets_created':0,
                'productive_emission_allowed':False}
    if kind != 'io_options':
        raise ValueError("Unknown scoped model family")
    signature_rows=[{'offset':o,'required_raw':v,'raw_value':bit(payload,o)} for o,v in provider['signature']]
    signature = all(r['raw_value']==r['required_raw'] for r in signature_rows)
    fields = [{'kind':s['kind'],'offset':s['offset'],'raw_value':bit(payload,s['offset']),
               'active':bit(payload,s['offset'])==s['active_raw']} for s in provider['fields']]
    strengths = [s['active'] for s in fields if s['kind']=='ioe_current_strength_8ma_group_bit']
    active = {s['kind'] for s in fields if s['active']}
    blockers = []
    if len(set(strengths))>1: blockers.append('current_strength_group_bits_disagree')
    if {'ioe_bus_hold_bit','ioe_weak_pull_up_bit'} <= active: blockers.append('bus_hold_conflicts_with_weak_pull_up')
    return {'format':'maxvell.io_options_ir.v1','target':provider['target'],'pin':provider['pin'],
            'status':'not_applicable_exact_site' if not signature else 'blocked' if blockers else 'decoded_exact_site',
            'fields':fields,'blockers':blockers,'site_signature_matches':signature,'site_signature':signature_rows,
            'qsf_fragment_allowed':provider['qsf_fragment_allowed'] and signature and not blockers,
            'productive_emission_allowed':False}


def qsf_lines(result, provider, pins):
    """Bind qualified options only to an existing exact-target emitted pin."""
    if result['target']!=provider['target'] or result['pin']!=provider['pin']:
        raise ValueError("I/O option target/site differs")
    signatures=result['site_signature']
    if [(r['offset'],r['required_raw']) for r in signatures]!=[tuple(r) for r in provider['signature']] or any(type(r['raw_value']) is not int or r['raw_value'] not in (0,1) for r in signatures):
        raise ValueError("I/O option site signature differs")
    if result['site_signature_matches'] is not all(r['raw_value']==r['required_raw'] for r in signatures):
        raise ValueError("I/O option site signature differs")
    if not provider['qsf_fragment_allowed'] or not result['site_signature_matches']:
        return []
    matches = [p for p in pins if p['pin']==provider['pin']]
    if not matches:
        return []
    if len(matches)!=1:
        raise ValueError("I/O option pin is not unique")
    if result['blockers'] or not result['qsf_fragment_allowed']:
        raise ValueError("I/O option combination blocked")
    expected = [(s['kind'],s['offset']) for s in provider['fields']]
    if [(s['kind'],s['offset']) for s in result['fields']]!=expected:
        raise ValueError("I/O option field bindings differ")
    for row,spec in zip(result['fields'],provider['fields']):
        if type(row['raw_value']) is not int or row['raw_value'] not in (0,1) or row['active'] is not (row['raw_value']==spec['active_raw']):
            raise ValueError("I/O option value differs")
    active = {s['kind'] for s in result['fields'] if s['active']}
    strengths = [s['active'] for s in result['fields'] if s['kind']=='ioe_current_strength_8ma_group_bit']
    if len(set(strengths))>1 or {'ioe_bus_hold_bit','ioe_weak_pull_up_bit'}<=active:
        raise ValueError("I/O option combination blocked")
    pin = matches[0]
    released = pin.get('oe') == {'kind':'constant','value':0} or (
        pin['mode']=='open_drain' and pin.get('data') == {'kind':'constant','value':1})
    driven = pin['mode'] in ('push_pull','open_drain') and not released
    if provider['output_required'] and not driven:
        raise ValueError("I/O option requires the decoded output port")
    lines = []
    for kind in sorted(active):
        option = provider['assignments'][kind]
        if option['direction_gate']=='output_or_bidir' and not driven:
            continue
        lines.append(f"set_instance_assignment -name {option['assignment_name']} {option['assignment_value']} -to p_{provider['pin']}\n")
    return lines
