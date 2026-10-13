# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_register_path_join import predict as local_clock
from .native_control_source import graph_context

def mux_selection(provider, payload, index):
    if len(payload) * 8 != provider['cfm_bits'] or type(index) != int or index not in range(4):
        raise ValueError('global selector input scope differs')
    fs = [f for f in provider['fields'] if f['index'] == index]
    if len(fs) != 1 or fs[0]['shape'] not in ([6, 3], [4, 3]):
        raise ValueError('global selector field not unique')
    width = fs[0]['shape'][0]
    active = [[], []]
    seen = set()
    for stage, ordinal, address, offset, xor in fs[0]['terms']:
        if (stage, ordinal) in seen or stage not in (0, 1) or ordinal not in range(width if stage == 0 else 3) or (type(offset) != int) or (not 0 <= offset < len(payload) * 8) or (xor not in (0, 1)):
            raise ValueError('global selector term differs')
        seen.add((stage, ordinal))
        if payload[offset // 8] >> offset % 8 & 1 ^ xor:
            active[stage].append(ordinal)
    if seen != {(0, i) for i in range(width)} | {(1, i) for i in range(3)}:
        raise ValueError('global selector terms incomplete')
    if len(active[0]) != 1 or len(active[1]) != 1:
        raise ValueError('global selector not uniquely active')
    matches = [i for i, pair in enumerate(provider['encoding']) if pair == [active[0][0], active[1][0]]]
    if len(matches) != 1:
        raise ValueError('global selector encoding not unique')
    return {'index': index, 'position': matches[0], 'active_ordinals': active, 'field': fs[0]}

def decode(context, payload, lc, clock_encoding, global_provider, graph_and_pins=None):
    if context['target'] != global_provider['target']:
        raise ValueError('global provider target differs')
    graph, pins = graph_context(context, payload) if graph_and_pins is None else graph_and_pins
    native = local_clock(context['fields'], payload, clock_encoding, [{'native_lc': lc, 'observed_output_port': 'REGOUT'}], context['resources'])[0]
    positions = native['clock_selection']['positions']
    if len(positions) != 1:
        raise ValueError('LAB clock selector not unique')
    position = positions[0]
    result = {'native_lc': lc, 'native_clock': native, 'productive_emission_allowed': False, 'clock_polarity_proved': False}
    if position < 6:
        if native['state'] != 'unique_native_clock_path':
            raise ValueError('local clock source unresolved')
        start = native['source_resource']
        result['branch'] = 'local_pia'
    elif position < 10:
        x = int(lc.split('_')[1][1:])
        index = position - 6
        candidates = [r for r in context['resources'] if r[1] == 294 and r[2] == x and (r[5] == index)]
        if len(candidates) != 1:
            raise ValueError('native LAB global clock identity not unique')
        start = candidates[0]
        result.update(branch='global', global_index=index)
    else:
        raise ValueError('unsupported LAB clock selector position')
    trace = graph.trace(start[0])
    result['clock_trace'] = trace
    terminal = trace['terminal']
    if terminal[1] == 369:
        if result.get('global_index') != terminal[5]:
            raise ValueError('global mux index differs from selected LAB clock')
        selection = mux_selection(global_provider, payload, terminal[5])
        result['io_global_selection'] = selection
        sources = [r for r in context['resources'] if r[1:6] == [276, terminal[2], terminal[3], 0, selection['position']]]
        if len(sources) != 1:
            raise ValueError('selected global local source not unique')
        if sources[0][0] not in graph.sinks[terminal[0]]['destination']:
            raise ValueError('selected global source outside retained destination population')
        trace = graph.trace(sources[0][0])
        result['input_trace'] = trace
        terminal = trace['terminal']
    if terminal[1] == 289:
        sources = [r for r in context['resources'] if r[1:5] == [301, *terminal[2:5]] and r[5] == 0 and (r[6] == r[4])]
        if len(sources) != 1:
            raise ValueError('clock buffer input identity not unique')
        result['clock_buffer_input_bridge'] = {'buffer': terminal, 'input': sources[0], 'scope': 'same native pad candidate; independent endpoint comparison required'}
        terminal = sources[0]
    elif trace['status'] != 'semantic_boundary':
        raise ValueError('clock input route unresolved')
    if terminal[1] != 301 or terminal[5] != 0 or terminal[6] != terminal[4]:
        raise ValueError('clock terminal is not an input pad')
    pin = pins.get(f'IOC_X{terminal[2]}_Y{terminal[3]}_N{terminal[4]}')
    if pin is None:
        raise ValueError('clock terminal package input unbound')
    return {**result, 'status': 'input_pin_candidate', 'source': {'kind': 'input_pin', 'pin': pin}, 'source_resource': terminal}
