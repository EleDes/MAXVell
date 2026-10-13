# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .boolean_control_budget import check as budget
from .state_control_expression import validate
from .state_control_expression import expression
CLASS = 'opposite_edge_single_source_state_controls.v1'
CONTROL_KEYS = ('aclr', 'aload', 'asynchronous_data', 'enable')

def classify(model):
    regs = model['registers']
    dependencies = {}
    matches = []
    for lc, r in regs.items():
        controls = {k: validate(r[k]) for k in CONTROL_KEYS}
        for k in CONTROL_KEYS:
            budget(r[k])
        deps = set().union(*(v['registers'] for v in controls.values()))
        if not deps <= set(regs):
            raise ValueError('state control register absent')
        if controls['asynchronous_data']['registers'] or controls['enable']['registers'] or len(deps) > 1:
            raise ValueError('state controls require one source and pin-only data/enable')
        dependencies[lc] = deps
        for source in deps:
            leaf = regs[source]
            if any((leaf[k] != {'kind': 'constant', 'value': 0} for k in ('aclr', 'aload'))):
                raise ValueError('source register asynchronous control outside separated-edge class')
            if source == lc:
                raise ValueError('state control self cycle')
            if any((validate(leaf[k])['registers'] for k in CONTROL_KEYS)):
                raise ValueError('state control cascade outside one-layer class')
            if leaf['clock_pin'] != r['clock_pin'] or leaf['clock_edge'] == r['clock_edge']:
                raise ValueError('state control requires separated edges of one clock')
            if any((r['clock_pin'] in controls[k]['inputs'] for k in ('aclr', 'aload'))):
                raise ValueError('control has coincident direct clock input')
            matches.append({'register': lc, 'source_register': source, 'clock_pin': r['clock_pin'], 'source_edge': leaf['clock_edge'], 'consumer_edge': r['clock_edge']})
    return {'class_id': CLASS, 'matched_controls': matches, 'input_hash_allowlist_used': False, 'whole_input_equivalence_verified': False, 'scope': 'One-layer single-state-source async controls on opposite edges of one primary clock. Settled binary single-input events only; no timing or startup guarantee.'}

def settled(model, inputs, state):
    for lc, r in model['registers'].items():
        if expression(r['aclr'], inputs, state):
            if state[lc] != 0:
                return False
        elif expression(r['aload'], inputs, state) and state[lc] != expression(r['asynchronous_data'], inputs, state):
            return False
    return True

def step(model, before, after, boundaries, state):
    from . import state_control_project as project
    project.evaluate(model, before, boundaries, state)
    if set(before) != set(after) or sum((before[p] != after[p] for p in before)) > 1:
        raise ValueError('simultaneous independent events outside scope')
    if not settled(model, before, state):
        raise ValueError('inconsistent initial asynchronous state')
    sampled = project.evaluate(model, after, boundaries, state)['register_data']
    next_state = dict(state)
    for lc, r in model['registers'].items():
        if expression(r['aclr'], after, state):
            next_state[lc] = 0
        elif expression(r['aload'], after, state):
            next_state[lc] = expression(r['asynchronous_data'], after, state)
        elif before[r['clock_pin']] == int(r['clock_edge'] == 'falling') and after[r['clock_pin']] == int(r['clock_edge'] == 'rising') and expression(r['enable'], after, state):
            next_state[lc] = sampled[lc]
    for _ in range(2):
        current = dict(next_state)
        for lc, r in model['registers'].items():
            if expression(r['aclr'], after, current):
                next_state[lc] = 0
            elif expression(r['aload'], after, current):
                next_state[lc] = expression(r['asynchronous_data'], after, current)
    if not settled(model, after, next_state):
        raise ValueError('asynchronous state did not settle')
    return {'state': next_state, 'pins': project.evaluate(model, after, boundaries, next_state)['pins']}
