"""Handler for GetStats query."""

import logging

from mediatr import Mediator

from domain.commands.get_stats import GetStats
from infrastructure.storage.stats_repo import StatsRepository

LOG = logging.getLogger('domain.handlers.get_stats')


@Mediator.handler
class GetStatsHandler:
    """Return the current sensor statistics from the repository."""

    def __init__(self, stats_repo: StatsRepository | None = None):
        self._stats_repo = stats_repo

    def handle(self, query: GetStats):
        return self._stats_repo.get_stats()
