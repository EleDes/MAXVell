# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
MAX_EXPANDED_NODES = 256

def check(expression):
    pending = [expression]
    count = 0
    while pending:
        value = pending.pop()
        count += 1
        if count > MAX_EXPANDED_NODES:
            raise ValueError('Boolean control expanded expression exceeds256nodes')
        if value['kind'] == 'lut':
            pending.extend(value['inputs'].values())
        elif value['kind'] == 'xor':
            pending.append(value['source'])
    return count
