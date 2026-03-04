"""Handler for SensorDataReceived domain events."""

import json
import logging
from typing import Callable

from mediatr import Mediator

from config import settings
from domain.events.sensor_data_received import SensorDataReceived

LOG = logging.getLogger('domain.handlers.sensor_data_received')


@Mediator.handler
class SensorDataReceivedHandler:
    """Forward sensor data to the Siddhi CEP engine via MQTT."""

    def __init__(self, mqtt_publish: Callable[[str, str], None] | None = None):
        self._publish = mqtt_publish

    def handle(self, event: SensorDataReceived) -> None:
        if self._publish:
            self._publish(
                settings.MQTT_TOPIC_SENSOR_EVENT,
                json.dumps({'sensor': event.sensor, 'value': event.value}),
            )
