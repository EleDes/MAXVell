# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
CAPABILITY_ID = 'NATIVE_IO_STORAGE_DECODER_IR'
FORMAT = 'maxvrec.native_io_storage_provider.v1'
KINDS = {'IO_DATA_INPUT', 'IO_PIA_TO_OE', 'IO_OE_INVERT', 'IO_DATA_INVERT', 'IO_USE_PULL_UP', 'IO_USE_SLOW_SLEW', 'IO_USE_BUS_HOLD', 'IO_USE_PCI_DIODE_CLAMP', 'IO_PIN_MODE', 'IO_SELECT_IOST_DIRT', 'IO_SET_PAD_TO_CORE_OTERM_DELAY_TSUNAMI', 'IO_SET_DRIVE_STRENGTH_TSUNAMI'}

def validate_provider(p):
    if p.get('format') != FORMAT or p.get('functional_IO_mode_proved') is not False or p.get('productive_emission_allowed') is not False or (p.get('index_planes') != 19) or (p.get('independent_check_planes') != 8):
        raise ValueError('IO storage boundaries differ')
    if set(p['io_counts']) != {'HIO', 'VIO'} or any((type(n) != int or n < 1 for n in p['io_counts'].values())):
        raise ValueError('IO block counts differ')
    if len({r['gid'] for r in p['pads']}) != len(p['pads']) or len({r['pad_id'] for r in p['pads']}) != len(p['pads']):
        raise ValueError('IO pad identity duplicated')
    pads = {(r['block'], r['index']): r for r in p['pads']}
    if len(pads) != len(p['pads']) or set(pads) != {(b, i) for b, n in p['io_counts'].items() for i in range(n)}:
        raise ValueError('IO pad population differs')
    identities = set()
    forward = {}
    reverse = {}
    for f in p['fields']:
        identity = (f['block'], f['index'], f['kind'])
        if identity in identities:
            raise ValueError('IO field duplicated')
        identities.add(identity)
        if any((f[k] != v for k, v in pads[f['block'], f['index']].items())):
            raise ValueError('IO field resource differs')
        if not f['shape'] or any((type(n) != int or n < 1 for n in f['shape'])):
            raise ValueError('IO field shape differs')
        ordinals = set()
        for stage, ordinal, address, offset, xor in f['terms']:
            if any((type(v) != int for v in (stage, ordinal, address, offset, xor))) or address < 0 or (not 0 <= offset < p['cfm_bits']) or (xor not in (0, 1)):
                raise ValueError('IO field bit bounds differ')
            if (stage, ordinal) in ordinals:
                raise ValueError('IO ordinal duplicated')
            ordinals.add((stage, ordinal))
            if address in forward and forward[address] != (offset, xor):
                raise ValueError('IO shared bit contradicts')
            if offset in reverse and reverse[offset] != address:
                raise ValueError('IO endpoint aliases')
            forward[address] = (offset, xor)
            reverse[offset] = address
        for stage, ordinal, token in f['sentinels']:
            if token not in ('ILL_LOW', 'ILL_HIGH') or (stage, ordinal) in ordinals:
                raise ValueError('IO sentinel differs')
            ordinals.add((stage, ordinal))
        if not f['terms'] or ordinals != {(stage, i) for stage, n in enumerate(f['shape']) for i in range(n)}:
            raise ValueError('IO field incomplete')
    excluded = {(f['block'], f['index'], f['kind']) for f in p['excluded_fields']}
    if len(excluded) != len(p['excluded_fields']) or identities & excluded or identities | excluded != {(b, i, k) for b, n in p['io_counts'].items() for i in range(n) for k in KINDS}:
        raise ValueError('IO field population differs')
    return set(reverse)

def decode_provider(provider, payload):
    validate_provider(provider)
    if len(payload) * 8 != provider['cfm_bits']:
        raise ValueError('IO payload geometry differs')
    return {'format': 'maxvrec.native_io_storage_ir.v1', 'target': provider['target'], 'fields': [{**f, 'terms': [t + [payload[t[3] // 8] >> t[3] % 8 & 1, payload[t[3] // 8] >> t[3] % 8 & 1 ^ t[4]] for t in f['terms']]} for f in provider['fields']], 'functional_IO_mode_proved': False, 'productive_emission_allowed': False}
