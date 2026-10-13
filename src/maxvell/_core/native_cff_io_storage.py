# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .cff_field_frontier import decode_candidate
CAPABILITY_ID = 'NATIVE_CFF_IO_STORAGE_DECODER_IR'
FORMAT = 'maxvrec.native_cff_io_storage_provider.v1'

def validate_provider(p):
    if p.get('format') != FORMAT or p.get('productive_emission_allowed') is not False or p.get('effective_IO_mode_proved') is not False or (p.get('independent_check_planes') != 8):
        raise ValueError('CFF storage provider scope differs')
    inv = p['inventory']
    raw = p['bindings']
    bindings = {int(k): v for k, v in raw.items()}
    if type(p['cfm_bits']) != int or p['cfm_bits'] <= 0 or p['cfm_bits'] % 8:
        raise ValueError('CFF payload geometry differs')
    if len(bindings) != len(raw) or any((str(int(k)) != str(k) for k in raw)):
        raise ValueError('CFF binding key differs')
    if inv['target'] != p['target'] or inv['cfm_bits'] != p['cfm_bits']:
        raise ValueError('CFF inventory identity differs')
    if inv['cff_ordinals'] != list(range(p['cff_bits'])) or p['cff_bits'] not in (480, 960, 1327, 1704):
        raise ValueError('CFF ordinal domain differs')
    identities = {(f['kind'], f['block'], f['index']) for f in inv['fields']}
    if len(identities) != len(inv['fields']) or len(identities) != inv['counts']['fields']:
        raise ValueError('CFF field population differs')
    used = set()
    for f in inv['fields']:
        positions = set()
        native = set()
        for stage, ordinal, space, value in f['tokens']:
            if type(stage) != int or type(ordinal) != int or min(stage, ordinal) < 0 or ((stage, ordinal) in positions):
                raise ValueError('CFF field term position differs')
            positions.add((stage, ordinal))
            if space == 'CFF':
                if type(value) != int or not 0 <= value < p['cff_bits']:
                    raise ValueError('CFF term outside native space')
                native.add(value)
            elif space != 'sentinel' or value not in ('ILL_LOW', 'ILL_HIGH'):
                raise ValueError('CFF field term space differs')
        if sorted(native) != f['cff_ordinals']:
            raise ValueError('CFF field ordinal population differs')
        used.update(native)
    if used != set(inv['cff_ordinals']):
        raise ValueError('CFF field coverage incomplete')
    result = decode_candidate(inv, bytes(p['cfm_bits'] // 8), bindings)
    if result['excluded_fields']:
        raise ValueError('CFF storage has incomplete mixed fields')
    return (bindings, {v[0] for v in bindings.values()})

def decode_provider(provider, payload):
    bindings, _ = validate_provider(provider)
    decoded = decode_candidate(provider['inventory'], payload, bindings)
    return {'format': 'maxvrec.native_cff_io_storage_ir.v1', 'target': provider['target'], 'payload_address_space': 'CFM', 'native_address_space': 'CFF', 'bindings': provider['bindings'], 'fields': [{**f, 'values': d['values']} for f, d in zip(provider['inventory']['fields'], decoded['fields'], strict=True)], 'logical_instances_created': 0, 'effective_IO_mode_proved': False, 'productive_emission_allowed': False}
