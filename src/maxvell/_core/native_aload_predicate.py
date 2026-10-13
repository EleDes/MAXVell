# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
import re
FORMAT = 'maxvrec.native_aload_predicate.v1'
TABLE = {(1, 0): False, (1, 1): False, (0, 1): True}

def predict(fields, payload, lc):
    if not re.fullmatch('LC_X[1-9][0-9]*_Y[1-9][0-9]*_N[0-9]', lc):
        raise ValueError('native LC identity differs')
    lab = lc.rsplit('_N', 1)[0].replace('LC_', 'LAB_')
    specs = ((lc, 'LE_USE_ASYNC_LOAD', 'ILL_LOW'), (lab, 'LAB_ENABLE_ALOAD', 'ILL_HIGH'))
    selected = []
    values = []
    for location, kind, sentinel in specs:
        found = [f for f in fields if (f['location'], f['class'], str(f['index'])) == (location, kind, 'none')]
        if len(found) != 1:
            raise ValueError('native load field not unique')
        f = found[0]
        if f['shape'] != [2] or f['sentinels'] != [[0, 0, sentinel]] or len(f['terms']) != 1:
            raise ValueError('native load decision shape differs')
        stage, ordinal, address, offset, invert = f['terms'][0]
        if any((type(x) != int for x in (stage, ordinal, address, offset, invert))) or (stage, ordinal) != (0, 1) or address < 0 or (not 0 <= offset < 8 * len(payload)) or (invert not in (0, 1)):
            raise ValueError('native load term differs')
        value = payload[offset // 8] >> offset % 8 & 1 ^ invert
        values.append(value)
        selected.append({**f, 'normalized_value': value})
    if selected[0]['terms'][0][3] == selected[1]['terms'][0][3]:
        raise ValueError('local and LAB controls alias')
    pair = tuple(values)
    known = pair in TABLE
    return {'format': FORMAT, 'native_lc': lc, 'native_lab': lab, 'status': 'candidate_resolved' if known else 'unresolved_combination', 'local_lab_values': values, 'aload_connected': TABLE.get(pair), 'condition_fields': selected, 'condition_offsets': sorted((f['terms'][0][3] for f in selected)), 'source_identity_proved': False, 'event_behavior_proved': False, 'productive_emission_allowed': False}
