# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
import re
from collections import defaultdict

def native_values(field, payload):
    seen = set()
    active = [[] for _ in field['shape']]
    if field['sentinels']:
        raise ValueError('IO field has unresolved terms')
    for stage, ordinal, address, offset, invert in field['terms']:
        if not 0 <= stage < len(active) or not 0 <= ordinal < field['shape'][stage] or (stage, ordinal) in seen or (not 0 <= offset < len(payload) * 8) or (invert not in (0, 1)):
            raise ValueError('IO term differs')
        seen.add((stage, ordinal))
        if payload[offset // 8] >> offset % 8 & 1 ^ invert:
            active[stage].append(ordinal)
    if len(seen) != sum(field['shape']):
        raise ValueError('IO field incomplete')
    return active

def predict(fields, payload, tables, resources):
    by_io = defaultdict(dict)
    for f in fields:
        if not f['bonded'] or f['kind'] not in ('IO_DATA_INPUT', 'IO_PIA_TO_OE', 'IO_DATA_INVERT', 'IO_OE_INVERT'):
            continue
        if f['kind'] in by_io[f['location']]:
            raise ValueError('duplicate IO field')
        by_io[f['location']][f['kind']] = f
    rows = []
    for loc, fs in sorted(by_io.items()):
        if len(fs) != 4:
            raise ValueError('bonded IO field inventory differs')
        data = fs['IO_DATA_INPUT']
        block = data['block']
        pins = data['package_pin_names']
        selected = {}
        inverts = {}
        if len(pins) != 1 or any((f['package_pin_names'] != pins for f in fs.values())):
            raise ValueError('IO package pin identity differs')
        for kind, f in fs.items():
            active = native_values(f, payload)
            if kind.endswith('INVERT'):
                if f['shape'] != [1]:
                    raise ValueError('IO inversion shape differs')
                inverts[kind] = int(bool(active[0]))
            else:
                if len(active) != 2:
                    raise ValueError('IO selector stage count differs')
                if block == 'HIO' and active == [[], []]:
                    selected[kind] = 18
                    continue
                if any((len(s) != 1 for s in active)):
                    selected[kind] = None
                    continue
                code = (active[0][0], active[1][0])
                if code not in tables[kind, block]:
                    raise ValueError('IO selector code not in recipient table')
                selected[kind] = tables[kind, block][code]
        m = re.fullmatch('IOC_X(\\d+)_Y(\\d+)_N(\\d+)', loc)
        if not m:
            raise ValueError('IO native coordinate differs')
        x, y, z = map(int, m.groups())
        constant = 18 if block == 'HIO' else 10
        data_position = selected['IO_DATA_INPUT']
        oe_position = selected['IO_PIA_TO_OE']
        matches = [r for r in resources if r[1:6] == [276, x, y, 0, data_position]] if data_position is not None and data_position != constant else []
        rows.append({'native_io': loc, 'package_pin': pins[0], 'block': block, 'fields': list(fs.values()), 'selector_positions': selected, 'native_inverts': inverts, 'predicted_output_enable': 1 - inverts['IO_OE_INVERT'] if oe_position == constant else None, 'predicted_data_constant': 1 - inverts['IO_DATA_INVERT'] if data_position == constant else None, 'predicted_data_source': matches[0] if len(matches) == 1 else None, 'predicted_data_inverted': bool(inverts['IO_DATA_INVERT']), 'state': 'native_hypothesis_only'})
    return rows
