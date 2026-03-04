"""Handler for ListAlerts query."""

import logging

from mediatr import Mediator

from domain.commands.list_alerts import ListAlerts
from infrastructure.storage.alert_repo import AlertRepository

LOG = logging.getLogger('domain.handlers.list_alerts')


@Mediator.handler
class ListAlertsHandler:
    """Return all active CEP alerts from the repository."""

    def __init__(self, alert_repo: AlertRepository | None = None):
        self._alert_repo = alert_repo

    def handle(self, query: ListAlerts) -> list:
        return self._alert_repo.list_alerts()
