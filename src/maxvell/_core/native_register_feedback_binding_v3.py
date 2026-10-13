# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_register_enable import scalar

def binding(lc, fields, payload, inputs, mask):
    value, field = scalar(fields, payload, lc, 'LE_USE_REGISTER_FEEDBACK')
    if not value:
        return None
    carry, carry_field = scalar(fields, payload, lc, 'LE_USE_CARRY')
    if carry:
        raise ValueError('register feedback arithmetic mode outside class')
    selectors = [f for f in fields if f['location'] == lc and f['class'] == 'LE_LUT_INPUT']
    if len(selectors) != 4 or {str(f['index']) for f in selectors} != {'0', '1', '2', '3'}:
        raise ValueError('register feedback selector population differs')
    ordinary = [r for r in inputs if r['predicted_port'] == 'DATAC']
    if len(ordinary) > 1:
        raise ValueError('ordinary DATAC population differs')
    return {'predicted_port': 'DATAC', 'state': 'unique_source', 'source_kind': 'register_feedback', 'source_lc': lc, 'source_xor': 1, 'ordinary_datac_rows': ordinary, 'feedback_field': field, 'feedback_value': value, 'carry_field': carry_field, 'carry_value': carry, 'scope': 'Internal same-LC REGOUT to raw LUT-C candidate; independent source comparison required.'}
