"""Dependency-injection container - single source of truth for all providers.

Uses ``dependency-injector`` to declare every application component
as a provider.  The container is instantiated once in the composition
root and wired to the modules that need automatic injection.
"""

from dependency_injector import containers, providers
from mediatr import Mediator

from config import settings
from domain.handlers.api_key_created_handler import ApiKeyCreatedHandler
from domain.handlers.sensor_data_received_handler import SensorDataReceivedHandler
from domain.handlers.get_stats_handler import GetStatsHandler
from domain.handlers.list_alerts_handler import ListAlertsHandler
from domain.handlers.clear_alerts_handler import ClearAlertsHandler
from domain.handlers.list_keys_handler import ListKeysHandler
from domain.handlers.create_api_key_handler import CreateApiKeyHandler
from domain.handlers.delete_api_key_handler import DeleteApiKeyHandler
from infrastructure.messaging.cep_mqtt import CepMQTTClient
from infrastructure.messaging.sensor_mqtt import SensorMQTTClient
from infrastructure.storage.alert_repo import AlertRepository
from infrastructure.storage.api_key_repo import APIKeyRepository
from infrastructure.storage.stats_repo import StatsRepository
from infrastructure.storage.user_repo import UserRepository


# ── Helper: create a handler factory for Mediator ───────────────────

def _make_handler_factory(
    cep_mqtt: CepMQTTClient,
    stats_repo: StatsRepository,
    alert_repo: AlertRepository,
    api_key_repo: APIKeyRepository,
):
    """Return a callable that Mediator uses to instantiate handler classes.

    Each handler class is mapped to the keyword arguments it requires so
    that the factory can inject the correct dependencies automatically.
    """
    publish = cep_mqtt.publish

    deps: dict[type, dict] = {
        SensorDataReceivedHandler: {'mqtt_publish': publish},
        ApiKeyCreatedHandler: {'mqtt_publish': publish},
        GetStatsHandler: {'stats_repo': stats_repo},
        ListAlertsHandler: {'alert_repo': alert_repo},
        ClearAlertsHandler: {'alert_repo': alert_repo},
        ListKeysHandler: {'api_key_repo': api_key_repo},
        CreateApiKeyHandler: {'api_key_repo': api_key_repo, 'mqtt_publish': publish},
        DeleteApiKeyHandler: {'api_key_repo': api_key_repo},
    }

    def factory(handler_class, is_behavior=False):
        kwargs = deps.get(handler_class, {})
        return handler_class(**kwargs)

    return factory


class Container(containers.DeclarativeContainer):
    """Application-level DI container."""

    wiring_config = containers.WiringConfiguration(
        modules=[
            'infrastructure.api.resources',
            'infrastructure.api.auth',
        ],
    )

    # ── Repositories (singletons) ──────────────────────────────────
    alert_repo = providers.Singleton(AlertRepository)
    stats_repo = providers.Singleton(StatsRepository)
    user_repo = providers.Singleton(UserRepository)
    api_key_repo = providers.Singleton(APIKeyRepository)

    # ── CEP MQTT client ────────────────────────────────────────────
    cep_mqtt = providers.Singleton(
        CepMQTTClient,
        alert_repo=alert_repo,
        broker=settings.MQTT_BROKER,
        port=settings.MQTT_PORT,
        username=settings.MQTT_USERNAME,
        password=settings.MQTT_PASSWORD,
    )

    # ── Handler factory (produces Mediator handler_class_manager) ──
    handler_factory = providers.Callable(
        _make_handler_factory,
        cep_mqtt=cep_mqtt,
        stats_repo=stats_repo,
        alert_repo=alert_repo,
        api_key_repo=api_key_repo,
    )

    # ── Mediator (domain event bus) ─────────────────────────────────
    mediator = providers.Singleton(
        Mediator,
        handler_class_manager=handler_factory,
    )

    # ── Sensor MQTT client ─────────────────────────────────────────
    sensor_mqtt = providers.Singleton(
        SensorMQTTClient,
        stats_repo=stats_repo,
        mediator=mediator,
        broker=settings.MQTT_BROKER,
        port=settings.MQTT_PORT,
        topics=settings.MQTT_TOPICS,
        username=settings.MQTT_USERNAME,
        password=settings.MQTT_PASSWORD,
    )
