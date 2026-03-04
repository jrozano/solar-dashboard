"""Stats repository - stores latest sensor values received via MQTT."""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock

from domain.models import SensorValue, Stats

TOPIC_KEY_MAP: dict[str, str] = {
    'ssd-solar/sensor/energia_importada_de_red_battery/state': 'battery',
    'ssd-solar/sensor/energia_importada_de_red_battery_power/state': 'battery_power',
    'ssd-solar/sensor/energia_importada_de_red_grid_power/state': 'grid_power',
    'ssd-solar/sensor/energia_importada_de_red_load_power/state': 'load_power',
    'ssd-solar/sensor/energia_importada_de_red_pv_power/state': 'pv_power',
}


class StatsRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._data: dict[str, SensorValue] = {
            v: SensorValue(value=None, timestamp=None)
            for v in TOPIC_KEY_MAP.values()
        }

    def update_topic(self, topic: str, raw_value: str) -> None:
        key = TOPIC_KEY_MAP.get(topic)
        if not key:
            return

        try:
            value: float | str = float(raw_value)
        except (ValueError, TypeError):
            value = raw_value

        with self._lock:
            self._data[key].value = value
            self._data[key].timestamp = datetime.now(timezone.utc).isoformat()

    def get_stats(self) -> Stats:
        with self._lock:
            values = deepcopy(self._data)
        return Stats(values=values)
