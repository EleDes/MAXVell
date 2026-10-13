# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations

def constant(value):
    if type(value) is not int or value not in (0, 1):
        raise ValueError('nonbinary constant')
    return {'kind': 'constant', 'value': value}

def invert(expression, bit):
    if type(bit) is not int or bit not in (0, 1):
        raise ValueError('nonbinary inversion')
    return expression if not bit else {'kind': 'xor', 'value': 1, 'source': expression}
