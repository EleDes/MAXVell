# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations

def key(field):
    return (field['location'], field['class'], field['index'])

def validate_fields(fields, cfm_bits):
    ids = set()
    bindings = {}
    reverse = {}
    for f in fields:
        identity = key(f)
        if identity in ids:
            raise ValueError('duplicate native field identity')
        ids.add(identity)
        ordinals = set()
        if not f['class'].startswith(('LE_', 'LAB_')):
            raise ValueError('native field class differs')
        for stage, ordinal, address, offset, invert in f['terms']:
            if any((type(v) != int for v in (stage, ordinal, address, offset, invert))) or not 0 <= offset < cfm_bits or address < 0 or (invert not in (0, 1)):
                raise ValueError('field endpoint bounds differ')
            if (stage, ordinal) in ordinals:
                raise ValueError('duplicate field ordinal')
            ordinals.add((stage, ordinal))
            if address in bindings and bindings[address] != (offset, invert):
                raise ValueError('shared native address conflicts')
            if offset in reverse and reverse[offset] != address:
                raise ValueError('native fields alias')
            bindings[address] = (offset, invert)
            reverse[offset] = address
        for stage, ordinal, value in f['sentinels']:
            if value not in ('ILL_LOW', 'ILL_HIGH') or (stage, ordinal) in ordinals:
                raise ValueError('field sentinel differs')
            ordinals.add((stage, ordinal))
        if not f['terms'] or not f['shape'] or any((type(n) != int or n <= 0 for n in f['shape'])) or (ordinals != {(s, o) for s, n in enumerate(f['shape']) for o in range(n)}):
            raise ValueError('field shape incomplete')
    return (ids, set(reverse))
