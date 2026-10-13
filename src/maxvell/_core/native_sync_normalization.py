# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations

def predict(fields, payload, lc):
    lab = lc.rsplit('_N', 1)[0].replace('LC_', 'LAB_')
    selected = []

    def read(location, kind, shape, sentinels):
        rows = [f for f in fields if (f['location'], f['class'], str(f['index'])) == (location, kind, 'none')]
        if len(rows) != 1:
            raise ValueError('synchronous field not unique')
        f = rows[0]
        if f['shape'] != shape or f['sentinels'] != sentinels:
            raise ValueError('synchronous field shape differs')
        expected = {(0, n) for n in range(shape[0])} - {(s, n) for s, n, name in sentinels}
        seen = set()
        values = []
        for s, n, a, o, x in f['terms']:
            if any((type(v) != int for v in (s, n, a, o, x))) or (s, n) in seen or (s, n) not in expected or (a < 0) or (not 0 <= o < 8 * len(payload)) or (x not in (0, 1)):
                raise ValueError('synchronous term differs')
            seen.add((s, n))
            values.append(payload[o // 8] >> o % 8 & 1 ^ x)
        if seen != expected:
            raise ValueError('synchronous field population differs')
        selected.append({**f, 'normalized_values': values})
        return values
    clear = read(lc, 'LE_USE_SYNC_CLEAR', [2], [[0, 0, 'ILL_HIGH']])[0]
    load = read(lc, 'LE_USE_SYNC_LOAD', [2], [[0, 0, 'ILL_HIGH']])[0]
    signals = read(lab, 'LAB_ENABLE_SYNC_SIGNALS', [3], [])
    if (clear, load) == (0, 0) and signals in ([0, 0, 0], [0, 0, 1]):
        mode = 'local_sync_off'
        native_mode = 'off'
        sload = 0
    elif (clear, load) == (1, 1) and signals == [0, 0, 0]:
        mode = 'constant_sync_load_datac'
        native_mode = 'on'
        sload = 1
    else:
        raise ValueError('synchronous control combination outside candidate scope')
    return {'mode': mode, 'native_synch_mode': native_mode, 'native_sclr': 0, 'native_sload': sload, 'fields': selected, 'effective_data_port': 'DATAC' if sload else 'LUT_RESULT', 'independent_comparison_required': True, 'productive_emission_allowed': False}
