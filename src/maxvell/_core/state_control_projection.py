# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .boolean_control_expression import validate as previous

def validate(expression):

    def convert(x):
        if not isinstance(x, dict):
            return x
        if x.get('kind') == 'boundary':
            if set(x) != {'kind', 'id'} or not isinstance(x['id'], str):
                raise ValueError('malformed projected state boundary')
            return {'kind': 'input_pin', 'pin': 'boundary_' + x['id']}
        return {k: convert(v) for k, v in x.items()}
    return previous(convert(expression))
