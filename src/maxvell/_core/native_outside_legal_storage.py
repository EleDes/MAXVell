# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_outside_legal_diagnostic import decode_storage

def decode_provider(provider, payload):
    result = decode_storage(provider, payload)
    result.update({'format': 'maxvrec.native_outside_legal_storage_ir.v1', 'partition': provider['partition'], 'excluded_fields': provider['excluded_fields'], 'coupled_bits': provider['coupled_bits'], 'logical_instances_created': 0, 'functional_influence': 'unresolved'})
    return result
