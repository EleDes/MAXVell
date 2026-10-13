# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from collections import Counter

def inventory(groups, pads):
    by_key = {(r['block'], r['index']): r for r in pads}
    if len(by_key) != len(pads):
        raise ValueError('CFF pad identity duplicate')
    fields = []
    seen = set()
    all_ordinals = set()
    for group in groups:
        if group['count'] != sum((b == group['block'] for b, i in by_key)):
            raise ValueError('CFF group/resource count differs')
        for index in range(group['count']):
            tokens = []
            cff = set()
            cram = set()
            for stage in range(group['stages']):
                for ordinal, token in enumerate(group['groups'][index, stage]):
                    if token.startswith('CFF:'):
                        value = int(token[4:])
                        if value < 0:
                            raise ValueError('CFF ordinal negative')
                        cff.add(value)
                        space = 'CFF'
                    elif token.isdigit():
                        value = int(token)
                        cram.add(value)
                        space = 'CRAM'
                    elif token in ('ILL_LOW', 'ILL_HIGH'):
                        value = token
                        space = 'sentinel'
                    else:
                        raise ValueError('CFF token syntax differs')
                    tokens.append([stage, ordinal, space, value])
            if not cff:
                continue
            key = (group['block'], index, group['kind'])
            if key in seen:
                raise ValueError('CFF field duplicate')
            seen.add(key)
            all_ordinals.update(cff)
            fields.append({**by_key[group['block'], index], 'kind': group['kind'], 'tokens': tokens, 'cff_ordinals': sorted(cff), 'raw_cram_addresses': sorted(cram), 'content_only_cff': not cram})
    return {'fields': fields, 'cff_ordinals': sorted(all_ordinals), 'counts': {'fields': len(fields), 'cff_ordinals': len(all_ordinals), 'mixed_cram_fields': sum((bool(f['raw_cram_addresses']) for f in fields)), 'bonded_fields': sum((f['bonded'] for f in fields)), 'classes': dict(Counter((f['kind'] for f in fields)))}, 'physical_bit_count': None, 'percentage_gain': None, 'productive_emission_allowed': False}

def decode_candidate(inventory, payload, bindings):
    """Only a validated future physical projection can supply these bindings.

    This function itself does not supply that proof or change any capability.
    Mixed CRAM/CFF fields require a separate complete join and remain excluded.
    """
    if len(payload) * 8 != inventory['cfm_bits']:
        raise ValueError('CFF candidate payload size differs')
    expected = set(inventory['cff_ordinals'])
    if set(bindings) != expected:
        raise ValueError('CFF binding domain incomplete')
    destinations = set()
    for native, (offset, xor) in bindings.items():
        if type(native) != int or type(offset) != int or type(xor) != int or (not 0 <= offset < len(payload) * 8) or (xor not in (0, 1)):
            raise ValueError('CFF binding bounds differ')
        if offset in destinations:
            raise ValueError('CFF endpoint alias')
        destinations.add(offset)
    fields = []
    excluded = []
    for f in inventory['fields']:
        if f['raw_cram_addresses']:
            excluded.append({'kind': f['kind'], 'block': f['block'], 'index': f['index'], 'reason': 'mixed CRAM join absent'})
            continue
        values = []
        for stage, ordinal, space, value in f['tokens']:
            if space == 'sentinel':
                decoded = int(value == 'ILL_HIGH')
            elif space == 'CFF':
                offset, xor = bindings[value]
                decoded = payload[offset // 8] >> offset % 8 & 1 ^ xor
            else:
                raise ValueError('CFF candidate unsupported space')
            values.append([stage, ordinal, decoded])
        fields.append({'kind': f['kind'], 'block': f['block'], 'index': f['index'], 'gid': f['gid'], 'values': values})
    return {'format': 'maxvrec.cff_field_candidate.v1', 'target': inventory['target'], 'fields': fields, 'excluded_fields': excluded, 'productive_emission_allowed': False, 'coverage_credit_allowed': False}
