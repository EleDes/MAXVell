# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations

def validate_inventory(d):
    if d.get('format') != 'maxvrec.native_outside_legal_inventory.v1' or any((d.get(k) is not False for k in ('productive_credit', 'usable_logic_claimed', 'no_effect_proved'))):
        raise ValueError('diagnostic boundaries differ')
    if not isinstance(d.get('target'), str) or not d['target'] or type(d.get('cfm_bits')) != int or (d['cfm_bits'] <= 0):
        raise ValueError('diagnostic identity differs')
    partition = d['partition']
    legal = set(partition['legal_locations'])
    other = set(partition['other_locations'])
    if legal & other or len(legal) != partition['legal_lc_count'] or len(other) != partition['other_lc_count'] or (len(legal | other) != partition['native_lc_count']) or (len(partition['legal_locations']) != len(legal)) or (len(partition['other_locations']) != len(other)):
        raise ValueError('diagnostic LC partition differs')
    legal_labs = set(partition['legal_lab_indices'])
    other_labs = set(partition['other_lab_indices'])
    if legal_labs & other_labs or len(legal_labs) != partition['legal_lab_count'] or len(other_labs) != partition['other_lab_count'] or (legal_labs | other_labs != set(range(partition['native_lab_count']))):
        raise ValueError('diagnostic LAB partition differs')
    identities = set()
    bindings = {}
    reverse = {}
    resource_ids = {}
    for f in d['fields']:
        key = (f['native_location'], f['class'], f['index'])
        if key in identities:
            raise ValueError('diagnostic duplicate field')
        identities.add(key)
        if f['resource_kind'] == 'LE':
            if f['native_location'] not in other or not f['class'].startswith('LE_'):
                raise ValueError('diagnostic field not outside legal LC set')
        elif f['resource_kind'] == 'LAB':
            if f['lab_index'] not in other_labs or not f['class'].startswith('LAB_'):
                raise ValueError('diagnostic field not outside legal LAB set')
        else:
            raise ValueError('diagnostic resource kind differs')
        resource = (f['resource_kind'], f['native_location'])
        identity = (f['native_gid'], f['lab_index'])
        if resource in resource_ids and resource_ids[resource] != identity:
            raise ValueError('diagnostic resource identity contradicts')
        resource_ids[resource] = identity
        shape = f['shape']
        if not shape or any((type(n) != int or n <= 0 for n in shape)):
            raise ValueError('diagnostic field shape differs')
        wanted = {(stage, o) for stage, n in enumerate(shape) for o in range(n)}
        seen = set()
        for stage, ordinal, address, offset, xor in f['terms']:
            if any((type(v) != int for v in (stage, ordinal, address, offset, xor))) or (stage, ordinal) not in wanted or (stage, ordinal) in seen or (address < 0) or (not 0 <= offset < d['cfm_bits']) or (xor not in (0, 1)):
                raise ValueError('diagnostic term differs')
            seen.add((stage, ordinal))
            if address in bindings and bindings[address] != (offset, xor):
                raise ValueError('diagnostic shared native binding differs')
            if offset in reverse and reverse[offset] != address:
                raise ValueError('diagnostic alias')
            bindings[address] = (offset, xor)
            reverse[offset] = address
        for stage, ordinal, token in f['sentinels']:
            if (stage, ordinal) not in wanted or (stage, ordinal) in seen or token not in ('ILL_LOW', 'ILL_HIGH'):
                raise ValueError('diagnostic sentinel differs')
            seen.add((stage, ordinal))
        if seen != wanted:
            raise ValueError('diagnostic field incomplete')
    if len(reverse) != d['summary']['unique_bits'] or len(d['fields']) != d['summary']['admitted_fields']:
        raise ValueError('diagnostic population differs')
    return set(reverse)

def decode_storage(d, payload):
    validate_inventory(d)
    if len(payload) * 8 != d['cfm_bits']:
        raise ValueError('diagnostic payload geometry differs')
    return {'format': 'maxvrec.native_outside_legal_storage_diagnostic.v1', 'target': d['target'], 'scope': 'native_storage_outside_exact_part_legal_membership', 'fields': [{**f, 'terms': [t + [payload[t[3] // 8] >> t[3] % 8 & 1, payload[t[3] // 8] >> t[3] % 8 & 1 ^ t[4]] for t in f['terms']]} for f in d['fields']], 'usable_logic_claimed': False, 'no_effect_proved': False, 'productive_emission_allowed': False}
