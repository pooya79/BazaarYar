"""DEPRECATED compatibility alias.

TODO(refactor-cleanup): remove this shim after callers migrate to
`server.features.chat.api`.
"""

import sys

from server.features.chat import api as _impl

sys.modules[__name__] = _impl
