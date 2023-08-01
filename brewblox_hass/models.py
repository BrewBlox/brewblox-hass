from typing import Optional

from brewblox_service.models import BaseServiceConfig, MqttProtocol


class ServiceConfig(BaseServiceConfig):
    hass_mqtt_protocol: MqttProtocol
    hass_mqtt_host: str
    hass_mqtt_port: Optional[int]
    hass_mqtt_path: str
