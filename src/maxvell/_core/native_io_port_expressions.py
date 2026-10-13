# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
import re
from .native_pin_model import predict

def local_endpoint(expression):
    if expression.get('kind') != 'io_mux_output':
        raise ValueError('not a dynamic IO mux expression')
    match = re.fullmatch('IOC_X(\\d+)_Y(\\d+)_N(\\d+)', expression['native_io'])
    if match is None:
        raise ValueError('invalid native IO coordinate')
    position = expression['table_position']
    if type(position) is not int or not 0 <= position < 18:
        raise ValueError('invalid IO table position')
    role = expression['mux_kind']
    if role not in ('IO_DATA_INPUT', 'IO_PIA_TO_OE'):
        raise ValueError('unknown IO mux role')
    x, y, n = map(int, match.groups())
    return {'selected_local_input': {'element_enum': 276, 'x': x, 'y': y, 'z': 0, 'index': position}, 'sink_role': 'DATAIN' if role == 'IO_DATA_INPUT' else 'OE', 'native_io': expression['native_io']}

def decode(fields, payload, tables):
    result = []
    for row in predict(fields, payload, tables, []):
        expressions = {}
        for port, kind, inversion in (('data', 'IO_DATA_INPUT', 'IO_DATA_INVERT'), ('oe', 'IO_PIA_TO_OE', 'IO_OE_INVERT')):
            position = row['selector_positions'][kind]
            constant = 18 if row['block'] == 'HIO' else 10
            invert = row['native_inverts'][inversion]
            if position is None:
                expression = {'kind': 'unresolved_selector', 'reason': 'nonunique_active_stages'}
            elif position == constant:
                expression = {'kind': 'constant', 'value': 1 ^ invert}
            else:
                expression = {'kind': 'io_mux_output', 'native_io': row['native_io'], 'mux_kind': kind, 'table_position': position, 'xor': invert, 'route_source_resolved': False}
            expressions[port] = expression
        result.append({'native_io': row['native_io'], 'package_pin': row['package_pin'], 'block': row['block'], 'expressions': expressions, 'data_direct_path_status': 'requires_separate_selected_path_evidence', 'productive_emission_allowed': False})
    return result

def evaluate(expression, mux_value=None):
    if expression['kind'] == 'constant':
        value = expression['value']
    elif expression['kind'] == 'io_mux_output':
        if type(mux_value) is not int or mux_value not in (0, 1):
            raise ValueError('missing or nonbinary mux input')
        if type(expression['xor']) is not int or expression['xor'] not in (0, 1):
            raise ValueError('nonbinary mux polarity')
        value = mux_value ^ expression['xor']
    else:
        raise ValueError('unresolved IO selector expression')
    if type(value) is not int or value not in (0, 1):
        raise ValueError('nonbinary IO value')
    return value

def bind_input_root(expression, resources, sink_results, native_io_pins):
    """Follow unique destination predicates; stop at an explicitly joined input.

    The resulting path still needs independent comparison before promotion.
    Source-only conditions are not turned into mandatory route requirements.
    """
    local = local_endpoint(expression)['selected_local_input']
    by_gid = {r[0]: r for r in resources}
    if len(by_gid) != len(resources) or any((len(r) != 7 for r in resources)):
        raise ValueError('resource identity or shape differs')
    matches = [r[0] for r in resources if r[1:6] == [local[k] for k in ('element_enum', 'x', 'y', 'z', 'index')]]
    if len(matches) != 1:
        raise ValueError('native local endpoint not unique')
    sinks = {r['sink_gid']: r for r in sink_results}
    if len(sinks) != len(sink_results):
        raise ValueError('duplicate native sink')
    gid = matches[0]
    path = []
    while True:
        if gid in path or gid not in by_gid:
            raise ValueError('cyclic or missing native source')
        path.append(gid)
        resource = by_gid[gid]
        if resource[1] == 301:
            if resource[5] != 0 or resource[6] != resource[4]:
                raise ValueError('native input port identity differs')
            location = f'IOC_X{resource[2]}_Y{resource[3]}_N{resource[4]}'
            pin = native_io_pins.get(location)
            if not isinstance(pin, str) or not pin:
                raise ValueError('native input package pin unresolved')
            return {'source': {'kind': 'input_pin', 'pin': pin}, 'xor': expression['xor'], 'native_path_gids': list(reversed(path)), 'independent_comparison_required': True}
        selected = sinks.get(gid)
        if selected is None or selected['destination_state'] != 'unique' or len(selected['destination']) != 1 or selected.get('destination_unknown'):
            raise ValueError('native source selection unresolved')
        gid = selected['destination'][0]
