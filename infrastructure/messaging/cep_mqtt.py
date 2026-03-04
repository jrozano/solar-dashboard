"""MQTT client for CEP events - infrastructure messaging adapter.

Subscribes to the Siddhi CEP alerts topic and stores incoming
alerts in the ``AlertRepository``.  Also exposes a ``publish``
method used by domain event handlers to push events to the
topics consumed by Siddhi.
"""

import json
import logging
import threading
import time

import paho.mqtt.client as mqtt

from config import settings
from infrastructure.storage.alert_repo import AlertRepository

LOG = logging.getLogger('infrastructure.messaging.cep_mqtt')


class CepMQTTClient(threading.Thread):
    """Daemon thread: CEP alert subscriber + event publisher."""

    def __init__(
        self,
        alert_repo: AlertRepository,
        broker: str,
        port: int,
        username: str = '',
        password: str = '',
    ) -> None:
        super().__init__(daemon=True)
        self._alert_repo = alert_repo
        self._broker = broker
        self._port = port
        self._client = mqtt.Client()

        if username:
            try:
                self._client.username_pw_set(username, password or None)
                LOG.info('Configured CEP MQTT username authentication')
            except Exception:
                LOG.exception('Failed to set MQTT username/password')

    # ── Publishing ──────────────────────────────────────────────────

    def publish(self, topic: str, payload: str) -> None:
        """Publish a message to an MQTT topic (thread-safe)."""
        try:
            self._client.publish(topic, payload)
        except Exception:
            LOG.exception('Failed to publish to %s', topic)

    # ── MQTT callbacks ──────────────────────────────────────────────

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc) -> None:
        if rc == 0:
            LOG.info('CEP MQTT connected to %s:%s', self._broker, self._port)
            client.subscribe(settings.MQTT_TOPIC_CEP_ALERTS)
            LOG.info('Subscribed to %s', settings.MQTT_TOPIC_CEP_ALERTS)
        else:
            LOG.warning('CEP MQTT connect returned rc=%s', rc)

    def _on_message(self, client: mqtt.Client, userdata, msg) -> None:
        payload = msg.payload.decode('utf-8')
        LOG.debug('CEP message on %s: %s', msg.topic, payload)

        if msg.topic == settings.MQTT_TOPIC_CEP_ALERTS:
            self._handle_cep_alert(payload)

    # ── Internal helpers ────────────────────────────────────────────

    def _handle_cep_alert(self, payload: str) -> None:
        """Parse and store a CEP alert received from Siddhi."""
        try:
            raw = json.loads(payload)
            LOG.info('CEP alert raw payload: %s', raw)
            # Siddhi wraps the fields inside an "event" key.
            data = raw.get('event', raw)
            self._alert_repo.add_alert(
                rule=data.get('rule', 'unknown'),
                severity=data.get('severity', 'info'),
                message=data.get('message', ''),
            )
            LOG.info('CEP alert stored: %s', data.get('rule'))
        except Exception:
            LOG.exception('Failed to parse CEP alert')

    # ── Thread entry point ──────────────────────────────────────────

    def run(self) -> None:
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        while True:
            try:
                self._client.connect(self._broker, self._port, 60)
                self._client.loop_forever()
            except Exception as exc:
                LOG.exception('CEP MQTT connection error: %s', exc)
                time.sleep(5)
