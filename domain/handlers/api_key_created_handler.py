"""Handler for ApiKeyCreated domain events."""

import json
import logging
from typing import Callable

from mediatr import Mediator

from config import settings
from domain.events.api_key_created import ApiKeyCreated

LOG = logging.getLogger('domain.handlers.api_key_created')


@Mediator.handler
class ApiKeyCreatedHandler:
    """Forward API-key creation events to the Siddhi CEP engine via MQTT."""

    def __init__(self, mqtt_publish: Callable[[str, str], None] | None = None):
        self._publish = mqtt_publish

    def handle(self, event: ApiKeyCreated) -> None:
        if self._publish:
            self._publish(
                settings.MQTT_TOPIC_API_KEY_EVENT,
                json.dumps({'user_id': event.user_id, 'name': event.name}),
            )
            LOG.info('Published ApiKeyCreated event for user %s', event.user_id)
