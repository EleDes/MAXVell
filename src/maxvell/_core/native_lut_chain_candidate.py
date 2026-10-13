# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
import re

def binding(lc, fields, payload, inputs, mask):
    if not any((mask >> n & 1 != mask >> (n ^ 8) & 1 for n in range(16))):
        return None
    flags = [f for f in fields if f['class'] == 'LE_USE_CASCADE_ROUTING']
    if len(flags) != 1:
        raise ValueError('cascade selector field not unique')
    field = flags[0]
    if field['shape'] != [1] or field.get('sentinels') or len(field['terms']) != 1:
        raise ValueError('cascade selector field shape differs')
    stage, ordinal, address, offset, xor = field['terms'][0]
    if (stage, ordinal) != (0, 0) or type(offset) is not int or (not 0 <= offset < len(payload) * 8) or (xor not in (0, 1)):
        raise ValueError('cascade selector term differs')
    normalized = payload[offset // 8] >> offset % 8 & 1 ^ xor
    if normalized == 1:
        return None
    if any((r['predicted_port'] == 'DATAD' for r in inputs)):
        raise ValueError('cascade and ordinary DATAD selector conflict')
    match = re.fullmatch('LC_X(\\d+)_Y(\\d+)_N([0-9])', lc)
    if match is None or int(match[3]) == 0:
        raise ValueError('cascade predecessor outside supported same-LAB geometry')
    source = f'LC_X{match[1]}_Y{match[2]}_N{int(match[3]) - 1}'
    return {'predicted_port': 'DATAD', 'state': 'unique_source', 'source_kind': 'lut_chain', 'source_lc': source, 'source_xor': 1, 'cascade_field': {'class': field['class'], 'term': field['terms'][0], 'normalized_value': normalized}, 'scope': 'candidate raw-LUT DATAD relation; separate functional qualification required'}
