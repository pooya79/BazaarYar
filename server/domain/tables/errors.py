"""DEPRECATED compatibility alias to `server.features.tables.errors`."""

import sys

from server.features.tables import errors as _impl

sys.modules[__name__] = _impl
