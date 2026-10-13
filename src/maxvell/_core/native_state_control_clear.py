# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_register_path_join import selected
from .native_register_enable import scalar
from .native_control_source import graph_context

def decode(context, payload, lc, encoding, clock_prediction, graph_and_pins=None):
    lab = lc.rsplit('_N', 1)[0].replace('LC_', 'LAB_')
    index, field = scalar(context['fields'], payload, lc, 'LE_CLEAR_SELECT')
    polarity, polarity_field = scalar(context['fields'], payload, lab, 'LAB_INVERT', 6 + index)
    candidates = [c for c in clock_prediction['native_clock']['clear_candidates'] if c['index'] == index]
    if len(candidates) != 1:
        raise ValueError('selected clear bank not unique')
    chosen = candidates[0]
    positions = chosen['selection']['positions']
    if len(positions) != 1:
        raise ValueError('selected clear mux unresolved')
    result = {'native_lc': lc, 'native_lab': lab, 'clear_index': index, 'le_selector_field': field, 'selected_bank': chosen, 'polarity_field': polarity_field, 'normalized_polarity': polarity, 'independent_comparison_required': True, 'productive_emission_allowed': False}
    position = positions[0]
    if position == 10:
        if polarity != 0:
            raise ValueError('constant clear mux with nondefault polarity outside candidate scope')
        return {**result, 'status': 'inactive_selected_bank', 'source': {'kind': 'constant', 'value': 0}}
    if position not in range(6):
        raise ValueError('active clear source outside local PIA class')
    fs = [f for f in context['fields'] if (f['location'], f['class'], str(f['index'])) == (lab, 'LAB_PIA_TO_INPUT', str(position))]
    if len(fs) != 1:
        raise ValueError('clear PIA field not unique')
    choice = selected(fs[0], payload, encoding['LAB_PIA_TO_INPUT', position])
    if len(choice['positions']) != 1:
        raise ValueError('clear PIA selection unresolved')
    p = choice['positions'][0]
    x, y = [int(v[1:]) for v in lab.split('_')[1:]]
    kind, line = (276, p) if p < 26 else (43, p - 26)
    resources = [r for r in context['resources'] if r[1:6] == [kind, x, y, 0, line]]
    if len(resources) != 1:
        raise ValueError('clear native source identity not unique')
    graph, pins = graph_context(context, payload) if graph_and_pins is None else graph_and_pins
    trace = graph.trace(resources[0][0])
    terminal = trace['terminal']
    if trace['status'] != 'semantic_boundary':
        raise ValueError('clear source requires routed-role composition')
    if terminal[1] != 301:
        from .native_state_control_source import decode as boolean_decode
        boolean = boolean_decode(context, payload, terminal[0], (graph, pins))
        source = boolean['source']
        if not polarity:
            source = {'kind': 'xor', 'source': source, 'value': 1}
        return {**result, 'status': 'selected_boolean_candidate', 'source': source, 'pia_field': fs[0], 'pia_selection': choice, 'trace': trace, 'boolean_source': boolean}
    if terminal[5] != 0 or terminal[6] != terminal[4]:
        raise ValueError('clear source input identity differs')
    pin = pins.get(f'IOC_X{terminal[2]}_Y{terminal[3]}_N{terminal[4]}')
    if pin is None:
        raise ValueError('clear source pad unbound')
    source = {'kind': 'input_pin', 'pin': pin}
    if not polarity:
        source = {'kind': 'xor', 'source': source, 'value': 1}
    return {**result, 'status': 'selected_input_candidate', 'source': source, 'pia_field': fs[0], 'pia_selection': choice, 'trace': trace}
