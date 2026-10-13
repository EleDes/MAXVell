# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations

def identity(resource):
    if not isinstance(resource, (list, tuple)) or len(resource) != 7 or any((type(v) != int for v in resource)):
        raise ValueError('source resource schema differs')
    _, kind, x, y, z, index, _ = resource
    if x < 0 or y < 0 or z != 0:
        raise ValueError('source resource coordinates differ')
    if kind == 43 and 0 <= index < 10:
        n, channel = (index, 2)
    elif kind == 45 and 0 <= index < 20:
        n, channel = (index // 2, index % 2)
    else:
        raise ValueError('source resource class or index unsupported')
    return (f'LC_X{x}_Y{y}_N{n}', channel)

def resolve(resource, fields, payload):
    lc, channel = identity(resource)
    matches = [f for f in fields if f['location'] == lc and f['class'] == 'LE_REG_OUT_YGR' and (f['index'] == str(channel))]
    if len(matches) != 1:
        raise ValueError('source channel field absent or duplicated')
    field = matches[0]
    if field['shape'] != [1] or field['sentinels'] or len(field['terms']) != 1:
        raise ValueError('source channel field shape differs')
    term = field['terms'][0]
    if len(term) != 5 or any((type(v) != int for v in term)):
        raise ValueError('source channel term differs')
    stage, ordinal, address, offset, invert = term
    if (stage, ordinal) != (0, 0) or address < 0 or (not 0 <= offset < len(payload) * 8) or (invert not in (0, 1)):
        raise ValueError('source channel term domain differs')
    serialized = payload[offset // 8] >> offset % 8 & 1
    internal = serialized ^ invert
    return {'native_resource': list(resource), 'canonical_lc': lc, 'channel_index': channel, 'field_class': 'LE_REG_OUT_YGR', 'native_address': address, 'payload_offset': offset, 'serialized_invert': invert, 'serialized_bit': serialized, 'internal_bit': internal, 'source_port': 'COMBOUT' if internal else 'REGOUT', 'state_semantics_proved': False, 'productive_emission_allowed': False}
