"""DEPRECATED compatibility alias.

TODO(refactor-cleanup): remove this shim after callers migrate to
`server.features.agent.api` modules.
"""

import sys

from server.db.models import Attachment, Conversation
from server.db.session import get_db_session
from server.features.agent.api.router import router
from server.features.agent.api import streaming as _impl
from server.features.attachments.schemas import StoredAttachment

# Preserve legacy monkeypatch points while exposing the canonical router.
_impl.router = router
_impl.get_db_session = get_db_session
_impl.Attachment = Attachment
_impl.Conversation = Conversation
_impl.StoredAttachment = StoredAttachment

sys.modules[__name__] = _impl
