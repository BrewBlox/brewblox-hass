from functools import lru_cache

from .models import HassMqttCredentials, ServiceConfig


@lru_cache
def get_config() -> ServiceConfig:  # pragma: no cover
    return ServiceConfig()


@lru_cache
def get_hass_credentials() -> HassMqttCredentials:
    return HassMqttCredentials()
