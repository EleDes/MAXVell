# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_io_port_expressions import bind_input_root
from .native_pin_pad_mode import output_value

def compose(normal_pins, modes, resources, sink_results):
    mode_by_pin = {row['pin']: row for row in modes}
    pin_join = {row['native_io']: row['package_pin'] for row in normal_pins}
    if len(mode_by_pin) != len(modes) or len(pin_join) != len(normal_pins):
        raise ValueError('duplicate pin identity')
    if set(mode_by_pin) != {row['package_pin'] for row in normal_pins}:
        raise ValueError('pad mode population differs')
    resource_by_gid = {row[0]: row for row in resources}
    bypass = {}
    for row in sink_results:
        sink = resource_by_gid[row['sink_gid']]
        if sink[1] != 504:
            continue
        if sink[5] != 0 or sink[6] != sink[4]:
            raise ValueError('direct pad identity differs')
        location = f'IOC_X{sink[2]}_Y{sink[3]}_N{sink[4]}'
        if location in bypass:
            raise ValueError('duplicate direct-pad sink')
        bypass[location] = row
    result = []
    for row in normal_pins:
        mode = mode_by_pin[row['package_pin']]
        if mode['native_io'] != row['native_io']:
            raise ValueError('pad mode coordinate differs')
        expressions = row['expressions']
        oe = expressions['oe']
        released = oe == {'kind': 'constant', 'value': 0}
        direct = bypass.get(row['native_io'])
        if not released and (direct is None or direct['destination_state'] != 'zero'):
            raise ValueError('active or unresolved direct path requires separate composition')
        ports = {}
        for port in ('oe', 'data'):
            expression = expressions[port]
            if port == 'data' and released:
                ports[port] = {'kind': 'constant', 'value': 0, 'unused_for_drive': True}
            elif expression['kind'] == 'constant':
                ports[port] = dict(expression)
            else:
                root = bind_input_root(expression, resources, sink_results, pin_join)
                ports[port] = {**root['source'], 'xor': root['xor'], 'native_path_gids': root['native_path_gids']}
        result.append({'pin': row['package_pin'], 'native_io': row['native_io'], 'mode': mode['mode'], 'ports': ports, 'direct_path': 'output_disabled' if released else 'zero_native_candidates'})
    return {'format': 'maxvrec.native_dynamic_pin_model.v1', 'pins': result, 'inputs': sorted({e['pin'] for row in result for e in row['ports'].values() if e['kind'] == 'input_pin'}), 'independent_comparison_required': True, 'productive_emission_allowed': False}

def evaluate(model, inputs):
    values = {}
    for row in model['pins']:
        ports = {}
        for port, expression in row['ports'].items():
            if expression['kind'] == 'constant':
                ports[port] = expression['value']
            elif expression['kind'] == 'input_pin':
                value = inputs[expression['pin']]
                if type(value) is not int or value not in (0, 1):
                    raise ValueError('nonbinary external input')
                ports[port] = value ^ expression['xor']
            else:
                raise ValueError('unresolved model source')
        values[row['pin']] = output_value(row['mode'], ports['data'], ports['oe'])
    return values
