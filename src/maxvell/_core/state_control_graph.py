# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
import re
from .native_lc_input_join import PORTS
from .native_pin_pad_mode import output_value
CLASS = 'acyclic_binary_lut_data_oe_with_explicit_cuts.v1'
FORMATS = {'maxvrec.native_partial_cone.v1', 'maxvrec.native_combinational_pin_cone.v1', 'maxvrec.native_sequential_cone.v1'}

def name(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z0-9_]+', value):
        raise ValueError('invalid interface identity')
    return value

def check(model, virtual_state_ports=0):
    if type(virtual_state_ports) != int or not 0 <= virtual_state_ports <= 6 * 4096:
        raise ValueError('invalid virtual state port bound')
    if model.get('format') not in FORMATS or model.get('registers'):
        raise ValueError('model outside combinational class')
    cells, pins, inputs = (model['cells'], model['pins'], model['inputs'])
    if len(cells) > 4096 or len(pins) > 512 + virtual_state_ports or len(inputs) != len(set(inputs)):
        raise ValueError('model population differs')
    for p in inputs:
        name(p)
    pin_ids = [name(p['pin']) for p in pins]
    if len(pin_ids) != len(set(pin_ids)) or set(inputs) - set(pin_ids):
        raise ValueError('pin population differs')
    boundaries = model.get('boundaries', [])
    boundary_ids = {name(b['id']) for b in boundaries}
    if len(boundary_ids) != len(boundaries) or any((not b.get('reason') or not b.get('identity') for b in boundaries)):
        raise ValueError('boundary identities or reasons differ')
    active, visited, order, deps = (set(), set(), [], {})
    used_inputs, used_boundaries = (set(), set())

    def expression(e, depth=0):
        if depth > 256:
            raise ValueError('model expression depth exceeds 256')
        kind = e.get('kind')
        if kind == 'constant' and set(e) == {'kind', 'value'}:
            if type(e['value']) is not int or e['value'] not in (0, 1):
                raise ValueError('nonbinary constant')
            return (set(), set())
        if kind == 'input_pin' and set(e) == {'kind', 'pin'} and (e['pin'] in inputs):
            used_inputs.add(e['pin'])
            return (set(), {e['pin']})
        if kind == 'boundary' and set(e) == {'kind', 'id'} and (e['id'] in boundary_ids):
            used_boundaries.add(e['id'])
            return ({e['id']}, set())
        if kind == 'xor' and set(e) == {'kind', 'value', 'source'}:
            if type(e['value']) is not int or e['value'] not in (0, 1):
                raise ValueError('nonbinary inversion')
            return expression(e['source'], depth + 1)
        if kind == 'lut':
            from .state_control_projection import validate
            validate(e)
            ds = [expression(e['inputs'][p], depth + 1) for p in PORTS]
            return (set().union(*(d[0] for d in ds)), set().union(*(d[1] for d in ds)))
        if kind != 'cell' or set(e) != {'kind', 'native_lc'} or e['native_lc'] not in cells:
            raise ValueError('unknown or malformed expression')
        lc = e['native_lc']
        if lc in active:
            raise ValueError('unbroken combinational cycle')
        if lc not in visited:
            c = cells[lc]
            if c.get('native_lc') != lc or type(c['mask']) is not int or (not 0 <= c['mask'] < 65536) or (set(c['inputs']) != set(PORTS)):
                raise ValueError('LUT schema differs')
            active.add(lc)
            ds = [expression(c['inputs'][p], depth + 1) for p in PORTS]
            deps[lc] = (set().union(*(d[0] for d in ds)), set().union(*(d[1] for d in ds)))
            active.remove(lc)
            visited.add(lc)
            order.append(lc)
        return deps[lc]
    rows = []
    for p in pins:
        if p['mode'] not in ('push_pull', 'open_drain'):
            raise ValueError('unsupported output mode')
        data, oe = (expression(p['data']), expression(p['oe']))
        bs, ins = (data[0] | oe[0], data[1] | oe[1])
        released = p['oe'] == {'kind': 'constant', 'value': 0} or (p['mode'] == 'open_drain' and p['data'] == {'kind': 'constant', 'value': 1})
        if released:
            bs, ins = (set(), set())
        rows.append({'pin': p['pin'], 'boundaries': sorted(bs), 'sampled_inputs': sorted(ins), 'closed_candidate': not bs, 'released': released, 'constant_drive': not released and (not bs) and (not ins)})
    if set(cells) != visited or set(inputs) != used_inputs or boundary_ids != used_boundaries:
        raise ValueError('unused or unreachable model members')
    return {'class_id': CLASS, 'model_class_accepted': True, 'topological_cells': order, 'outputs': rows, 'metrics': {'total_pin_relations': len(rows), 'closed_candidate_pin_relations': sum((r['closed_candidate'] for r in rows)), 'closed_nonconstant_output_paths': sum((r['closed_candidate'] and (not r['released']) and (not r['constant_drive']) for r in rows)), 'conditional_pin_relations': sum((not r['closed_candidate'] for r in rows)), 'constant_drive_relations': sum((r['constant_drive'] for r in rows)), 'released_relations': sum((r['released'] for r in rows)), 'open_interfaces': len(boundaries), 'lut_cells': len(cells), 'register_models': 0}, 'original_equivalence_verified': False, 'compile_verified': False}

def evaluate(model, inputs, boundaries, virtual_state_ports=0):
    admission = check(model, virtual_state_ports)
    if set(inputs) != set(model['inputs']) or set(boundaries) != {b['id'] for b in model.get('boundaries', [])} or any((type(v) is not int or v not in (0, 1) for v in [*inputs.values(), *boundaries.values()])):
        raise ValueError('binary input domain differs')
    values = {}

    def e(x):
        if x['kind'] == 'constant':
            return x['value']
        if x['kind'] == 'input_pin':
            return inputs[x['pin']]
        if x['kind'] == 'boundary':
            return boundaries[x['id']]
        if x['kind'] == 'xor':
            return e(x['source']) ^ x['value']
        if x['kind'] == 'lut':
            return x['mask'] >> sum((e(x['inputs'][p]) << i for i, p in enumerate(PORTS))) & 1
        return values[x['native_lc']]
    for lc in admission['topological_cells']:
        c = model['cells'][lc]
        values[lc] = c['mask'] >> sum((e(c['inputs'][p]) << i for i, p in enumerate(PORTS))) & 1
    return {p['pin']: output_value(p['mode'], e(p['data']), e(p['oe'])) for p in model['pins']}
