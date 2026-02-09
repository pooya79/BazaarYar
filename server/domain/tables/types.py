"""DEPRECATED compatibility alias to `server.features.tables.types`."""

import sys

from server.features.tables import types as _impl

sys.modules[__name__] = _impl
