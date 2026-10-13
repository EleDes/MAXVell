# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from collections import Counter
FORMAT = 'maxvrec.native_source_exclusion_storage_provider.v1'
CLASSES = {264: 'H4', 269: 'V4', 276: 'LAB_LINE'}

def validate_provider(p):
    if p.get('format') != FORMAT or not isinstance(p.get('target'), str) or (not p['target']) or any((p.get(k) is not False for k in ('mandatory_route_terms_proved', 'selected_routes_proved', 'productive_emission_allowed'))) or (p.get('resource_namespace') != 'DYGR_native') or (p.get('condition_kind') != 'source_exclusion') or (p.get('index_planes') != 19) or (p.get('independent_check_planes') != 8):
        raise ValueError('source storage boundaries differ')
    if any((type(p.get(k)) != int or p[k] <= 0 for k in ('cfm_bits', 'raw_bits'))):
        raise ValueError('source storage geometry differs')
    resources = {}
    classes = {r[0]: (r[1], r[2]) for r in p['classes']}
    if len(classes) != len(p['classes']) or set(classes) != set(CLASSES) or any((classes[k][0] != v for k, v in CLASSES.items())):
        raise ValueError('source classes differ')
    for r in p['resources']:
        if len(r) != 7 or any((type(v) != int for v in r)) or (not 0 <= r[0] < 2 ** 32) or (r[0] in resources) or (r[1] not in CLASSES):
            raise ValueError('source resource identity differs')
        resources[r[0]] = r
    if Counter((r[1] for r in resources.values())) != {k: v[1] for k, v in classes.items()}:
        raise ValueError('source class population differs')
    bindings = {}
    offsets = set()
    for a, offset, xor in p['bindings']:
        if any((type(v) != int for v in (a, offset, xor))) or not 0 <= a < p['raw_bits'] or (not 0 <= offset < p['cfm_bits']) or (xor not in (0, 1)) or (a in bindings) or (offset in offsets):
            raise ValueError('source storage binding differs')
        bindings[a] = (offset, xor)
        offsets.add(offset)
    identities = set()
    sources = set()
    used = set()
    for f in p['fields']:
        key = (f['source_gid'], f['group'])
        if any((type(v) != int for v in key)) or key in identities or key[0] not in resources or (key[1] < 0) or (not f['bits']):
            raise ValueError('source group identity differs')
        identities.add(key)
        sources.add(key[0])
        seen = set()
        for a, encoding, high in f['bits']:
            if any((type(v) != int for v in (a, encoding, high))) or a not in bindings or a in seen or (encoding not in (0, 1, 2)) or (high != -1 if encoding == 0 else high not in (0, 1)):
                raise ValueError('source term differs')
            seen.add(a)
            used.add(a)
    for f in p['excluded_fields']:
        key = (f['source_gid'], f['group'])
        bad = f['invalid_addresses']
        if any((type(v) != int for v in key)) or key in identities or key[0] not in resources or (key[1] < 0):
            raise ValueError('excluded group identity differs')
        if not isinstance(bad, list) or len(set(bad)) != len(bad) or any((type(a) != int or a < 0 for a in bad)) or (f['reason'] == 'unresolved_native_endpoint' and (not bad)) or (f['reason'] == 'zero_bit_group' and bad) or (f['reason'] not in ('unresolved_native_endpoint', 'zero_bit_group')):
            raise ValueError('excluded group reason differs')
        identities.add(key)
        sources.add(key[0])
    absent = p['no_source_exclusion_gids']
    zero = set(absent)
    if len(zero) != len(absent) or any((type(v) != int for v in absent)) or sources & zero or (sources | zero != set(resources)):
        raise ValueError('source group partition differs')
    if used != set(bindings) or len(identities) != p['captured_field_count']:
        raise ValueError('source field population differs')
    if 'unique_bits' in p and p['unique_bits'] != len(offsets):
        raise ValueError('source bit count differs')
    return offsets

def decode_provider(p, payload):
    validate_provider(p)
    if len(payload) * 8 != p['cfm_bits']:
        raise ValueError('source payload geometry differs')
    return {'format': 'maxvrec.native_source_exclusion_storage_ir.v1', 'target': p['target'], 'resource_namespace': 'DYGR_native', 'condition_kind': 'source_exclusion', 'resource_columns': ['gid', 'element_enum', 'x', 'y', 'z', 'index', 'sub_location'], 'resources': p['resources'], 'classes': p['classes'], 'fields': p['fields'], 'excluded_fields': p['excluded_fields'], 'no_source_exclusion_gids': p['no_source_exclusion_gids'], 'binding_columns': ['native_address', 'serialized_offset', 'serializer_xor', 'stored_value', 'native_value'], 'bindings': [r + [payload[r[1] // 8] >> r[1] % 8 & 1, payload[r[1] // 8] >> r[1] % 8 & 1 ^ r[2]] for r in p['bindings']], 'mandatory_route_terms_proved': False, 'selected_routes_proved': False, 'productive_emission_allowed': False}
