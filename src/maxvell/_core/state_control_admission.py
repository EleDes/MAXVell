# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .state_control_expression import validate
from .state_control_event import classify as structural

def classify(model):
    result = structural(model)
    cells = {}
    controls = []
    for lc, r in model['registers'].items():
        q = r['qualification']
        for port, key in (('aload', 'aload_prediction'), ('aclr', 'clear_prediction')):
            e = r[port]
            v = validate(e)
            if not v['cells'] and (not v['registers']):
                continue
            proof = q.get(key, {})
            if proof.get('source') != e or 'boolean_source' not in proof:
                raise ValueError('state control native source record absent')
            source = proof['boolean_source']
            nodes = {n: row['expression'] for n, row in source['nodes'].items()}
            if nodes != v['cells']:
                raise ValueError('state control native node population differs')
            roles = {row['canonical_lc'] for row in source['source_roles'] if row['source_port'] == 'REGOUT'}
            if roles != v['registers']:
                raise ValueError('state control native register roles differ')
            for n, node in nodes.items():
                if n in cells and cells[n] != node:
                    raise ValueError('state control native node conflict')
                cells[n] = node
                modes = q.get('boolean_source_modes', {}).get(n, {})
                if set(modes) != {'LE_USE_CARRY', 'LE_USE_REGISTER_FEEDBACK'}:
                    raise ValueError('state control ordinary-mode record absent')
                for kind, value in modes.items():
                    f = value.get('field', {})
                    if type(value.get('normalized_value')) is not int or value['normalized_value'] != 0 or f.get('location') != n or (f.get('class') != kind) or (f.get('shape') != [1]) or (f.get('sentinels') != []) or (len(f.get('terms', [])) != 1):
                        raise ValueError('state control ordinary-mode record differs')
            controls.append({'register': lc, 'port': port, 'source_registers': sorted(v['registers']), 'source_cells': sorted(nodes)})
    return {**result, 'native_controls': controls, 'control_lut_cells': sorted(cells), 'native_source_modes_required': True}
