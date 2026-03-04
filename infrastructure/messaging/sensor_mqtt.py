"""MQTT client for sensor stats - infrastructure messaging adapter.

Subscribes to Home-Assistant sensor topics, updates the stats
repository, and dispatches ``SensorDataReceived`` domain events
via the Mediator so that the handler can forward them to Siddhi.
"""

import logging
import threading
import time

import paho.mqtt.client as mqtt

from config import settings
from domain.events.sensor_data_received import SensorDataReceived
from infrastructure.storage.stats_repo import StatsRepository, TOPIC_KEY_MAP
from mediatr import Mediator

LOG = logging.getLogger('infrastructure.messaging.sensor_mqtt')


class SensorMQTTClient(threading.Thread):
    """Daemon thread: subscribes to HA sensor topics."""

    def __init__(
        self,
        stats_repo: StatsRepository,
        mediator: Mediator,
        broker: str,
        port: int,
        topics: list[str],
        username: str = '',
        password: str = '',
    ) -> None:
        super().__init__(daemon=True)
        self._stats_repo = stats_repo
        self._mediator = mediator
        self._broker = broker
        self._port = port
        self._topics = topics
        self._client = mqtt.Client()

        if username:
            try:
                self._client.username_pw_set(username, password or None)
                LOG.info('Configured MQTT username authentication')
            except Exception:
                LOG.exception('Failed to set MQTT username/password')

    # ── MQTT callbacks ──────────────────────────────────────────────

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc) -> None:
        if rc == 0:
            LOG.info('Sensor MQTT connected to %s:%s', self._broker, self._port)
            for topic in self._topics:
                client.subscribe(topic)
                LOG.info('Subscribed to %s', topic)
        else:
            LOG.warning('Sensor MQTT connect returned rc=%s', rc)

    def _on_message(self, client: mqtt.Client, userdata, msg) -> None:
        payload = msg.payload.decode('utf-8')
        LOG.debug('Sensor message on %s: %s', msg.topic, payload)

        self._stats_repo.update_topic(msg.topic, payload)

        # Dispatch domain event for numeric values
        key = TOPIC_KEY_MAP.get(msg.topic)
        if key:
            try:
                value = float(payload)
                self._mediator.send(SensorDataReceived(sensor=key, value=value))
            except (ValueError, TypeError):
                pass  # Skip non-numeric values for CEP

    # ── Thread entry point ──────────────────────────────────────────

    def run(self) -> None:
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        while True:
            try:
                self._client.connect(self._broker, self._port, 60)
                self._client.loop_forever()
            except Exception as exc:
                LOG.exception('Sensor MQTT connection error: %s', exc)
                time.sleep(5)
