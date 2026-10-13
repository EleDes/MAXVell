# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from collections import Counter
from collections import defaultdict

def _terms(bits):
    result = {}
    for address, encoding, high in bits:
        if any((type(v) != int for v in (address, encoding, high))) or address < 0 or address in result or (encoding not in (0, 1, 2)) or (high != -1 if encoding == 0 else high not in (0, 1)):
            raise ValueError('route term identity differs')
        result[address] = 1 if encoding == 0 else high
    return result

def compile_predicates(fields, exclusions, bindings, cfm_bits):
    if type(cfm_bits) != int or cfm_bits <= 0:
        raise ValueError('CFM geometry differs')
    offsets = set()
    for address, (offset, xor) in bindings.items():
        if any((type(v) != int for v in (address, offset, xor))) or address < 0 or (not 0 <= offset < cfm_bits) or (xor not in (0, 1)) or (offset in offsets):
            raise ValueError('route binding differs')
        offsets.add(offset)
    excluded = {source: set().union(*(_terms(group).keys() for group in groups)) if groups else set() for source, groups in exclusions.items()}
    rows = []
    seen = set()
    source_groups = set()
    for field in fields:
        source, sink, group = (field[k] for k in ('source_gid', 'sink_gid', 'group'))
        if any((type(v) != int or v < 0 for v in (source, sink, group))) or (source, sink) in seen or (source, group) in source_groups:
            raise ValueError('route pair or group duplicate')
        seen.add((source, sink))
        source_groups.add((source, group))
        destination = _terms(field['bits'])
        composed = {address: 0 for address in excluded.get(source, set())}
        composed.update(destination)
        row = {'source_gid': source, 'sink_gid': sink, 'group': group, 'constant_destination': not destination, 'source_conditions_known': source in exclusions}
        for label, terms in [('destination', destination), ('assembled', composed)]:
            row[label] = [[bindings[a][0], v ^ bindings[a][1]] for a, v in sorted(terms.items()) if a in bindings]
            row[label + '_missing'] = sorted((a for a in terms if a not in bindings))
        rows.append(row)
    return rows

def evaluate(rows, payload, resources):
    sinks = defaultdict(lambda: {'destination': [], 'assembled': [], 'destination_unknown': [], 'assembled_unknown': [], 'constant_destinations': []})
    seen = set()
    for row in rows:
        source, sink = (row['source_gid'], row['sink_gid'])
        if source not in resources or sink not in resources or (source, sink) in seen:
            raise ValueError('route resource or pair differs')
        seen.add((source, sink))
        result = sinks[sink]
        if row['constant_destination']:
            result['constant_destinations'].append(source)
        for label in ('destination', 'assembled'):
            for offset, value in row[label]:
                if type(offset) != int or not 0 <= offset < len(payload) * 8 or type(value) != int or (value not in (0, 1)):
                    raise ValueError('route condition outside payload')
            if row[label + '_missing'] or (label == 'assembled' and (not row['source_conditions_known'])):
                result[label + '_unknown'].append(source)
            elif all((payload[o // 8] >> o % 8 & 1 == v for o, v in row[label])):
                result[label].append(source)
    classes = defaultdict(Counter)
    results = []
    for sink, r in sorted(sinks.items()):
        row = {'sink_gid': sink, 'sink_class': resources[sink][1], **{k: sorted(v) for k, v in r.items()}}
        for label in ('destination', 'assembled'):
            count = len(row[label])
            state = 'unresolved' if row[label + '_unknown'] else 'zero' if count == 0 else 'unique' if count == 1 else 'multiple'
            row[label + '_state'] = state
            classes[row['sink_class']][label + '_' + state] += 1
        row['match_sets_differ'] = row['destination'] != row['assembled']
        classes[row['sink_class']]['sinks'] += 1
        classes[row['sink_class']]['match_sets_differ'] += row['match_sets_differ']
        results.append(row)
    return {'format': 'maxvrec.native_route_predicate_frontier.v1', 'sink_results': results, 'classes': {str(k): dict(v) for k, v in sorted(classes.items())}, 'pair_count': len(rows), 'selected_routes_proved': False, 'productive_emission_allowed': False, 'coverage_credit_allowed': False}
