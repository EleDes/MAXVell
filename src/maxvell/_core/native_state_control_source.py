# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_lc_input_join import predict
from .native_lut_chain_candidate import binding as chain_binding
from .native_register_enable import scalar
from .native_control_source import graph_context
from .native_lc_input_join import PORTS
from .native_source_output_role import resolve

def decode(context, payload, start, graph_and_pins=None):
    graph, pins = graph_context(context, payload) if graph_and_pins is None else graph_and_pins
    active = set()
    nodes = {}
    traces = []
    roles = []

    def resource(gid, depth=0):
        if depth > 16:
            raise ValueError('Boolean control depth exceeds16')
        trace = graph.trace(gid)
        traces.append(trace)
        r = trace['terminal']
        if trace['status'] != 'semantic_boundary':
            raise ValueError('Boolean control route unresolved')
        if r[1] == 301:
            if r[5] != 0 or r[6] != r[4]:
                raise ValueError('Boolean control input identity differs')
            pin = pins.get(f'IOC_X{r[2]}_Y{r[3]}_N{r[4]}')
            if pin is None:
                raise ValueError('Boolean control pad unbound')
            return {'kind': 'input_pin', 'pin': pin}
        role = resolve(r, context['fields'], payload)
        roles.append(role)
        if role['source_port'] == 'REGOUT':
            return {'kind': 'register', 'native_lc': role['canonical_lc']}
        if role['source_port'] != 'COMBOUT':
            raise ValueError('Boolean control requires register-state composition')
        return cell(role['canonical_lc'], depth)

    def cell(lc, depth=0):
        if depth > 16:
            raise ValueError('Boolean control depth exceeds16')
        if lc in active:
            raise ValueError('Boolean control combinational cycle')
        if lc in nodes:
            return nodes[lc]['expression']
        if len(nodes) + len(active) >= 64:
            raise ValueError('Boolean control exceeds64cells')
        if scalar(context['fields'], payload, lc, 'LE_USE_CARRY')[0] != 0:
            raise ValueError('Boolean control arithmetic mode outside class')
        fields = [f for f in context['fields'] if f['location'] == lc]
        luts = [f for f in fields if f['class'] == 'LE_LUT_FUNCTION']
        if len(luts) != 1:
            raise ValueError('Boolean control LUT not unique')
        terms = sorted(luts[0]['terms'], key=lambda t: t[1])
        if luts[0]['shape'] != [16] or luts[0]['sentinels'] or [(t[0], t[1]) for t in terms] != [(0, i) for i in range(16)]:
            raise ValueError('Boolean control LUT shape differs')
        if any((len(t) != 5 or any((type(v) != int for v in t)) or (not 0 <= t[3] < len(payload) * 8) or (t[4] not in (0, 1)) for t in terms)):
            raise ValueError('Boolean control LUT serialization differs')
        mask = sum(((payload[t[3] // 8] >> t[3] % 8 & 1) << t[1] for t in terms))
        rows = predict(fields, payload, context['lc_tables'], context['input_mapping'], context['resources'])['rows']
        chain = chain_binding(lc, fields, payload, rows, mask)
        if chain is not None:
            selectors = [f for f in fields if f['class'] == 'LE_LUT_INPUT']
            if len(selectors) != 4 or {str(f['index']) for f in selectors} != {'0', '1', '2', '3'}:
                raise ValueError('Boolean control chain selector population differs')
            rows.append(chain)
        bindings = {r['predicted_port']: r for r in rows}
        if len(bindings) != len(rows):
            raise ValueError('Boolean control input identity duplicated')
        active.add(lc)
        inputs = {}
        for i, port in enumerate(PORTS):
            if not any((mask >> n & 1 != mask >> (n ^ 1 << i) & 1 for n in range(16))):
                inputs[port] = {'kind': 'constant', 'value': 0}
                continue
            row = bindings.get(port)
            if row is None or row['state'] != 'unique_source':
                raise ValueError('Boolean control influential input unresolved')
            inputs[port] = {'kind': 'xor', 'source': cell(row['source_lc'], depth + 1), 'value': row['source_xor']} if row.get('source_kind') == 'lut_chain' else resource(row['source_resource'][0], depth + 1)
        active.remove(lc)
        expression = {'kind': 'lut', 'native_lc': lc, 'mask': mask, 'inputs': inputs}
        nodes[lc] = {'expression': expression, 'lut_field': luts[0], 'input_predictions': rows}
        return expression
    source = resource(start)
    return {'format': 'maxvrec.native_state_control_source.v1', 'source': source, 'nodes': nodes, 'traces': traces, 'source_roles': roles, 'independent_comparison_required': True, 'productive_emission_allowed': False}
