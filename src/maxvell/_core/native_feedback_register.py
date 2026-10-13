# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from .boolean_control_budget import check
from .state_control_expression import validate
from .native_register_enable import scalar
from .native_feedback_register_base import register as previous

def register(context, payload, *args, **kwargs):
    result = previous(context, payload, *args, **kwargs)
    modes = {}
    for key in ('aclr', 'aload', 'asynchronous_data', 'enable', 'effective_data'):
        if result.get(key) is not None:
            validate(result[key])
            check(result[key])
    for key in ('aload_prediction', 'clear_prediction'):
        for lc in result.get(key, {}).get('boolean_source', {}).get('nodes', {}):
            if lc in modes:
                continue
            fields = {}
            for kind in ('LE_USE_CARRY', 'LE_USE_REGISTER_FEEDBACK'):
                value, field = scalar(context['fields'], payload, lc, kind)
                if value:
                    raise ValueError('state control source outside ordinary LUT mode')
                fields[kind] = {'normalized_value': value, 'field': field}
            modes[lc] = fields
    if modes:
        result['boolean_source_modes'] = modes
    return result
