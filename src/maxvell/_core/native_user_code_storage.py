# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
FORMAT = 'maxvrec.native_user_code_storage_provider.v1'

def validate_provider(provider):
    if provider.get('format') != FORMAT or provider.get('productive_emission_allowed') is not False or provider.get('address_space') != 'CFM_payload_lsb0' or (provider.get('named_native_field') != 'USER_CODE') or (provider.get('native_full_payload_single_bit_scan') is not True) or (provider.get('independent_field_mapping_match') is not True) or (provider.get('native_combined_checks') != 10):
        raise ValueError('native user-code scope differs')
    size = provider.get('cfm_bits')
    rows = provider.get('bindings')
    if type(size) != int or size not in (53248, 110592, 208896, 348160):
        raise ValueError('CFM geometry differs')
    if not isinstance(rows, list) or len(rows) != 32:
        raise ValueError('field population differs')
    if any((not isinstance(r, list) or len(r) != 3 or any((type(v) != int for v in r)) for r in rows)):
        raise ValueError('field binding shape differs')
    if [r[0] for r in rows] != list(range(32)) or len({r[1] for r in rows}) != 32:
        raise ValueError('field identity differs')
    if any((not 0 <= r[1] < size or r[2] not in (0, 1) for r in rows)):
        raise ValueError('field binding domain differs')
    return {r[1] for r in rows}

def decode_provider(provider, payload):
    validate_provider(provider)
    if len(payload) * 8 != provider['cfm_bits']:
        raise ValueError('payload geometry differs')
    value = sum(((payload[offset // 8] >> offset % 8 & 1 ^ xor) << ordinal for ordinal, offset, xor in provider['bindings']))
    return {'format': 'maxvrec.native_user_code_ir.v1', 'target': provider['target'], 'address_space': 'CFM_payload_lsb0', 'width': 32, 'value': value, 'hex': f'{value:08X}', 'bindings': provider['bindings'], 'logical_instances_created': 0, 'productive_emission_allowed': False}
