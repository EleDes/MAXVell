# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from copy import deepcopy
from .state_control_expression import expression
from .native_enabled_register_v8 import CONSTANTS
from . import state_control_graph as lut
from .native_lc_input_join import PORTS
CLASS = 'partial_opposite_edge_state_controls.v1'

def view(model):
    if model.get('format') != 'maxvrec.native_partial_state_cone.v7':
        raise ValueError('partial state format differs')
    if len(model['pins']) > 512 or len(model['registers']) > 4096:
        raise ValueError('physical pin or state population exceeds bound')
    m = deepcopy(model)
    registers = m.pop('registers')
    m['format'] = 'maxvrec.native_partial_cone.v1'
    ids = {lc: 'state_' + lut.name(lc) for lc in registers}
    virtual = {}

    def convert(e):
        if e.get('kind') == 'register':
            if set(e) != {'kind', 'native_lc'} or e['native_lc'] not in ids:
                raise ValueError('unknown state expression')
            return {'kind': 'boundary', 'id': ids[e['native_lc']]}
        return {k: convert(v) if isinstance(v, dict) else v for k, v in e.items()}
    for c in m['cells'].values():
        c['inputs'] = {p: convert(e) for p, e in c['inputs'].items()}
    for p in m['pins']:
        for k in ('data', 'oe'):
            p[k] = convert(p[k])
    for lc, r in sorted(registers.items()):
        q = r['qualification']
        if r['native_lc'] != lc or r['clock_edge'] not in ('rising', 'falling') or q['native_lc'] != lc or (q['control_constants'] != CONSTANTS) or (q['clock_edge'] != r['clock_edge']) or (r['enable'] != q['enable']) or (r['aclr'] != q['aclr']) or (r['clock_pin'] != q['clock_pin']) or (r['aload'] != q['aload']) or (r['asynchronous_data'] != q['asynchronous_data']):
            raise ValueError('partial state predicate differs')
        if q.get('effective_data') is not None and r['data'] != q['effective_data']:
            raise ValueError('effective register D differs')
        for e in (r['aclr'], r['aload'], r['asynchronous_data'], r['enable']):
            expression(e, {p: 0 for p in m['inputs']}, {lc: 0 for lc in registers})
        m['boundaries'].append({'id': ids[lc], 'identity': lc + ':state', 'reason': 'corresponding binary state variable'})
        virtual[lc] = {}
        for k, e in {'aclr': r['aclr'], 'data': r['data'], 'clock': {'kind': 'input_pin', 'pin': r['clock_pin']}, 'aload': r['aload'], 'async_data': r['asynchronous_data'], 'enable': r['enable']}.items():
            pin = '__state_' + lc + '_' + k
            virtual[lc][k] = pin
            m['pins'].append({'pin': pin, 'mode': 'push_pull', 'data': convert(e), 'oe': {'kind': 'constant', 'value': 1}})
    return (m, ids, virtual)

def check(model):
    from .state_control_event import classify
    classify(model)
    m, ids, virtual = view(model)
    admission = lut.check(m, virtual_state_ports=6 * len(ids))
    by_pin = {r['pin']: r for r in admission['outputs']}
    deps = {ids[lc]: set().union(*(set(by_pin[p]['boundaries']) for p in vs.values())) for lc, vs in virtual.items()}

    def expanded(boundaries):
        pending = list(boundaries)
        seen = set()
        cuts = set()
        while pending:
            b = pending.pop()
            if b in seen:
                continue
            seen.add(b)
            if b in deps:
                pending.extend(deps[b])
            else:
                cuts.add(b)
        return cuts
    rows = []
    for p in model['pins']:
        row = by_pin[p['pin']]
        bs = expanded(row['boundaries'])
        has_state = bool(set(row['boundaries']) & set(ids.values()))
        rows.append({**row, 'boundaries': sorted(bs), 'closed_candidate': not bs, 'constant_drive': row['constant_drive'] and (not has_state)})
    metrics = {**admission['metrics'], 'total_pin_relations': len(rows), 'closed_candidate_pin_relations': sum((r['closed_candidate'] for r in rows)), 'closed_nonconstant_output_paths': sum((r['closed_candidate'] and (not r['released']) and (not r['constant_drive']) for r in rows)), 'conditional_pin_relations': sum((not r['closed_candidate'] for r in rows)), 'released_relations': sum((r['released'] for r in rows)), 'constant_drive_relations': sum((r['constant_drive'] for r in rows)), 'open_interfaces': len(model['boundaries']), 'register_models': len(ids), 'closed_register_models': sum((not expanded(deps[b]) for b in ids.values()))}
    return {'class_id': CLASS, 'model_class_accepted': True, 'topological_cells': admission['topological_cells'], 'outputs': rows, 'metrics': metrics, 'original_equivalence_verified': False, 'compile_verified': False}

def evaluate(model, inputs, boundaries, state):
    check(model)
    m, ids, virtual = view(model)
    if set(state) != set(ids):
        raise ValueError('state domain differs')
    values = lut.evaluate(m, inputs, {**boundaries, **{ids[lc]: v for lc, v in state.items()}}, virtual_state_ports=6 * len(ids))
    return {'pins': {p['pin']: values[p['pin']] for p in model['pins']}, 'register_data': {lc: int(values[v['data']]) for lc, v in virtual.items()}}

def step(model, before, after, boundaries, state):
    from .state_control_event import step as state_step
    return state_step(model, before, after, boundaries, state)

def render(model):
    admission = check(model)
    cells = {lc: 'c' + str(i) for i, lc in enumerate(admission['topological_cells'])}
    regs = model['registers']
    sampled = ['sample_' + lut.name(p) for p in model['inputs']]
    cuts = ['open_' + lut.name(b['id']) for b in model['boundaries']]
    pins = [lut.name(p['pin']) for p in model['pins']]
    outputs = [f'{role}_{p}' for p in pins for role in ('data', 'oe')]
    lines = ['// PARTIAL STATE DRAFT: unknown boundaries and initial states are not inferred.', 'module recovered_core(' + ','.join(sampled + cuts + outputs) + ');']
    if sampled + cuts:
        lines.append('input wire ' + ','.join(sampled + cuts) + ';')
    if outputs:
        lines.append('output wire ' + ','.join(outputs) + ';')

    def e(x):
        kind = x['kind']
        if kind == 'constant':
            return "1'b" + str(x['value'])
        if kind == 'input_pin':
            return 'sample_' + lut.name(x['pin'])
        if kind == 'lut':
            from .boolean_control_expression import render_lut
            return render_lut(x, e)
        if kind == 'boundary':
            return 'open_' + lut.name(x['id'])
        if kind == 'register':
            return 'q_' + lut.name(x['native_lc'])
        if kind == 'xor':
            return '(' + e(x['source']) + " ^ 1'b" + str(x['value']) + ')'
        return cells[x['native_lc']]
    for lc in sorted(regs):
        lines.append('wire q_' + lut.name(lc) + ';')
    for lc in admission['topological_cells']:
        c = model['cells'][lc]
        ident = cells[lc]
        lines += [f"wire [15:0] lut_{ident}=16'h{c['mask']:04x};", f'wire {ident};', f'assign {ident}=lut_{ident}[{{' + ','.join((e(c['inputs'][p]) for p in reversed(PORTS))) + '}];']
    for lc, r in sorted(regs.items()):
        q = 'q_' + lut.name(lc)
        clock = ('~' if r['clock_edge'] == 'falling' else '') + 'sample_' + r['clock_pin']
        a = e(r['aload'])
        d = e(r['asynchronous_data'])
        ident = 'state_' + lut.name(lc)
        ports = {'dataa': e(r['data']), 'datab': "1'b0", 'datac': d, 'datad': "1'b0", 'clk': clock, 'aload': a, 'ena': e(r['enable']), 'aclr': e(r['aclr']), 'sclr': "1'b0", 'sload': "1'b0", 'regcascin': "1'b0", 'inverta': "1'b0", 'cin': "1'b0", 'regout': q}
        # Explicit empty bindings preserve the primitive's existing unconnected
        # input defaults and mark unused outputs without missing-port warnings.
        ports.update({p: '' for p in ('cin0', 'cin1', 'devclrn', 'devpor', 'combout', 'cout', 'cout0', 'cout1')})
        lines.append('maxv_lcell ' + ident + ' (' + ','.join(('.' + p + '(' + v + ')' for p, v in ports.items())) + ');')
        for key, value in {'lut_mask': 'aaaa', 'operation_mode': 'normal', 'output_mode': 'reg_only', 'register_cascade_mode': 'off', 'sum_lutc_input': 'datac', 'synch_mode': 'off'}.items():
            lines.append('defparam ' + ident + '.' + key + ' = "' + value + '";')
    for p in model['pins']:
        pin = p['pin']
        data = e(p['data'])
        oe = e(p['oe'])
        if p['mode'] == 'open_drain':
            data, oe = ("1'b0", '(' + oe + ') & ~(' + data + ')')
        lines += [f'assign data_{pin}={data};', f'assign oe_{pin}={oe};']
    lines += ['endmodule', 'module recovered(' + ','.join(['p_' + p for p in pins] + cuts) + ');']
    if pins:
        lines.append('inout wire ' + ','.join(('p_' + p for p in pins)) + ';')
    if cuts:
        lines.append('input wire ' + ','.join(cuts) + ';')
    if outputs:
        lines.append('wire ' + ','.join(outputs) + ';')
    connections = [f'.sample_{p}(p_{p})' for p in model['inputs']] + [f'.{p}({p})' for p in cuts + outputs]
    lines.append('recovered_core core(' + ','.join(connections) + ');')
    for pin in pins:
        lines.append(f"assign p_{pin}=oe_{pin} ? data_{pin} : 1'bz;")
    return '\n'.join(lines + ['endmodule', ''])
