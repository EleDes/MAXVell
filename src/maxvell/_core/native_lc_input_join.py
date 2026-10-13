# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_coordinate import parse_route_element
from collections import Counter
from collections import defaultdict
PORTS = ('DATAA', 'DATAB', 'DATAC', 'DATAD')

def predict(fields, payload, tables, index_to_port, resources):
    if set(index_to_port) != set(range(4)) or set(index_to_port.values()) != set(PORTS):
        raise ValueError('named-port hypothesis is not bijective')
    lookup = defaultdict(list)
    gids = set()
    for r in resources:
        if len(r) != 7 or r[0] in gids:
            raise ValueError('native resource identity differs')
        gids.add(r[0])
        lookup[tuple(r[1:6])].append(r)
    rows = []
    inactive = 0
    ids = set()
    for f in fields:
        if f['class'] != 'LE_LUT_INPUT':
            continue
        index = int(f['index'])
        identity = (f['location'], index)
        if identity in ids:
            raise ValueError('selector field duplicated')
        ids.add(identity)
        if f['shape'] != [6, 3] or f['sentinels']:
            raise ValueError('selector field shape differs')
        active = [[], []]
        ordinals = set()
        for stage, ordinal, address, offset, invert in f['terms']:
            if type(offset) != int or not 0 <= offset < len(payload) * 8 or invert not in (0, 1) or (stage not in (0, 1)) or (not 0 <= ordinal < (6 if stage == 0 else 3)) or ((stage, ordinal) in ordinals):
                raise ValueError('selector term differs')
            ordinals.add((stage, ordinal))
            if payload[offset // 8] >> offset % 8 & 1 ^ invert:
                active[stage].append(ordinal)
        if ordinals != {(0, i) for i in range(6)} | {(1, i) for i in range(3)}:
            raise ValueError('selector terms incomplete')
        if active == [[], []]:
            inactive += 1
            continue
        row = {'native_lc': f['location'], 'native_input_index': index, 'predicted_port': index_to_port[index], 'active_ordinals': active, 'bit_offsets': [t[3] for t in f['terms']], 'state': 'ambiguous_code'}
        if len(active[0]) == len(active[1]) == 1:
            position = tables[index].get((active[0][0], active[1][0]))
            if position is None:
                raise ValueError('unique selector code not in recipient table')
            lc = parse_route_element(f['location'])
            if not lc or lc['family'] != 'LC':
                raise ValueError('native LC syntax differs')
            kind = 276 if position < 26 else 43
            line = position if position < 26 else position - 26
            matches = lookup[kind, lc['x'], lc['y'], 0, line]
            row.update(selector_position=position, source_class=kind, source_index=line, state='unique_source' if len(matches) == 1 else 'unresolved_native_resource', source_resource=matches[0] if len(matches) == 1 else None)
        rows.append(row)
    return {'format': 'maxvrec.native_lc_input_prediction.v1', 'rows': rows, 'inactive_field_count': inactive, 'selector_field_count': len(ids), 'states': dict(Counter((r['state'] for r in rows))), 'generic_port_transfer_proved': False, 'productive_emission_allowed': False}
