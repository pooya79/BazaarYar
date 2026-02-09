"""DEPRECATED compatibility alias to `server.features.chat.tokens`."""

import sys

from server.features.chat import tokens as _impl

sys.modules[__name__] = _impl
