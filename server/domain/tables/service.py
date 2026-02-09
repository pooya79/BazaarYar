"""DEPRECATED compatibility alias to `server.features.tables.service`."""

import sys

from server.features.tables import service as _impl

sys.modules[__name__] = _impl
