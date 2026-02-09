"""DEPRECATED compatibility alias to `server.features.chat.types`."""

import sys

from server.features.chat import types as _impl

sys.modules[__name__] = _impl
