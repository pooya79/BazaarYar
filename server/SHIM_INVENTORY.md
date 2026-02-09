# Shim Inventory

Temporary compatibility shims introduced during the feature-slice refactor.

- `server/api/agents/router.py` -> `server.features.agent.api.router`
- `server/api/conversations/router.py` -> `server.features.chat.api`
- `server/api/tables/router.py` -> `server.features.tables.api`
- `server/agents/attachments.py` -> `server.features.attachments`
- `server/domain/chat_store/__init__.py` -> `server.features.chat`
- `server/domain/chat_store/constants.py` -> `server.features.chat.constants`
- `server/domain/chat_store/errors.py` -> `server.features.chat.errors`
- `server/domain/chat_store/repository.py` -> `server.features.chat.repo`
- `server/domain/chat_store/selection.py` -> `server.features.chat.selection`
- `server/domain/chat_store/tokens.py` -> `server.features.chat.tokens`
- `server/domain/chat_store/types.py` -> `server.features.chat.types`
- `server/domain/tables/__init__.py` -> `server.features.tables`
- `server/domain/tables/errors.py` -> `server.features.tables.errors`
- `server/domain/tables/importers.py` -> `server.features.tables.importers`
- `server/domain/tables/query_engine.py` -> `server.features.tables.query_engine`
- `server/domain/tables/repository.py` -> `server.features.tables.repo`
- `server/domain/tables/schema.py` -> `server.features.tables.schema`
- `server/domain/tables/service.py` -> `server.features.tables.service`
- `server/domain/tables/types.py` -> `server.features.tables.types`
