"""Handler for ClearAlerts command."""

import logging

from mediatr import Mediator

from domain.commands.clear_alerts import ClearAlerts
from infrastructure.storage.alert_repo import AlertRepository

LOG = logging.getLogger('domain.handlers.clear_alerts')


@Mediator.handler
class ClearAlertsHandler:
    """Clear all CEP alerts and return the count of removed alerts."""

    def __init__(self, alert_repo: AlertRepository | None = None):
        self._alert_repo = alert_repo

    def handle(self, command: ClearAlerts) -> int:
        count = self._alert_repo.clear_alerts()
        LOG.info('ALERTS_CLEARED user_id=%s count=%d', command.user_id, count)
        return count
