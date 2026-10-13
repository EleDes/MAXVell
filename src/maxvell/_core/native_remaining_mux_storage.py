# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from collections import Counter
FORMAT = 'maxvrec.native_remaining_mux_storage_provider.v1'

def validate_provider(p):
    if p.get('format') != FORMAT or p.get('functional_routes_proved') is not False or p.get('productive_emission_allowed') is not False or (p.get('complete_legal_alternatives_proved') is not False) or (p.get('resource_namespace') != 'DYGR_native') or (p.get('index_planes') != 19) or (p.get('independent_check_planes') != 8):
        raise ValueError('route storage boundaries differ')
    resources = {}
    bindings = {}
    offsets = set()
    for r in p['resources']:
        if len(r) != 7 or any((type(v) != int for v in r)) or (not 0 <= r[0] < 2 ** 32) or (r[0] in resources):
            raise ValueError('route resource identity differs')
        resources[r[0]] = r
    classes = {r[0]: (r[1], r[2]) for r in p['classes']}
    if len(classes) != len(p['classes']) or any((classes.get(k, ('', 0))[0] != name for k, name in ((292, 'GLOBAL_CLK_H'), (294, 'LAB_CLK'), (369, 'GLOBAL_CLK_MUX'), (504, 'IO_BYPASS_OUT')))) or sum((classes.get(k, ('', 0))[1] for k in (292, 294, 369, 504))) != p['sink_count'] or (Counter((r[1] for r in resources.values())) != {k: v[1] for k, v in classes.items()}):
        raise ValueError('route class population differs')
    for address, offset, xor in p['bindings']:
        if any((type(v) != int for v in (address, offset, xor))) or not 0 <= address < p['raw_bits'] or (not 0 <= offset < p['cfm_bits']) or (xor not in (0, 1)) or (address in bindings) or (offset in offsets):
            raise ValueError('route storage binding differs')
        bindings[address] = (offset, xor)
        offsets.add(offset)
    identities = set()
    used = set()
    for f in p['fields']:
        identity = (f['source_gid'], f['sink_gid'])
        seen = set()
        if identity in identities or identity[0] not in resources or identity[1] not in resources or (resources[identity[1]][1] not in (292, 294, 369, 504)) or (type(f['group']) != int) or (f['group'] < 0) or (not f['bits']):
            raise ValueError('route field identity differs')
        identities.add(identity)
        for address, encoding, high in f['bits']:
            if any((type(v) != int for v in (address, encoding, high))) or address not in bindings or address in seen or (encoding not in (0, 1, 2)) or (high != -1 if encoding == 0 else high not in (0, 1)):
                raise ValueError('route field term differs')
            seen.add(address)
            used.add(address)
    excluded = {(f['source_gid'], f['sink_gid']) for f in p['excluded_fields']}
    if any((a not in resources or b not in resources or resources[b][1] not in (292, 294, 369, 504) for a, b in excluded)):
        raise ValueError('excluded route resource differs')
    zero = set(p['zero_native_fanin_gids'])
    sinks = {b for a, b in identities | excluded}
    if len(zero) != len(p['zero_native_fanin_gids']) or zero & sinks or zero | sinks != {gid for gid, r in resources.items() if r[1] in (292, 294, 369, 504)}:
        raise ValueError('route sink partition differs')
    if used != set(bindings) or identities & excluded or len(excluded) != len(p['excluded_fields']) or (len(identities) + len(excluded) != p['captured_field_count']):
        raise ValueError('route field population differs')
    return offsets

def decode_provider(p, payload):
    validate_provider(p)
    if len(payload) * 8 != p['cfm_bits']:
        raise ValueError('route payload geometry differs')
    return {'format': 'maxvrec.native_remaining_mux_storage_ir.v1', 'target': p['target'], 'resource_namespace': 'DYGR_native', 'resource_columns': ['gid', 'element_enum', 'x', 'y', 'z', 'index', 'sub_location'], 'resources': p['resources'], 'zero_native_fanin_gids': p['zero_native_fanin_gids'], 'classes': p['classes'], 'fields': p['fields'], 'binding_columns': ['native_address', 'serialized_offset', 'serializer_xor', 'stored_value', 'native_value'], 'bindings': [r + [payload[r[1] // 8] >> r[1] % 8 & 1, payload[r[1] // 8] >> r[1] % 8 & 1 ^ r[2]] for r in p['bindings']], 'selected_routes_proved': False, 'complete_legal_alternatives_proved': False, 'productive_emission_allowed': False}
