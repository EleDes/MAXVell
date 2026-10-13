# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
import re

def values(field, payload):
    result = [[] for _ in field['shape']]
    seen = set()
    if field['sentinels']:
        raise ValueError('incomplete native control field')
    for stage, ordinal, address, offset, invert in field['terms']:
        if type(offset) != int or not 0 <= offset < len(payload) * 8 or invert not in (0, 1) or (not 0 <= stage < len(result)) or (not 0 <= ordinal < field['shape'][stage]) or ((stage, ordinal) in seen):
            raise ValueError('native control term differs')
        seen.add((stage, ordinal))
        if payload[offset // 8] >> offset % 8 & 1 ^ invert:
            result[stage].append(ordinal)
    if seen != {(s, i) for s, n in enumerate(field['shape']) for i in range(n)}:
        raise ValueError('native control term population differs')
    return result

def selected(field, payload, table):
    active = values(field, payload)
    kind = field['class']
    shapes = {'LAB_PIA_TO_INPUT': [6, 3], 'LAB_CLOCK_FAST_MUX': [5, 1], 'LAB_CLEAR_FAST_MUX': [3, 4]}
    if field['shape'] != shapes[kind]:
        raise ValueError('native mux shape differs')
    first = sum((1 << i for i in active[0])) if kind == 'LAB_CLEAR_FAST_MUX' else active[0][0] if len(active[0]) == 1 else None
    second = sum((1 << i for i in active[1])) if kind == 'LAB_CLOCK_FAST_MUX' else active[1][0] if len(active[1]) == 1 else None
    positions = []
    for position, (a, b) in enumerate(table):
        if a == 'ILL_ALWAYS' or b == 'ILL_ALWAYS':
            continue
        if a not in ('ILL_NEVER', str(first)):
            continue
        if b not in ('ILL_NEVER', str(second)):
            continue
        positions.append(position)
    return {'active_ordinals': active, 'positions': positions, 'condition_offsets': [t[3] for t in field['terms']]}

def predict(fields, payload, encoding, cells, resources):
    lookup = {(f['location'], f['class'], str(f['index'])): f for f in fields}
    if len(lookup) != len(fields):
        raise ValueError('duplicate native control field identity')
    rows = []
    for cell in cells:
        if cell['observed_output_port'] != 'REGOUT':
            continue
        lc = cell['native_lc']
        match = re.fullmatch('LC_X(\\d+)_Y(\\d+)_N(\\d+)', lc)
        if not match:
            raise ValueError('register native location differs')
        x, y, n = map(int, match.groups())
        lab = f'LAB_X{x}_Y{y}'
        le = lookup[lc, 'LE_CLOCK_SELECT', 'none']
        v = values(le, payload)
        if le['shape'] != [1]:
            raise ValueError('LE clock selector shape differs')
        clock_index = int(bool(v[0]))
        clock = lookup[lab, 'LAB_CLOCK_FAST_MUX', str(clock_index)]
        chosen = selected(clock, payload, encoding['LAB_CLOCK_FAST_MUX', clock_index])
        base = {'native_lc': lc, 'native_lab': lab, 'clock_index': clock_index, 'le_clock_field': le, 'clock_field': clock, 'clock_selection': chosen, 'state': 'unresolved_clock_selector'}
        if len(chosen['positions']) == 1 and chosen['positions'][0] < 6:
            index = chosen['positions'][0]
            pia = lookup[lab, 'LAB_PIA_TO_INPUT', str(index)]
            source = selected(pia, payload, encoding['LAB_PIA_TO_INPUT', index])
            base.update(pia_index=index, pia_field=pia, pia_selection=source)
            if len(source['positions']) == 1:
                position = source['positions'][0]
                kind = 276 if position < 26 else 43
                line = position if position < 26 else position - 26
                matches = [r for r in resources if r[1:6] == [kind, x, y, 0, line]]
                base.update(state='unique_native_clock_path' if len(matches) == 1 else 'unresolved_clock_source', source_resource=matches[0] if len(matches) == 1 else None)
        clear = []
        for index in range(2):
            field = lookup[lab, 'LAB_CLEAR_FAST_MUX', str(index)]
            clear.append({'index': index, 'field': field, 'selection': selected(field, payload, encoding['LAB_CLEAR_FAST_MUX', index]), 'effective_polarity_proved': False})
        base['clear_candidates'] = clear
        rows.append(base)
    if not rows:
        raise ValueError('empty register path population')
    return rows
