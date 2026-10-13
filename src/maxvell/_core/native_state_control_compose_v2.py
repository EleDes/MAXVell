# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .state_control_expression import input_pins as control_input_pins
from .native_combinational_cone import invert
from .native_candidate_path import CandidateGraph
from .state_control_expression import validate as control_validate
from .native_lc_input_join import PORTS
from .native_combinational_cone import constant
FORMAT = 'maxvrec.native_partial_state_cone.v7'

def compose(normal, modes, resources, sinks, load_cell, load_role, load_register):
    graph = CandidateGraph(resources, sinks)
    by_io = {r['native_io']: r['package_pin'] for r in normal}
    by_pin = {r['pin']: r for r in modes}
    if len(by_io) != len(normal) or len(by_pin) != len(modes) or len(set(by_io.values())) != len(normal) or (set(by_io.values()) != set(by_pin)):
        raise ValueError('pin population differs')
    direct = {}
    for row in sinks:
        r = graph.resources[row['sink_gid']]
        if r[1] != 504:
            continue
        loc = f'IOC_X{r[2]}_Y{r[3]}_N{r[4]}'
        if r[5] != 0 or r[6] != r[4] or loc in direct:
            raise ValueError('direct pin identity differs')
        direct[loc] = row
    cells, boundaries, roles, traces = ({}, {}, {}, [])
    registers = {}
    qualified = {}

    def qualify(lc):
        if lc in qualified:
            return qualified[lc]
        q = load_register(lc)
        control_refs = set().union(*(control_validate(q[k])['registers'] for k in ('aclr', 'aload', 'asynchronous_data', 'enable')))
        if control_validate(q['asynchronous_data'])['registers'] or control_validate(q['enable'])['registers'] or len(control_refs) > 1:
            raise ValueError('state control class requires one source and pin-only data/enable')
        for source in control_refs:
            if source == lc:
                raise ValueError('state control self cycle')
            leaf = load_register(source)
            if any((leaf[k] != {'kind': 'constant', 'value': 0} for k in ('aclr', 'aload'))):
                raise ValueError('source register asynchronous control outside separated-edge class')
            if any((control_validate(leaf[k])['registers'] for k in ('aclr', 'aload', 'asynchronous_data', 'enable'))):
                raise ValueError('state control cascade outside one-layer class')
            if leaf['clock_pin'] != q['clock_pin'] or leaf['clock_edge'] == q['clock_edge']:
                raise ValueError('state control requires separated edges of one clock')
            if any((q['clock_pin'] in control_input_pins(q[k]) for k in ('aclr', 'aload'))):
                raise ValueError('control has coincident direct clock input')
            qualified[source] = leaf
        qualified[lc] = q
        return q
    active, inputs = (set(), set())

    def cut(identity, reason):
        if identity not in boundaries:
            boundaries[identity] = {'id': f'b{len(boundaries)}', 'identity': identity, 'reason': reason}
        return {'kind': 'boundary', 'id': boundaries[identity]['id']}

    def resolve(gid):
        trace = graph.trace(gid)
        traces.append(trace)
        if trace['status'] != 'semantic_boundary':
            return cut(f'resource:{gid}', trace['status'])
        r = trace['terminal']
        if r[1] == 301:
            if r[5] != 0 or r[6] != r[4]:
                return cut(f'resource:{r[0]}', 'input resource identity differs')
            pin = by_io.get(f'IOC_X{r[2]}_Y{r[3]}_N{r[4]}')
            if pin is None:
                return cut(f'resource:{r[0]}', 'input pin unbound')
            inputs.add(pin)
            return {'kind': 'input_pin', 'pin': pin}
        try:
            role = load_role(r)
        except ValueError as exc:
            return cut(f'resource:{r[0]}', str(exc))
        roles[r[0]] = role
        lc = role['canonical_lc']
        if role['source_port'] == 'REGOUT':
            return resolve_register(lc)
        if role['source_port'] != 'COMBOUT':
            return cut(f"{lc}:{role['source_port']}", 'unsupported source boundary')
        return resolve_cell(lc)

    def resolve_register(lc):
        if True:
            if lc not in registers:
                try:
                    q = qualify(lc)
                    if q['native_lc'] != lc or q['clock_edge'] not in ('rising', 'falling'):
                        raise ValueError('register identity/edge differs')
                    controls = [q['aclr'], q['aload'], q['asynchronous_data'], q['enable']] + ([q['effective_data']] if q.get('effective_data') is not None else [])
                    control_inputs = set().union(*(control_input_pins(e) for e in controls))
                    if not control_inputs <= set(by_pin):
                        raise ValueError('state control pin unbound')
                    if q['clock_pin'] not in by_pin:
                        raise ValueError('state clock pin unbound')
                except (ValueError, KeyError) as exc:
                    return cut(f'{lc}:REGOUT', str(exc))
                registers[lc] = {'native_lc': lc, 'clock_pin': q['clock_pin'], 'clock_edge': q['clock_edge'], 'aclr': q['aclr'], 'aload': q['aload'], 'asynchronous_data': q['asynchronous_data'], 'enable': q['enable'], 'qualification': q}
                for dependency in sorted(set().union(*(control_validate(e)['registers'] for e in controls))):
                    resolved = resolve_register(dependency)
                    if resolved['kind'] != 'register':
                        raise ValueError('qualified source register did not compose')
                inputs.add(q['clock_pin'])
                inputs.update(control_inputs)
                registers[lc]['data'] = q['effective_data'] if q.get('effective_data') is not None else {'kind': 'cell', 'native_lc': lc} if lc in active else resolve_cell(lc)
            return {'kind': 'register', 'native_lc': lc}

    def resolve_cell(lc):
        if lc in active:
            return cut(f'{lc}:COMBOUT', 'combinational cycle cut; no closed-loop equivalence')
        if lc not in cells:
            if len(active) >= 128:
                return cut(f'{lc}:COMBOUT', 'explicit traversal depth cut at 128 cells')
            if len(cells) + len(active) >= 4096:
                return cut(f'{lc}:COMBOUT', 'cone population bound')
            try:
                raw = load_cell(lc)
                mask = raw['mask']
                if type(mask) is not int or not 0 <= mask < 65536:
                    raise ValueError('invalid LUT mask')
                bindings = {v['predicted_port']: v for v in raw['inputs']}
                if len(bindings) != len(raw['inputs']) or set(bindings) - set(PORTS):
                    raise ValueError('invalid LUT input population')
            except ValueError as exc:
                return cut(f'{lc}:COMBOUT', str(exc))
            active.add(lc)
            ports = {}
            for i, p in enumerate(PORTS):
                influential = any((mask >> n & 1 != mask >> (n ^ 1 << i) & 1 for n in range(16)))
                if not influential:
                    ports[p] = constant(0)
                elif p not in bindings or bindings[p]['state'] != 'unique_source':
                    ports[p] = cut(f'{lc}:{p}', 'influential LUT input unresolved')
                elif bindings[p].get('source_kind') == 'register_feedback':
                    ports[p] = invert(resolve_register(bindings[p]['source_lc']), bindings[p]['source_xor'])
                elif bindings[p].get('source_kind') == 'lut_chain':
                    ports[p] = invert(resolve_cell(bindings[p]['source_lc']), bindings[p]['source_xor'])
                else:
                    ports[p] = resolve(bindings[p]['source_resource'][0])
            cells[lc] = {'native_lc': lc, 'mask': mask, 'inputs': ports, 'native_decode': raw}
            active.remove(lc)
        return {'kind': 'cell', 'native_lc': lc}

    def expr(value, identity):
        if value['kind'] == 'constant':
            return constant(value['value'])
        if value['kind'] != 'io_mux_output':
            return cut(identity, 'unresolved IO selector')
        try:
            gid = graph.endpoint(value)
        except ValueError as exc:
            return cut(identity, str(exc))
        return invert(resolve(gid), value['xor'])
    pins = []
    for row in normal:
        pin, loc = (row['package_pin'], row['native_io'])
        mode = by_pin[pin]
        if mode['native_io'] != loc or mode['mode'] not in ('push_pull', 'open_drain'):
            raise ValueError('pin mode identity or class differs')
        oe = expr(row['expressions']['oe'], f'{loc}:OE')
        data, kind = (constant(0), 'output_disabled')
        if oe != constant(0):
            route, value = (direct.get(loc), row['expressions']['data'])
            if route is None:
                data, kind = (cut(f'{loc}:DATA', 'unexamined direct path'), 'open')
            elif route['destination_state'] == 'zero':
                data, kind = (expr(value, f'{loc}:DATA'), 'normal')
            elif route['destination_state'] == 'unique' and (not route.get('destination_unknown')):
                if value['kind'] == 'constant':
                    data, kind = (invert(resolve(route['sink_gid']), 1 - value['value']), 'direct')
                else:
                    data, kind = (cut(f'{loc}:DATA', 'direct/normal overlap'), 'open')
            else:
                data, kind = (cut(f'{loc}:DATA', 'unresolved direct path'), 'open')
        pins.append({'pin': pin, 'native_io': loc, 'mode': mode['mode'], 'data': data, 'oe': oe, 'path_kind': kind})
    return {'format': FORMAT, 'pins': pins, 'cells': cells, 'registers': registers, 'inputs': sorted(inputs), 'boundaries': list(boundaries.values()), 'source_roles': list(roles.values()), 'native_traces': traces, 'sampled_pads_are_independent': True, 'original_equivalence_verified': False, 'productive_emission_allowed': False}
