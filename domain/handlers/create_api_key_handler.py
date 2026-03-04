"""Handler for CreateApiKey command."""

import json
import logging
from typing import Callable

from mediatr import Mediator

from config import settings
from domain.commands.create_api_key import CreateApiKey
from domain.models import ApiKey
from infrastructure.storage.api_key_repo import APIKeyRepository

LOG = logging.getLogger('domain.handlers.create_api_key')


@Mediator.handler
class CreateApiKeyHandler:
    """Create a new API key, publish the event via MQTT, and return the result.

    Encapsulates the full key-creation use case: persistence in the
    repository **and** side-effect notification to Siddhi CEP via MQTT.
    """

    def __init__(
        self,
        api_key_repo: APIKeyRepository | None = None,
        mqtt_publish: Callable[[str, str], None] | None = None,
    ):
        self._api_key_repo = api_key_repo
        self._publish = mqtt_publish

    def handle(self, command: CreateApiKey) -> tuple[str, ApiKey]:
        raw_key, entry = self._api_key_repo.create_key(
            command.user_id, command.name,
        )
        LOG.info('KEY_CREATED user_id=%s name=%s', command.user_id, command.name)

        if self._publish:
            self._publish(
                settings.MQTT_TOPIC_API_KEY_EVENT,
                json.dumps({'user_id': command.user_id, 'name': command.name}),
            )
            LOG.info(
                'Published ApiKeyCreated event for user %s', command.user_id,
            )

        return raw_key, entry
