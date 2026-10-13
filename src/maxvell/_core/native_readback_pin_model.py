# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_dynamic_pin_model import compose as compose_simple
from .native_lc_input_join import PORTS
from .native_dynamic_pin_model import evaluate as evaluate_simple
from .native_pin_pad_mode import output_value

def compose(normal, modes, resources, sinks, cell, output_pin, output_path):
    by_pin = {p['package_pin']: p for p in normal}
    if len(by_pin) != len(normal) or output_pin not in by_pin:
        raise ValueError('readback pin population differs')
    by_io = {p['native_io']: p['package_pin'] for p in normal}
    if len(by_io) != len(normal):
        raise ValueError('duplicate native IO')
    output = by_pin[output_pin]
    if output['expressions']['oe'] != {'kind': 'constant', 'value': 1}:
        raise ValueError('readback output enable outside scope')
    if cell['mode']['predicted_port'] != 'COMBOUT' or cell['missing_influential_ports']:
        raise ValueError('readback cell not completely combinational')
    bindings = {}
    for item in cell['inputs']:
        port = item['predicted_port']
        trace = item['trace']
        if port not in PORTS or port in bindings or trace['status'] != 'semantic_boundary':
            raise ValueError('readback cell input differs')
        r = trace['terminal']
        if r[1] != 301 or r[5] != 0 or r[6] != r[4]:
            raise ValueError('cell source is not sampled pin')
        location = f'IOC_X{r[2]}_Y{r[3]}_N{r[4]}'
        if location not in by_io:
            raise ValueError('sampled pin has no package identity')
        bindings[port] = by_io[location]
    mask = cell['serialized_mask']
    if type(mask) != int or not 0 <= mask < 65536:
        raise ValueError('invalid LUT mask')
    for index, port in enumerate(PORTS):
        if port not in bindings and any((mask >> n & 1 != mask >> (n ^ 1 << index) & 1 for n in range(16))):
            raise ValueError('unbound input influences output')
    expression = output['expressions']['data']
    if output_path['path_kind'] == 'normal':
        if expression['kind'] != 'io_mux_output':
            raise ValueError('normal output expression differs')
        xor = expression['xor']
    elif output_path['path_kind'] == 'direct':
        if expression['kind'] != 'constant':
            raise ValueError('direct inversion source outside scope')
        xor = 1 - expression['value']
    else:
        raise ValueError('unknown output path')
    remaining = [p for p in normal if p['package_pin'] != output_pin]
    rest = compose_simple(remaining, [m for m in modes if m['pin'] != output_pin], resources, sinks)
    output_modes = [m for m in modes if m['pin'] == output_pin]
    if len(output_modes) != 1 or output_modes[0]['native_io'] != output['native_io']:
        raise ValueError('output mode binding differs')
    return {'format': 'maxvrec.native_readback_pin_model.v1', 'pins': sorted(by_pin), 'remainder': rest, 'cell': {'native_lc': cell['candidate_lc'], 'mask': mask, 'bindings': bindings}, 'output': {'pin': output_pin, 'mode': output_modes[0]['mode'], 'xor': xor}, 'inputs': sorted(set(rest['inputs']) | set(bindings.values())), 'sampled_pad_is_independent': True, 'productive_emission_allowed': False}

def evaluate(model, inputs):
    if set(inputs) != set(model['inputs']) or any((type(v) != int or v not in (0, 1) for v in inputs.values())):
        raise ValueError('readback binary input domain differs')
    result = evaluate_simple(model['remainder'], inputs)
    c = model['cell']
    minterm = sum((inputs[c['bindings'][p]] << i for i, p in enumerate(PORTS) if p in c['bindings']))
    out = model['output']
    result[out['pin']] = output_value(out['mode'], c['mask'] >> minterm & 1 ^ out['xor'], 1)
    if set(result) != set(model['pins']):
        raise ValueError('readback output population differs')
    return result
