# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_lc_input_join import predict
from .native_control_source import graph_context
from .native_source_output_role import resolve

def decode(context, payload, lc, graph_and_pins=None):
    fields = [f for f in context['fields'] if f['location'] == lc]
    inputs = predict(fields, payload, context['lc_tables'], context['input_mapping'], context['resources'])
    candidates = [r for r in inputs['rows'] if r['predicted_port'] == 'DATAC']
    if len(candidates) != 1 or candidates[0]['state'] != 'unique_source':
        raise ValueError('register DATAC source unresolved')
    selected = candidates[0]
    graph, pins = graph_context(context, payload) if graph_and_pins is None else graph_and_pins
    trace = graph.trace(selected['source_resource'][0])
    r = trace['terminal']
    result = {'native_lc': lc, 'input_selection': selected, 'trace': trace, 'productive_emission_allowed': False}
    if trace['status'] != 'semantic_boundary':
        raise ValueError('register data route unresolved')
    if r[1] == 301:
        if r[5] != 0 or r[6] != r[4]:
            raise ValueError('data input identity differs')
        pin = pins.get(f'IOC_X{r[2]}_Y{r[3]}_N{r[4]}')
        if pin is None:
            raise ValueError('data input pin unresolved')
        return {**result, 'source': {'kind': 'input_pin', 'pin': pin}}
    role = resolve(r, context['fields'], payload)
    if role['source_port'] != 'COMBOUT':
        raise ValueError('register data requires state-source composition')
    fs = [f for f in context['fields'] if f['location'] == role['canonical_lc']]
    luts = [f for f in fs if f['class'] == 'LE_LUT_FUNCTION']
    carry = [f for f in fs if f['class'] == 'LE_USE_CARRY']
    if len(luts) != 1 or len(carry) != 1:
        raise ValueError('constant data cell fields missing')
    terms = sorted(luts[0]['terms'], key=lambda t: t[1])
    if [(t[0], t[1]) for t in terms] != [(0, n) for n in range(16)]:
        raise ValueError('data cell LUT terms differ')
    mask = sum(((payload[t[3] // 8] >> t[3] % 8 & 1) << t[1] for t in terms))
    if mask not in (0, 65535) or len(carry[0]['terms']) != 1:
        raise ValueError('nonconstant data needs cone composition')
    t = carry[0]['terms'][0]
    if payload[t[3] // 8] >> t[3] % 8 & 1 ^ t[4]:
        raise ValueError('data carry mode not qualified')
    return {**result, 'source': {'kind': 'constant', 'value': int(mask == 65535)}, 'constant_cell': {'role': role, 'lut_field': luts[0], 'carry_field': carry[0], 'lut_mask': mask}, 'requires_independent_constant_cell_check': True}
