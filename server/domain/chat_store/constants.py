"""DEPRECATED compatibility alias to `server.features.chat.constants`."""

import sys

from server.features.chat import constants as _impl

sys.modules[__name__] = _impl
