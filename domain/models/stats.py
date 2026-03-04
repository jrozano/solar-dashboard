from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class SensorValue:
    value: Any
    timestamp: str | None

    def to_primitive(self):
        return {'value': self.value, 'timestamp': self.timestamp}


@dataclass
class Stats:
    values: Dict[str, SensorValue]

    def to_dict(self) -> dict:
        values = {k: v.to_primitive() for k, v in self.values.items()}
        pv = values.get('pv_power', {}).get('value')
        load = values.get('load_power', {}).get('value')
        grid = values.get('grid_power', {}).get('value')
        battery = values.get('battery_power', {}).get('value')
        return {
            'values': values,
            'derived': {
                'pv_power': pv,
                'load_power': load,
                'grid_power': grid,
                'battery_power': battery,
            },
        }
