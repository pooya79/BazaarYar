"""DEPRECATED compatibility alias.

TODO(refactor-cleanup): remove this shim after callers migrate to
`server.features.tables.api`.
"""

import sys

from server.features.tables import api as _impl

sys.modules[__name__] = _impl
