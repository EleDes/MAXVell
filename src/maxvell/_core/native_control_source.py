# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from . import native_io_storage as io
from .native_route_predicate_frontier import evaluate
from .native_io_port_expressions import decode as decode_io
from .native_candidate_path import CandidateGraph
from .native_register_path_join import selected
import re
from .native_aload_predicate import predict as presence
FORMAT = 'maxvrec.native_control_source.v1'

def mapped_source(fields, payload, resources, encoding, lab, kind='LAB_ALOAD_FAST_MUX', index=0):
    match = re.fullmatch('LAB_X([1-9][0-9]*)_Y([1-9][0-9]*)', lab)
    if not match:
        raise ValueError('LAB identity differs')
    lookup = {(f['location'], f['class'], str(f['index'])): f for f in fields}
    if len(lookup) != len(fields):
        raise ValueError('duplicate native field')
    f = lookup[lab, kind, str(index)]
    if f['shape'] != [1] or f['sentinels'] or len(f['terms']) != 1:
        raise ValueError('fast mux field differs')
    s, o, a, offset, xor = f['terms'][0]
    if (s, o) != (0, 0) or not 0 <= offset < len(payload) * 8 or xor not in (0, 1):
        raise ValueError('fast mux term differs')
    value = payload[offset // 8] >> offset % 8 & 1 ^ xor
    fast, pias = encoding
    positions = [i for i, x in enumerate(fast[kind, index]) if x == str(value)]
    if len(positions) != 1:
        raise ValueError('fast mux selection not unique')
    pia_index = positions[0]
    pia = lookup[lab, 'LAB_PIA_TO_INPUT', str(pia_index)]
    choice = selected(pia, payload, pias['LAB_PIA_TO_INPUT', pia_index])
    base = {'native_lab': lab, 'fast_field': f, 'fast_value': value, 'pia_index': pia_index, 'pia_field': pia, 'pia_selection': choice, 'condition_offsets': sorted({t[3] for field in (f, pia) for t in field['terms']})}
    if len(choice['positions']) != 1:
        return {**base, 'status': 'unresolved_pia'}
    p = choice['positions'][0]
    x, y = map(int, match.groups())
    kind_id = 276 if p < 26 else 43
    line = p if p < 26 else p - 26
    rs = [r for r in resources if r[1:6] == [kind_id, x, y, 0, line]]
    if len(rs) != 1:
        raise ValueError('native selected source identity not unique')
    return {**base, 'status': 'unique_native_source', 'pia_position': p, 'source_resource': rs[0]}

def graph_context(context, payload):
    resources = context['resources']
    sinks = evaluate(context['compiled'], payload, {r[0]: r for r in resources})['sink_results']
    normal = decode_io(context['providers'][io.CAPABILITY_ID]['fields'], payload, context['io_tables'])
    return (CandidateGraph(resources, sinks), {r['native_io']: r['package_pin'] for r in normal})

def aload(context, payload, lc, encoding, graph_and_pins=None):
    p = presence(context['fields'], payload, lc)
    result = {'format': FORMAT, 'native_lc': lc, 'presence': p, 'productive_emission_allowed': False, 'source_polarity_proved': False, 'event_behavior_proved': False}
    if p['aload_connected'] is False:
        return {**result, 'status': 'inactive', 'source': {'kind': 'constant', 'value': 0}}
    if p['aload_connected'] is not True:
        return {**result, 'status': 'unresolved_presence'}
    mux = mapped_source(context['fields'], payload, context['resources'], encoding, p['native_lab'])
    result['mux'] = mux
    if mux['status'] != 'unique_native_source':
        return {**result, 'status': 'unresolved_mux'}
    graph, pins = graph_context(context, payload) if graph_and_pins is None else graph_and_pins
    trace = graph.trace(mux['source_resource'][0])
    result['trace'] = trace
    if trace['status'] != 'semantic_boundary':
        return {**result, 'status': 'unresolved_route'}
    r = trace['terminal']
    if r[1] != 301:
        return {**result, 'status': 'needs_source_role_composition'}
    if r[5] != 0 or r[6] != r[4]:
        raise ValueError('input resource identity differs')
    pin = pins.get(f'IOC_X{r[2]}_Y{r[3]}_N{r[4]}')
    if pin is None:
        raise ValueError('selected input pin unbound')
    return {**result, 'status': 'input_pin_source', 'source': {'kind': 'input_pin', 'pin': pin}}
