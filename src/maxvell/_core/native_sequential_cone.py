# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_lc_input_join import PORTS
from .native_combinational_cone import constant
from .native_pin_pad_mode import output_value
FORMAT = 'maxvrec.native_sequential_cone.v1'
CONSTANTS = {'ena': 1, 'aload': 0, 'aclr': 0, 'sclr': 0, 'sload': 0, 'regcascin': 0, 'inverta': 0}

def evaluate(model, inputs, state):
    if model.get('format') != FORMAT or set(inputs) != set(model['inputs']) or set(state) != set(model['registers']):
        raise ValueError('model input/state domain differs')
    if any((type(v) != int or v not in (0, 1) for v in list(inputs.values()) + list(state.values()))):
        raise ValueError('nonbinary input/state')
    memo = {}
    active = set()

    def value(e):
        kind = e['kind']
        if kind == 'constant':
            return constant(e['value'])['value']
        if kind == 'input_pin':
            return inputs[e['pin']]
        if kind == 'register':
            return state[e['native_lc']]
        if kind == 'xor':
            return value(e['source']) ^ constant(e['value'])['value']
        if kind != 'cell':
            raise ValueError('unknown cone expression')
        lc = e['native_lc']
        if lc in active:
            raise ValueError('combinational cell cycle')
        if lc not in memo:
            active.add(lc)
            c = model['cells'][lc]
            index = sum((value(c['inputs'][p]) << i for i, p in enumerate(PORTS)))
            if type(c['mask']) != int or not 0 <= c['mask'] < 65536:
                raise ValueError('LUT mask invalid')
            memo[lc] = c['mask'] >> index & 1
            active.remove(lc)
        return memo[lc]
    pins = {}
    for p in model['pins']:
        if p['pin'] in pins:
            raise ValueError('duplicate output pin')
        pins[p['pin']] = output_value(p['mode'], value(p['data']), value(p['oe']))
    return {'pins': pins, 'register_data': {lc: value(r['data']) for lc, r in model['registers'].items()}}

def step(model, before, after, state):
    evaluate(model, before, state)
    result = evaluate(model, after, state)
    next_state = dict(state)
    for lc, r in model['registers'].items():
        if r['clock_edge'] != 'rising' or r['clock_pin'] not in after:
            raise ValueError('unsupported clock event')
        if before[r['clock_pin']] == 0 and after[r['clock_pin']] == 1:
            next_state[lc] = result['register_data'][lc]
    return {'state': next_state, 'pins': evaluate(model, after, next_state)['pins']}
