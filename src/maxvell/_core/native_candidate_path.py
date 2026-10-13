# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_io_port_expressions import local_endpoint

class CandidateGraph:

    def __init__(self, resources, sinks):
        self.resources = {}
        for row in resources:
            if len(row) != 7 or any((type(v) is not int for v in row)) or row[0] in self.resources:
                raise ValueError('invalid or duplicate native resource')
            self.resources[row[0]] = row
        self.sinks = {}
        for row in sinks:
            gid = row['sink_gid']
            if gid not in self.resources or gid in self.sinks:
                raise ValueError('invalid or duplicate native sink')
            self.sinks[gid] = row

    def endpoint(self, expression):
        local = local_endpoint(expression)['selected_local_input']
        identity = [local[k] for k in ('element_enum', 'x', 'y', 'z', 'index')]
        matches = [r[0] for r in self.resources.values() if r[1:6] == identity]
        if len(matches) != 1:
            raise ValueError('native endpoint is not unique')
        return matches[0]

    def trace(self, start):
        path, seen = ([], set())
        gid = start
        while True:
            if gid in seen or gid not in self.resources:
                raise ValueError('cyclic or missing native source')
            seen.add(gid)
            resource = self.resources[gid]
            path.append(resource)
            if resource[1] in (301, 45, 43):
                return {'status': 'semantic_boundary', 'path': path, 'terminal': resource, 'functional_role_proved': False}
            selected = self.sinks.get(gid)
            if selected is None:
                return {'status': 'missing_destination_rule', 'path': path, 'terminal': resource, 'functional_role_proved': False}
            if selected['destination_state'] != 'unique' or len(selected['destination']) != 1 or selected.get('destination_unknown'):
                return {'status': 'unresolved_destination', 'path': path, 'terminal': resource, 'selection': selected, 'functional_role_proved': False}
            gid = selected['destination'][0]
