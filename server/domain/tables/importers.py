"""DEPRECATED compatibility alias to `server.features.tables.importers`."""

import sys

from server.features.tables import importers as _impl

sys.modules[__name__] = _impl
