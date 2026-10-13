# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from . import asmdb_lut_native_anchor_materializer as native
ROW_COLUMNS = ('location', 'native_input_index', 'stage', 'ordinal', 'native_address', 'offset', 'serializer_xor')

def decode_provider(provider, payload):
    validate_provider(provider)
    if len(payload) * 8 != provider['cfm_bits']:
        raise ValueError('native selector payload geometry differs')
    return {'format': 'maxvrec.native_input_selector_storage_ir.v1', 'target': provider['target'], 'row_columns': [*ROW_COLUMNS, 'stored_value', 'native_value'], 'rows': [r + [payload[r[5] // 8] >> r[5] % 8 & 1, payload[r[5] // 8] >> r[5] % 8 & 1 ^ r[6]] for r in provider['rows']], 'selected_source_proved': False, 'productive_emission_allowed': False}

def validate_provider(provider):
    if provider.get('format') != 'maxvrec.native_input_selector_storage_provider.v1' or provider.get('row_columns') != list(ROW_COLUMNS) or provider.get('index_planes') != 19 or (provider.get('independent_check_planes') != 8) or (provider.get('selected_source_proved') is not False) or (provider.get('productive_emission_allowed') is not False):
        raise ValueError('native selector provider boundaries differ')
    fields = {}
    addresses = set()
    offsets = set()
    for row in provider['rows']:
        if len(row) != 7 or not isinstance(row[0], str) or native.LC_PATTERN.fullmatch(row[0]) is None or any((type(v) != int for v in row[1:])):
            raise ValueError('native selector row types differ')
        loc, port, stage, ordinal, address, offset, xor = row
        if port not in range(4) or stage not in (0, 1) or ordinal not in range(6 if stage == 0 else 3) or (address < 0) or (not 0 <= offset < provider['cfm_bits']) or (xor not in (0, 1)):
            raise ValueError('native selector row bounds differ')
        if address in addresses or offset in offsets:
            raise ValueError('native selector duplicate endpoint')
        addresses.add(address)
        offsets.add(offset)
        fields.setdefault((loc, port), set()).add((stage, ordinal))
    expected = {(0, i) for i in range(6)} | {(1, i) for i in range(3)}
    if any((v != expected for v in fields.values())) or len(fields) != provider['verified_fields'] or len(fields) + len(provider['excluded_fields']) != provider['cell_count'] * 4:
        raise ValueError('native selector field completeness differs')
    return offsets
