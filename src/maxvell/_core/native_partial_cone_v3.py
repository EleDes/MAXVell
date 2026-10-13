# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations

def validate_chain_fields(model, fields):
    used = {lc for lc, cell in model['cells'].items() if any((row.get('source_kind') == 'lut_chain' for row in cell['native_decode']['inputs']))}
    grouped = {lc: [] for lc in used}
    for field in fields:
        if field['location'] in used and field['class'] == 'LE_LUT_INPUT':
            grouped[field['location']].append(field)
    for lc, rows in grouped.items():
        if len(rows) != 4 or {int(row['index']) for row in rows} != set(range(4)):
            raise ValueError('chain ordinary selector field population incomplete or duplicated: ' + lc)
    return len(used)
