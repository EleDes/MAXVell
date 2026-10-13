# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .state_control_admission import classify as previous

def classify(model):
    prior = previous(model)
    matched = []
    unresolved = []
    boundaries = {b['id']: b for b in model['boundaries']}
    for lc, c in model['cells'].items():
        rows = [r for r in c['native_decode']['inputs'] if r.get('source_kind') == 'register_feedback']
        if not rows:
            continue
        if len(rows) != 1:
            raise ValueError('feedback source not unique')
        row = rows[0]
        if row['predicted_port'] != 'DATAC' or row['source_lc'] != lc or any((type(row[k]) is not int or row[k] != v for k, v in (('source_xor', 1), ('feedback_value', 1), ('carry_value', 0)))):
            raise ValueError('feedback binding differs')
        for kind, key in (('LE_USE_REGISTER_FEEDBACK', 'feedback_field'), ('LE_USE_CARRY', 'carry_field')):
            f = row[key]
            if f['location'] != lc or f['class'] != kind or f['shape'] != [1] or f['sentinels'] or (len(f['terms']) != 1):
                raise ValueError('feedback mode field differs')
        influential = any((c['mask'] >> n & 1 != c['mask'] >> (n ^ 4) & 1 for n in range(16)))
        record = {'native_lc': lc, 'port': 'DATAC', 'source_lc': lc, 'influential': influential}
        if influential:
            e = c['inputs']['DATAC']
            if lc in model['registers']:
                if e != {'kind': 'xor', 'source': {'kind': 'register', 'native_lc': lc}, 'value': 1}:
                    raise ValueError('feedback state expression differs')
            else:
                if set(e) != {'kind', 'source', 'value'} or e['kind'] != 'xor' or type(e['value']) is not int or (e['value'] != 1) or (set(e['source']) != {'kind', 'id'}) or (e['source']['kind'] != 'boundary'):
                    raise ValueError('feedback state cut differs')
                b = boundaries.get(e['source']['id'], {})
                if b.get('identity') != lc + ':REGOUT' or not b.get('reason'):
                    raise ValueError('feedback boundary identity differs')
                unresolved.append({**record, 'boundary_id': e['source']['id'], 'reason': b['reason']})
                continue
        matched.append(record)
    return {**prior, 'register_feedback_class': {'class_id': 'ordinary_internal_register_lut_c.v1', 'matched_cells': matched, 'unresolved_state_cells': unresolved, 'input_hash_allowlist_used': False, 'whole_input_equivalence_verified': False}}
