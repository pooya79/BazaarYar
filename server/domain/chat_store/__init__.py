"""DEPRECATED compatibility alias to `server.features.chat`."""

import sys

from server.features import chat as _impl

sys.modules[__name__] = _impl
