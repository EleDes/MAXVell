# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
FORMAT = 'maxvrec.native_device_field_storage_provider.v1'
PORTS = ('DRDIN', 'DRSHFT', 'DRCLK', 'ARDIN', 'ARSHFT', 'ARCLK', 'PROGRAM', 'ERASE', 'OSC_ENA', 'SBDIN')
KINDS = {**{'UNVM_' + prefix + port: 1 for prefix in ('PIA_TO_', 'INVERT_') for port in PORTS}, 'UNVM_CONTENT': 1, 'IO_PIA_TO_GLOBAL_CLK_MUX': 4, 'DEVICE_USE_GLOBAL_CLEAR': 1, 'DEVICE_USE_GLOBAL_TRI': 1, 'JTAG_PIA_TO_TDOUSER': 1, 'JTAG_TDOUSER_INVERT': 1}

def field_resource(kind, index, singletons, target):
    if kind.startswith('UNVM_'):
        return {'kind': 'UNVM', **singletons['UNVM']}
    if kind.startswith('JTAG_'):
        return {'kind': 'JTAG', **singletons['JTAG']}
    if kind == 'IO_PIA_TO_GLOBAL_CLK_MUX':
        return {'kind': 'native_global_selector', 'scope': 'native_architecture_group_ordinal', 'index': index, 'target': target, 'physical_global_identity_proved': False}
    return {'kind': 'device', 'scope': 'exact_device', 'target': target}

def validate_provider(p):
    if p.get('format') != FORMAT or p.get('functional_modes_proved') is not False or p.get('productive_emission_allowed') is not False or (p.get('index_planes') != 19) or (p.get('independent_check_planes') != 8):
        raise ValueError('device storage boundaries differ')
    if set(p['singletons']) != {'UNVM', 'JTAG'}:
        raise ValueError('singleton catalog differs')
    identities = set()
    forward = {}
    reverse = {}
    for f in p['fields']:
        identity = (f['kind'], f['index'])
        if identity in identities or f['kind'] == 'UNVM_CONTENT' or f.get('address_space') != 'CFM':
            raise ValueError('device field identity or address space differs')
        identities.add(identity)
        if f['resource'] != field_resource(f['kind'], f['index'], p['singletons'], p['target']):
            raise ValueError('device field resource differs')
        if not f['shape'] or any((type(n) != int or n < 1 for n in f['shape'])):
            raise ValueError('device field shape differs')
        ordinals = set()
        for stage, ordinal, address, offset, xor in f['terms']:
            if any((type(v) != int for v in (stage, ordinal, address, offset, xor))) or not 0 <= address < p['raw_bits'] or (not 0 <= offset < p['cfm_bits']) or (xor not in (0, 1)):
                raise ValueError('device field bit bounds differ')
            if (stage, ordinal) in ordinals:
                raise ValueError('device ordinal duplicated')
            ordinals.add((stage, ordinal))
            if address in forward and forward[address] != (offset, xor):
                raise ValueError('device shared bit contradicts')
            if offset in reverse and reverse[offset] != address:
                raise ValueError('device endpoint aliases')
            forward[address] = (offset, xor)
            reverse[offset] = address
        for stage, ordinal, token in f['sentinels']:
            if token not in ('ILL_LOW', 'ILL_HIGH') or (stage, ordinal) in ordinals:
                raise ValueError('device sentinel differs')
            ordinals.add((stage, ordinal))
        if not f['terms'] or ordinals != {(s, i) for s, n in enumerate(f['shape']) for i in range(n)}:
            raise ValueError('device field incomplete')
    excluded = {(f['kind'], f['index']) for f in p['excluded_fields']}
    if len(excluded) != len(p['excluded_fields']) or identities & excluded or identities | excluded != {(k, i) for k, n in KINDS.items() for i in range(n)}:
        raise ValueError('device field population differs')
    return set(reverse)

def decode_provider(provider, payload):
    validate_provider(provider)
    if len(payload) * 8 != provider['cfm_bits']:
        raise ValueError('device field payload geometry differs')
    return {'format': 'maxvrec.native_device_field_storage_ir.v1', 'target': provider['target'], 'fields': [{**f, 'terms': [t + [payload[t[3] // 8] >> t[3] % 8 & 1, payload[t[3] // 8] >> t[3] % 8 & 1 ^ t[4]] for t in f['terms']]} for f in provider['fields']], 'functional_modes_proved': False, 'productive_emission_allowed': False}
