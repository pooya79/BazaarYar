"""DEPRECATED compatibility alias to `server.features.tables.repo`."""

import sys

from server.features.tables import repo as _impl

sys.modules[__name__] = _impl
