"""DEPRECATED compatibility alias to `server.features.tables.query_engine`."""

import sys

from server.features.tables import query_engine as _impl

sys.modules[__name__] = _impl
