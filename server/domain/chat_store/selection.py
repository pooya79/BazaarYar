"""DEPRECATED compatibility alias to `server.features.chat.selection`."""

import sys

from server.features.chat import selection as _impl

sys.modules[__name__] = _impl
