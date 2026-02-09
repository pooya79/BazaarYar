"""DEPRECATED compatibility alias to `server.features.tables.schema`."""

import sys

from server.features.tables import schema as _impl

sys.modules[__name__] = _impl
