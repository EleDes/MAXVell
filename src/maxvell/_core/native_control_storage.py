# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .asmdb_logiccell_lab_field_materializer import EXPECTED_FIELD_MULTIPLICITIES
from collections import Counter
from collections import defaultdict
FORMAT = 'maxvrec.native_le_lab_control_storage_provider.v1'
SKIP = {'LE_LUT_FUNCTION', 'LE_LUT_INPUT'}

def validate_fields(provider):
    if provider.get('format') != FORMAT or provider.get('index_planes') != 19 or provider.get('independent_check_planes') != 8 or (provider.get('functional_controls_proved') is not False) or (provider.get('productive_emission_allowed') is not False):
        raise ValueError('control storage proof boundaries differ')
    bindings = {}
    reverse = {}
    identities = set()
    uses = defaultdict(list)
    for field in provider['fields']:
        identity = (field['location'], field['class'], field['index'])
        if identity in identities or field['class'] in SKIP or field['class'] not in EXPECTED_FIELD_MULTIPLICITIES:
            raise ValueError('control field identity differs')
        identities.add(identity)
        ordinals = set()
        for stage, ordinal, address, offset, xor in field['terms']:
            if any((type(v) != int for v in (stage, ordinal, address, offset, xor))) or stage not in (0, 1) or ordinal < 0 or (address < 0) or (not 0 <= offset < provider['cfm_bits']) or (xor not in (0, 1)):
                raise ValueError('control field term bounds differ')
            if (stage, ordinal) in ordinals:
                raise ValueError('control field ordinal duplicated')
            ordinals.add((stage, ordinal))
            if address in bindings and bindings[address] != (offset, xor):
                raise ValueError('shared native control bit contradicts')
            if offset in reverse and reverse[offset] != address:
                raise ValueError('different native control bits alias')
            bindings[address] = (offset, xor)
            reverse[offset] = address
            uses[offset].append([*identity, stage, ordinal])
        for stage, ordinal, token in field['sentinels']:
            if token not in ('ILL_LOW', 'ILL_HIGH') or (stage, ordinal) in ordinals:
                raise ValueError('control sentinel differs')
            ordinals.add((stage, ordinal))
        shape = field['shape']
        if not field['terms'] or len(shape) not in (1, 2) or any((type(n) != int or n <= 0 for n in shape)) or (ordinals != {(stage, o) for stage, n in enumerate(shape) for o in range(n)}):
            raise ValueError('control field ordinal sequence incomplete')
    excluded = {(f['location'], f['class'], f['index']) for f in provider['excluded_fields']}
    if len(excluded) != len(provider['excluded_fields']) or excluded & identities:
        raise ValueError('control field exclusions duplicated')
    counts = Counter((kind for _, kind, _ in identities | excluded))
    expected = {k: v * (provider['cell_count'] if k.startswith('LE_') else provider['lab_count']) for k, v in EXPECTED_FIELD_MULTIPLICITIES.items() if k not in SKIP}
    if counts != expected:
        raise ValueError('control field population incomplete')
    return (set(reverse), [{'offset': o, 'native_address': reverse[o], 'references': refs} for o, refs in sorted(uses.items()) if len(refs) > 1])

def decode_provider(provider, payload):
    offsets, coupling = validate_fields(provider)
    if len(payload) * 8 != provider['cfm_bits']:
        raise ValueError('control payload geometry differs')
    return {'format': 'maxvrec.native_le_lab_control_storage_ir.v1', 'target': provider['target'], 'fields': [{**f, 'terms': [t + [payload[t[3] // 8] >> t[3] % 8 & 1, payload[t[3] // 8] >> t[3] % 8 & 1 ^ t[4]] for t in f['terms']]} for f in provider['fields']], 'coupled_bits': coupling, 'sentinels_counted_as_bits': False, 'functional_controls_proved': False, 'productive_emission_allowed': False}
