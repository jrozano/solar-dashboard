"""Handler for ListKeys query."""

import logging

from mediatr import Mediator

from domain.commands.list_keys import ListKeys
from infrastructure.storage.api_key_repo import APIKeyRepository

LOG = logging.getLogger('domain.handlers.list_keys')


@Mediator.handler
class ListKeysHandler:
    """Return all API keys belonging to a specific user."""

    def __init__(self, api_key_repo: APIKeyRepository | None = None):
        self._api_key_repo = api_key_repo

    def handle(self, query: ListKeys) -> list:
        return self._api_key_repo.list_keys(query.user_id)
