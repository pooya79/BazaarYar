"""DEPRECATED compatibility alias to `server.features.tables`."""

import sys

from server.features import tables as _impl

sys.modules[__name__] = _impl
