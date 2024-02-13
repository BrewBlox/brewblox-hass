from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.appenv',
        env_prefix='brewblox_hass_',
        case_sensitive=False,
        json_schema_extra='ignore',
    )

    name: str = 'hass'
    debug: bool = False
    debugger: bool = False

    mqtt_protocol: Literal['mqtt', 'mqtts'] = 'mqtt'
    mqtt_host: str = 'eventbus'
    mqtt_port: int = 1883

    hass_mqtt_protocol: Literal['mqtt', 'mqtts'] = 'mqtt'
    hass_mqtt_host: str = 'eventbus'
    hass_mqtt_port: int = 1883

    state_topic: str = 'brewcast/state'


class HassMqttCredentials(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='hass_',
        case_sensitive=False,
        json_schema_extra='ignore',
    )

    mqtt_username: str | None = None
    mqtt_password: str | None = None
