# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_register_enable import scalar

def predict(fields, payload, lc):
    lab = lc.rsplit('_N', 1)[0].replace('LC_', 'LAB_')
    bank, selection = scalar(fields, payload, lc, 'LE_CLOCK_SELECT')
    index = 1 + 3 * bank
    value, field = scalar(fields, payload, lab, 'LAB_INVERT', index)
    return {'native_lc': lc, 'native_lab': lab, 'clock_index': bank, 'invert_index': index, 'inverted': bool(value), 'clock_edge': 'falling' if value else 'rising', 'fields': [selection, field], 'independent_comparison_required': True, 'productive_emission_allowed': False}
