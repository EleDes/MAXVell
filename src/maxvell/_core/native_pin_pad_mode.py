# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .native_cff_io_storage import decode_provider

def decode_modes(provider, payload):
    decoded = decode_provider(provider, payload)
    modes = []
    seen = set()
    for field in decoded['fields']:
        if field['kind'] != 'IO_PIN_MODE' or not field['bonded']:
            continue
        pins = field['package_pin_names']
        values = field['values']
        if len(pins) != 1 or len(values) != 1 or values[0][:2] != [0, 0]:
            raise ValueError('native pad-mode shape or pin join differs')
        value = values[0][2]
        if type(value) is not int or value not in (0, 1):
            raise ValueError('native pad mode is not binary')
        if pins[0] in seen:
            raise ValueError('duplicate pad-mode pin')
        seen.add(pins[0])
        modes.append({'native_io': field['location'], 'pin': pins[0], 'mode': 'open_drain' if value else 'push_pull', 'native_value': value, 'cff_ordinals': field['cff_ordinals'], 'independent_mode_comparison_required': True})
    return modes

def output_value(mode, data, oe):
    if mode not in ('push_pull', 'open_drain'):
        raise ValueError('unknown pad mode')
    if any((type(value) is not int or value not in (0, 1) for value in (data, oe))):
        raise ValueError('pad DATA/OE must be binary')
    if oe == 0 or (mode == 'open_drain' and data == 1):
        return 'Z'
    return str(data)
