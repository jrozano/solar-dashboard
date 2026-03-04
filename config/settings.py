import os

from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(_env_path)

MQTT_BROKER: str = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT: int = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME: str = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD: str = os.getenv('MQTT_PASSWORD', '')

MQTT_TOPICS: list[str] = [
    'ssd-solar/sensor/energia_importada_de_red_battery/state',
    'ssd-solar/sensor/energia_importada_de_red_battery_power/state',
    'ssd-solar/sensor/energia_importada_de_red_grid_power/state',
    'ssd-solar/sensor/energia_importada_de_red_load_power/state',
    'ssd-solar/sensor/energia_importada_de_red_pv_power/state',
]

# MQTT topics for Siddhi CEP integration
MQTT_TOPIC_SENSOR_EVENT: str = 'ssd-solar/events/sensor'
MQTT_TOPIC_API_KEY_EVENT: str = 'ssd-solar/events/api_key'
MQTT_TOPIC_CEP_ALERTS: str = 'ssd-solar/cep/alerts'

SECRET_KEY: str = os.getenv('SECRET_KEY', 'change-me')
LOGLEVEL: str = os.getenv('LOGLEVEL', 'INFO')

# Comma-separated list of allowed CORS origins (e.g. http://localhost:5000)
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000,https://oberon.iguana-dragon.ts.net').split(',')
    if o.strip()
]

GOOGLE_CLIENT_ID: str = os.getenv('GOOGLE_CLIENT_ID', 'change-me')
GOOGLE_CLIENT_SECRET: str = os.getenv('GOOGLE_CLIENT_SECRET', 'change-me')
