"""Alert repository - in-memory store for CEP alerts received from Siddhi."""

from datetime import datetime, timezone
from threading import Lock

from domain.models.cep import CepAlert


class AlertRepository:
    """Thread-safe repository that accumulates alerts published by Siddhi."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._alerts: list[CepAlert] = []
        self._next_id = 1

    def add_alert(self, rule: str, severity: str, message: str) -> CepAlert:
        """Create and persist a new alert."""
        with self._lock:
            alert = CepAlert(
                id=self._next_id,
                rule=rule,
                severity=severity,
                message=message,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._alerts.append(alert)
            self._next_id += 1
            return alert

    def list_alerts(self) -> list[CepAlert]:
        with self._lock:
            return list(self._alerts)

    def clear_alerts(self) -> int:
        with self._lock:
            n = len(self._alerts)
            self._alerts.clear()
            return n
