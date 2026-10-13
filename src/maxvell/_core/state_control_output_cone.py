# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from copy import deepcopy
from . import state_control_project as project

def extract(model, output_pins, source_ref=None):
    wanted = list(output_pins)
    if not wanted or len(wanted) != len(set(wanted)):
        raise ValueError('unique nonempty output selection required')
    admission = project.check(model)
    rows = {r['pin']: r for r in admission['outputs']}
    pins = {p['pin']: p for p in model['pins']}
    if any((p not in rows or not rows[p]['closed_candidate'] or rows[p]['released'] for p in wanted)):
        raise ValueError('selected output cone is not closed and driven')
    cells, registers, inputs = (set(), set(), set())

    def expression(e):
        kind = e['kind']
        if kind == 'constant':
            return
        if kind == 'input_pin':
            inputs.add(e['pin'])
            return
        if kind == 'xor':
            expression(e['source'])
            return
        if kind == 'lut':
            for value in e['inputs'].values():
                expression(value)
            return
        if kind == 'cell':
            lc = e['native_lc']
            if lc not in cells:
                cells.add(lc)
                for v in model['cells'][lc]['inputs'].values():
                    expression(v)
            return
        if kind == 'register':
            lc = e['native_lc']
            if lc not in registers:
                registers.add(lc)
                r = model['registers'][lc]
                inputs.add(r['clock_pin'])
                for key in ('data', 'aclr', 'aload', 'asynchronous_data', 'enable'):
                    expression(r[key])
            return
        raise ValueError('unresolved expression in selected cone')
    for pin in wanted:
        for key in ('data', 'oe'):
            expression(pins[pin][key])
    if inputs & set(wanted) or any((pins[p]['oe'] != {'kind': 'constant', 'value': 0} for p in inputs)):
        raise ValueError('selected cone requires an independently driven original output pad')
    result = deepcopy(model)
    result.update(cells={lc: deepcopy(model['cells'][lc]) for lc in sorted(cells)}, registers={lc: deepcopy(model['registers'][lc]) for lc in sorted(registers)}, inputs=sorted(inputs), pins=[deepcopy(p) for p in model['pins'] if p['pin'] in inputs | set(wanted)], boundaries=[], native_traces=[], source_roles=[r for r in model.get('source_roles', []) if r.get('canonical_lc') in cells | registers], output_selection={'pins': wanted, 'omitted_original_pins': sorted(set(pins) - inputs - set(wanted)), 'whole_original_equivalence_verified': False})
    project.check(result)
    return result
