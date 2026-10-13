# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_control_source import graph_context
from .native_control_source import mapped_source

def scalar(fields, payload, location, kind, index='none'):
    found = [f for f in fields if (f['location'], f['class'], str(f['index'])) == (location, kind, str(index))]
    if len(found) != 1:
        raise ValueError('Enable field not unique: ' + kind)
    field = found[0]
    if field['shape'] != [1] or field['sentinels'] or len(field['terms']) != 1:
        raise ValueError('Enable scalar shape differs')
    s, n, a, o, x = field['terms'][0]
    if any((type(v) != int for v in (s, n, a, o, x))) or (s, n) != (0, 0) or a < 0 or (not 0 <= o < len(payload) * 8) or (x not in (0, 1)):
        raise ValueError('Enable scalar term differs')
    return (payload[o // 8] >> o % 8 & 1 ^ x, field)

def decode(context, payload, lc, encoding, graph_and_pins=None):
    fields = context['fields']
    lab = lc.rsplit('_N', 1)[0].replace('LC_', 'LAB_')
    index, selector = scalar(fields, payload, lc, 'LE_CLOCK_SELECT')
    inactive, field = scalar(fields, payload, lab, 'LAB_ENABLE_CE', index)
    result = {'native_lc': lc, 'native_lab': lab, 'enable_index': index, 'selected_field': field, 'le_selector_field': selector, 'normalized_inactive': inactive, 'source_polarity_proved': False, 'independent_comparison_required': True, 'productive_emission_allowed': False}
    if inactive:
        return {**result, 'status': 'inactive_selected_bank', 'source': {'kind': 'constant', 'value': 1}}
    mux = mapped_source(fields, payload, context['resources'], encoding, lab, 'LAB_CE_FAST_MUX', index)
    if mux['status'] != 'unique_native_source':
        raise ValueError('Enable selected mux unresolved')
    graph, pins = graph_context(context, payload) if graph_and_pins is None else graph_and_pins
    trace = graph.trace(mux['source_resource'][0])
    terminal = trace['terminal']
    if trace['status'] != 'semantic_boundary' or terminal[1] != 301 or terminal[5] != 0 or (terminal[6] != terminal[4]):
        raise ValueError('Enable source outside input-pin class')
    pin = pins.get(f'IOC_X{terminal[2]}_Y{terminal[3]}_N{terminal[4]}')
    if pin is None:
        raise ValueError('Enable input pad not package-bound')
    return {**result, 'status': 'selected_input_candidate', 'source': {'kind': 'input_pin', 'pin': pin}, 'mux': mux, 'trace': trace}
