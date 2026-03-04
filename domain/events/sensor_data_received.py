"""SensorDataReceived domain event."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SensorDataReceived:
    """A new numeric sensor reading arrived from the MQTT broker."""

    sensor: str
    value: float
