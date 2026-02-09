"""DEPRECATED compatibility alias to `server.features.chat.errors`."""

import sys

from server.features.chat import errors as _impl

sys.modules[__name__] = _impl
