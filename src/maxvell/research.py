"""Retained research interpretations without new-input or emission grants."""
# SPDX-License-Identifier: 0BSD
from collections import Counter

PARTS = {'route_group_candidates': ('5M1270ZT144C5', 208896),
         'selector_qualification': ('5M240ZT100C5', 53248),
         'lut_context_candidates': ('5M240ZT100C5', 53248)}
PORTS = ('DATAA', 'DATAB', 'DATAC', 'DATAD')


def bit(payload, offset):
    if type(offset) is not int or not 0 <= offset < len(payload)*8:
        raise ValueError('Research offset outside CFM section')
    return (payload[offset//8] >> (offset%8)) & 1


def common(kind, provider, payload):
    if kind not in PARTS or (provider.get('target'), provider.get('cfm_bits')) != PARTS[kind]:
        raise ValueError('Research model target/geometry differs')
    if provider.get('kind') != kind or provider.get('offset_domain') != 'cfm_section_payload_lsb0':
        raise ValueError('Research model kind/offset domain differs')
    if not isinstance(payload, bytes) or len(payload)*8 != provider['cfm_bits']:
        raise ValueError('Research input geometry differs')
    if any(provider.get(flag) is not False for flag in
           ('input_scope_verified', 'canonical_functional_ir_allowed', 'productive_emission_allowed')):
        raise ValueError('Research model grants unverified functionality')
    return {'format': f'maxvell.{kind}_ir.v1', 'target': provider['target'],
            'offset_domain': provider['offset_domain'], 'validation_scope': provider['validation_scope'],
            'input_scope_verified': False, 'source_identity_proved': False,
            'logical_nets_created': 0, 'canonical_functional_ir_allowed': False,
            'productive_emission_allowed': False}


def decode(kind, provider, payload):
    result = common(kind, provider, payload)
    if kind == 'route_group_candidates':
        if provider['offsets'] != [195184, 196208] or provider['route_element'] != 'C4_X15_Y8_N0':
            raise ValueError('Retained route-group binding differs')
        if provider['polarity'] != 'active_low' or provider['atomic_bit_ownership_proven'] is not False:
            raise ValueError('Route-group interpretation differs')
        values = [bit(payload, offset) for offset in provider['offsets']]
        consistent = values[0] == values[1]
        return {**result, 'route_element': provider['route_element'], 'offsets': provider['offsets'],
                'raw_values': values, 'state': ('candidate_present' if values[0] == 0 else 'candidate_absent')
                if consistent else 'blocked_duplicated_bit_disagreement',
                'candidate_present': values[0] == 0 if consistent else None,
                'atomic_bit_ownership_proven': False, 'historical_case_count': 8}
    if kind == 'selector_qualification':
        return {**result, **selectors(provider, payload)}
    return {**result, **contexts(provider, payload)}


def selectors(provider, payload):
    codes = provider['codes']
    if len(codes) != 4:
        raise ValueError('Selector field-code population differs')
    tables = []
    for rows in codes:
        if len(rows) != 18 or any(len(row) != 3 or any(type(v) is not int for v in row) for row in rows):
            raise ValueError('Selector code shape differs')
        table = {(a, b): position for a, b, position in rows}
        if set(table) != {(a, b) for a in range(6) for b in range(3)} or len(set(table.values())) != 18:
            raise ValueError('Selector code is incomplete or duplicated')
        tables.append(table)
    groups = [{tuple(row) for row in provider[key]} for key in
              ('controlled_classes', 'pairable_classes', 'unresolved_classes')]
    legal = {(i, position) for i, table in enumerate(tables) for position in table.values()}
    if [len(group) for group in groups] != [17, 36, 19] or set.union(*groups) != legal or any(
            groups[i] & groups[j] for i in range(3) for j in range(i)):
        raise ValueError('Retained selector-class qualification differs')
    fields = provider['fields']
    ids, offsets, rows = set(), set(), []
    for site, index, terms in fields:
        if type(index) is not int or index not in range(4) or (site, index) in ids or len(terms) != 9:
            raise ValueError('Selector instance duplicated or malformed')
        ids.add((site, index)); active = [[], []]
        for ordinal, term in enumerate(terms):
            if len(term) != 2 or type(term[1]) is not int or term[1] not in (0, 1) or term[0] in offsets:
                raise ValueError('Selector term duplicated or malformed')
            offsets.add(term[0])
            if bit(payload, term[0]) ^ term[1]:
                active[0 if ordinal < 6 else 1].append(ordinal if ordinal < 6 else ordinal-6)
        position = None; basis = None
        if active == [[], []]:
            state = 'inactive'
        elif len(active[0]) != 1 or len(active[1]) != 1:
            state = 'invalid_one_hot'
        else:
            position = tables[index][active[0][0], active[1][0]]
            group = (index, position)
            state = 'validated_active_class' if group in groups[0] | groups[1] else 'unresolved_legal_class'
            basis = 'controlled_route_replay' if group in groups[0] else 'train_holdout_pair' if group in groups[1] else 'legal_class_unresolved'
        rows.append({'site': site, 'field_index': index, 'port': PORTS[index],
                     'active_ordinals': active, 'selector_position': position,
                     'selector_state': state, 'class_validation_basis': basis,
                     'source_binding_status': 'unresolved', 'complete_route_alternatives_proved': False})
    sites = {site for site, _ in ids}
    if len(ids) != 960 or len(sites) != 240 or ids != {(site, i) for site in sites for i in range(4)}:
        raise ValueError('Selector instance population differs')
    return {'selector_instances': rows, 'summary': {'instance_count': 960, 'term_count': len(offsets),
            'controlled_class_count': 17, 'pairable_class_count': 36, 'validated_class_count': 53,
            'unresolved_class_count': 19, 'states': dict(Counter(row['selector_state'] for row in rows))}}


def permutation(values):
    if len(values) != 16 or any(type(v) is not int for v in values) or set(values) != set(range(16)):
        raise ValueError('LUT context transform is not a minterm bijection')
    return values


def offsets(kind, provider):
    """CFM addresses represented by one retained diagnostic surface."""
    if kind == 'route_group_candidates':
        values = set(provider['offsets'])
    elif kind == 'selector_qualification':
        values = {term[0] for _, _, terms in provider['fields'] for term in terms}
    elif kind == 'lut_context_candidates':
        values = {offset for _, terms, _, _, _ in provider['cells'] for offset in terms}
    else:
        raise ValueError('Unknown research surface')
    if provider.get('offset_domain') != 'cfm_section_payload_lsb0' or any(
            type(value) is not int or not 0 <= value < provider['cfm_bits'] for value in values):
        raise ValueError('Research coverage offsets differ')
    return values


def contexts(provider, payload):
    if provider['input_topology_verified'] is not False or provider['site_global_mapping_allowed'] is not False:
        raise ValueError('LUT context model grants unsupported topology')
    exact = {}
    for site, transform in provider['exact_sites']:
        if site in exact:
            raise ValueError('Retained LUT context site duplicated')
        exact[site] = permutation(transform)
    seen, offsets, cells = set(), set(), []
    for site, terms, transform, ports, segment in provider['cells']:
        if site in seen or len(terms) != 16 or len(set(terms)) != 16 or offsets & set(terms):
            raise ValueError('Controlled LUT context binding duplicated or malformed')
        if set(ports) != set(PORTS) or len(set(ports.values())) != 4 or type(segment) is not int or segment not in range(4):
            raise ValueError('Controlled LUT context port binding differs')
        seen.add(site); offsets.update(terms); permutation(transform)
        raw = [bit(payload, offset) for offset in terms]
        views = [{'context_kind': 'controlled_layout', 'segment_index': segment,
                  'physical_port_to_semantic_input': ports, 'native_to_context_minterm': transform}]
        if site in exact:
            views.append({'context_kind': 'retained_exact_site_codebook', 'native_to_context_minterm': exact[site]})
        for view in views:
            view.update(mask=f"{sum(value << view['native_to_context_minterm'][i] for i, value in enumerate(raw)):04X}",
                        selection_status='available_not_selected', input_topology_verified=False)
        cells.append({'quartus_lc': site, 'raw_native_ordinal_mask': f'{sum(value << i for i, value in enumerate(raw)):04X}',
                      'context_views': views})
    if len(seen) != 240 or len(exact) != 8 or not set(exact) <= seen:
        raise ValueError('Retained LUT context population differs')
    return {'cells': cells, 'controlled_context_sites': 240, 'retained_exact_context_sites': 8,
            'selected_context_view_count': 0, 'input_topology_verified': False,
            'site_global_mapping_allowed': False, 'historical_conflict_binding_count': 58,
            'historical_conflict_site_count': 6}
