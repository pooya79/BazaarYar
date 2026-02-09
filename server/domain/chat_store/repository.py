"""DEPRECATED compatibility alias to `server.features.chat.repo`."""

import sys

from server.features.chat import repo as _impl

sys.modules[__name__] = _impl
