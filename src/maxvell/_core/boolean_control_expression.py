# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
import re
from .native_lc_input_join import PORTS

def validate(e):
    cells = {}
    pins = set()
    active = set()
    count = 0

    def visit(x, depth=0):
        nonlocal count
        count += 1
        if not isinstance(x, dict) or depth > 32 or count > 4096:
            raise ValueError('Boolean control expression bound exceeded')
        kind = x.get('kind')
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
    return {'inputs': pins, 'cells': cells}

def render_lut(e, render):
    return "(|((16'h" + format(e['mask'], '04x') + ' >> {' + ','.join((render(e['inputs'][p]) for p in reversed(PORTS))) + "}) & 16'h0001))"
