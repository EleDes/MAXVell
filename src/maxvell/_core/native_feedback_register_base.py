# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_control_source import graph_context
from .native_register_enable import decode as enable_decode
from .native_control_source import aload
from .native_load_data import decode as load_data
from .native_clock_polarity import predict as clock_polarity
from . import native_sequential_cone as base
from .native_global_clock_v2 import decode as clock_decode
from .native_state_control_clear import decode as clear_decode
from .native_sync_normalization import predict as sync_predict
CONSTANTS = {k: v for k, v in base.CONSTANTS.items() if k not in ('aload', 'ena', 'aclr')}

def register(context, payload, lc, global_provider, encodings=None, graph=None):
    lab = lc.rsplit('_N', 1)[0].replace('LC_', 'LAB_')
    selected = [f for f in context['fields'] if f['location'] in (lc, lab)]
    lookup = {(f['location'], f['class'], str(f['index'])): f for f in selected}
    if len(lookup) != len(selected):
        raise ValueError('duplicate control field')
    evidence = []

    def require(location, kind, index, expected):
        f = lookup.get((location, kind, str(index)))
        if f is None:
            raise ValueError('control field missing: ' + kind)
        seen = set()
        values = []
        for s, n, a, o, x in f['terms']:
            if any((type(v) != int for v in (s, n, a, o, x))) or not 0 <= o < 8 * len(payload) or x not in (0, 1) or ((s, n) in seen):
                raise ValueError('invalid control term')
            if not 0 <= s < len(f['shape']) or not 0 <= n < f['shape'][s]:
                raise ValueError('control shape differs')
            seen.add((s, n))
            values.append(payload[o // 8] >> o % 8 & 1 ^ x)
        sent = {(s, n) for s, n, name in f['sentinels']}
        if seen & sent or seen | sent != {(s, n) for s, size in enumerate(f['shape']) for n in range(size)}:
            raise ValueError('control population differs')
        if values != expected:
            raise ValueError('control pattern outside candidate scope: ' + kind)
        evidence.append({**f, 'normalized_values': values})
    for kind, value in [('LE_USE_CARRY', 0), ('LE_USE_REG_CASCADE', 1), ('LE_USE_CASCADE_ROUTING', 1)]:
        require(lc, kind, 'none', [value])
    from .native_register_enable import scalar
    feedback, feedback_field = scalar(context['fields'], payload, lc, 'LE_USE_REGISTER_FEEDBACK')
    require(lc, 'LE_USE_REGISTER_FEEDBACK', 'none', [feedback])
    for index in (2, 3, 5, 8):
        require(lab, 'LAB_INVERT', index, [0])
    for kind in ('LAB_ENABLE_INVERT_A', 'LAB_ENABLE_INVERT_A_INTO_LABCINT'):
        require(lab, kind, 'none', [0])
    sync = sync_predict(context['fields'], payload, lc)
    evidence.extend(sync['fields'])
    if encodings is None:
        encodings = (context['clock_encoding'], context['control_encoding'])
    if graph is None:
        graph = graph_context(context, payload)
    clock = clock_decode(context, payload, lc, encodings[0], global_provider, graph)
    polarity = clock_polarity(context['fields'], payload, lc)
    if polarity['clock_index'] != clock['native_clock']['clock_index']:
        raise ValueError('selected clock polarity bank differs')
    evidence.extend(polarity['fields'])
    clear = clear_decode(context, payload, lc, encodings[0], clock, graph)
    enable = enable_decode(context, payload, lc, encodings[1], graph)
    if enable['enable_index'] != clock['native_clock']['clock_index']:
        raise ValueError('Enable/clock bank identity differs')
    source = aload(context, payload, lc, encodings[1], graph)
    if source['status'] == 'needs_source_role_composition':
        from .native_state_control_source import decode as boolean_decode
        boolean = boolean_decode(context, payload, source['trace']['terminal'][0], graph)
        source = {**source, 'status': 'boolean_source_candidate', 'source': boolean['source'], 'boolean_source': boolean}
    if 'source' not in source:
        other = [c for c in clock['native_clock']['clear_candidates'] if c['index'] != clear['clear_index']]
        if source['status'] == 'unresolved_presence' and source['presence']['local_lab_values'] == [0, 0] and (len(other) == 1) and (len(other[0]['selection']['positions']) == 1) and (sorted([clear['selected_bank']['selection']['positions'][0], other[0]['selection']['positions'][0]]) in [[p, 10] for p in range(6)]):
            source = {**source, 'status': 'inactive_in_local_clear_lab', 'source': {'kind': 'constant', 'value': 0}, 'independent_comparison_required': True}
        else:
            raise ValueError('load source unresolved: ' + source['status'])
    data = load_data(context, payload, lc, graph) if source['source'] != {'kind': 'constant', 'value': 0} else None
    effective_data = load_data(context, payload, lc, graph) if sync['native_sload'] else None
    if effective_data and source['source'] != {'kind': 'constant', 'value': 0}:
        raise ValueError('combined synchronous/asynchronous load outside candidate scope')
    return {'synchronous_normalization': sync, 'effective_data': effective_data['source'] if effective_data else None, 'effective_data_prediction': effective_data, 'native_lc': lc, 'clock_pin': clock['source']['pin'], 'clock_source_resource': clock['source_resource'], 'enable': enable['source'], 'enable_prediction': enable, 'aclr': clear['source'], 'clear_prediction': clear, 'clock_edge': polarity['clock_edge'], 'clock_polarity': polarity, 'data_source': {'native_lc': lc, 'port': 'LUT_RESULT'}, 'control_constants': CONSTANTS, 'aload': source['source'], 'asynchronous_data': data['source'] if data else {'kind': 'constant', 'value': 0}, 'clock_prediction': clock, 'aload_prediction': source, 'data_prediction': data, 'control_fields': evidence, 'independent_comparison_required': True, 'productive_emission_allowed': False}
