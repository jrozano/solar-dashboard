"""Handler for DeleteApiKey command."""

import logging

from mediatr import Mediator

from domain.commands.delete_api_key import DeleteApiKey
from infrastructure.storage.api_key_repo import APIKeyRepository

LOG = logging.getLogger('domain.handlers.delete_api_key')


@Mediator.handler
class DeleteApiKeyHandler:
    """Revoke an API key owned by the requesting user."""

    def __init__(self, api_key_repo: APIKeyRepository | None = None):
        self._api_key_repo = api_key_repo

    def handle(self, command: DeleteApiKey) -> bool:
        deleted = self._api_key_repo.delete_key(command.user_id, command.key_id)
        if deleted:
            LOG.info(
                'KEY_DELETED user_id=%s key_id=%s',
                command.user_id, command.key_id,
            )
        else:
            LOG.warning(
                'KEY_DELETE_NOT_FOUND user_id=%s key_id=%s',
                command.user_id, command.key_id,
            )
        return deleted
