# SPDX-License-Identifier: 0BSD
# Standalone functional result consumer.
from __future__ import annotations
from . import native_sequential_cone as base
CONSTANTS = {k: v for k, v in base.CONSTANTS.items() if k not in ('aload', 'ena', 'aclr')}
