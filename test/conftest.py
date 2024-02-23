"""
Master file for pytest fixtures.
Any fixtures declared here are available to all test functions in this directory.
"""


import logging
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from pytest_docker.plugin import Services as DockerServices

from brewblox_hass import app_factory, utils
from brewblox_hass.models import HassMqttCredentials, ServiceConfig

LOGGER = logging.getLogger(__name__)


class TestConfig(ServiceConfig):
    """
    An override for ServiceConfig that only uses
    settings provided to __init__()

    This makes tests independent from env values
    and the content of .appenv
    """

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


class TestCredentials(HassMqttCredentials):
    """
    An override for HassMqttCredentials that only uses
    settings provided to __init__()

    This makes tests independent from env values
    and the content of .appenv
    """

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


@pytest.fixture(autouse=True)
def config(monkeypatch: pytest.MonkeyPatch,
           docker_services: DockerServices,
           ) -> Generator[ServiceConfig, None, None]:
    cfg = TestConfig(
        debug=True,
        mqtt_host='localhost',
        mqtt_port=docker_services.port_for('eventbus', 1883),
        hass_mqtt_host='localhost',
        hass_mqtt_port=docker_services.port_for('hass_eventbus', 1883),
    )
    monkeypatch.setattr(utils, 'get_config', lambda: cfg)
    yield cfg


@pytest.fixture(autouse=True)
def credentials(monkeypatch: pytest.MonkeyPatch,
                ) -> Generator[HassMqttCredentials, None, None]:
    credentials = HassMqttCredentials(
        mqtt_username=None,
        mqtt_password=None,
    )
    monkeypatch.setattr(utils, 'get_hass_credentials', lambda: credentials)
    yield credentials


@pytest.fixture(scope='session')
def docker_compose_file():
    return Path('./test/docker-compose.yml').resolve()


@pytest.fixture(autouse=True)
def setup_logging(config):
    app_factory.setup_logging(True)


@pytest.fixture
def app() -> FastAPI:
    """
    Override this in test modules to bootstrap required dependencies.

    IMPORTANT: This must NOT be an async fixture.
    Contextvars assigned in async fixtures are invisible to test functions.
    """
    app = FastAPI()
    return app


@pytest.fixture
async def manager(app: FastAPI) -> AsyncGenerator[LifespanManager, None]:
    """
    AsyncClient does not automatically send ASGI lifespan events to the app
    https://asgi.readthedocs.io/en/latest/specs/lifespan.html

    For testing, this ensures that lifespan() functions are handled.
    If you don't need to make HTTP requests, you can use the manager
    without the `client` fixture.
    """
    async with LifespanManager(app) as mgr:
        yield mgr


@pytest.fixture
async def client(app: FastAPI, manager: LifespanManager) -> AsyncGenerator[AsyncClient, None]:
    """
    The default test client for making REST API calls.
    Using this fixture will also guarantee that lifespan startup has happened.
    """
    # AsyncClient does not automatically send ASGI lifespan events to the app
    # https://asgi.readthedocs.io/en/latest/specs/lifespan.html
    async with AsyncClient(app=app,
                           base_url='http://test') as ac:
        yield ac
