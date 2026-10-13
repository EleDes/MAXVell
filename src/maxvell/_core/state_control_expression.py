# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_lc_input_join import PORTS
import re

def validate(e):
    cells = {}
    pins = set()
    registers = set()
    active = set()
    count = 0

    def visit(x, depth=0):
        nonlocal count
        count += 1
        if not isinstance(x, dict) or depth > 32 or count > 4096:
            raise ValueError('Boolean control expression bound exceeded')
        kind = x.get('kind')
        if kind == 'register' and set(x) == {'kind', 'native_lc'} and isinstance(x['native_lc'], str) and re.fullmatch('LC_X[1-9][0-9]*_Y[1-9][0-9]*_N[0-9]', x['native_lc']):
            registers.add(x['native_lc'])
            return
        if kind == 'constant' and set(x) == {'kind', 'value'} and (type(x['value']) is int) and (x['value'] in (0, 1)):
            return
        if kind == 'input_pin' and set(x) == {'kind', 'pin'} and isinstance(x['pin'], str):
            pins.add(x['pin'])
            return
        if kind == 'xor' and set(x) == {'kind', 'source', 'value'} and (type(x['value']) is int) and (x['value'] in (0, 1)):
            visit(x['source'], depth + 1)
            return
        if kind != 'lut' or set(x) != {'kind', 'native_lc', 'mask', 'inputs'}:
            raise ValueError('unsupported Boolean control expression')
        lc = x['native_lc']
        if not isinstance(lc, str) or not re.fullmatch('LC_X[1-9][0-9]*_Y[1-9][0-9]*_N[0-9]', lc) or type(x['mask']) is not int or (not 0 <= x['mask'] < 65536) or (not isinstance(x['inputs'], dict)) or (set(x['inputs']) != set(PORTS)):
            raise ValueError('Boolean control LUT differs')
        if lc in active:
            raise ValueError('Boolean control expression cycle')
        if lc in cells:
            if cells[lc] != x:
                raise ValueError('Boolean control native identity conflicts')
            return
        if len(cells) + len(active) >= 64:
            raise ValueError('Boolean control cell bound exceeded')
        active.add(lc)
        for port in PORTS:
            visit(x['inputs'][port], depth + 1)
        active.remove(lc)
        cells[lc] = x
    visit(e)
    return {'inputs': pins, 'cells': cells, 'registers': registers}

def input_pins(e):
    return validate(e)['inputs']

def expression(e, inputs, state=None):
    state = {} if state is None else state
    required = validate(e)['registers']
    if not required <= set(state) or any((type(state[q]) is not int or state[q] not in (0, 1) for q in required)):
        raise ValueError('control state domain differs')
    pins = input_pins(e)
    if not pins <= set(inputs) or any((type(inputs[p]) is not int or inputs[p] not in (0, 1) for p in pins)):
        raise ValueError('Boolean control input domain differs')

    def value(x):
        if x['kind'] == 'constant':
            return x['value']
        if x['kind'] == 'input_pin':
            return inputs[x['pin']]
        if x['kind'] == 'register':
            return state[x['native_lc']]
        if x['kind'] == 'xor':
            return value(x['source']) ^ x['value']
        return x['mask'] >> sum((value(x['inputs'][p]) << i for i, p in enumerate(PORTS))) & 1
    return value(e)
