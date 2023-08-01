"""
Master file for pytest fixtures.
Any fixtures declared here are available to all test functions in this directory.
"""


import logging

import pytest
from aiohttp import test_utils
from brewblox_service import brewblox_logger, features, service

from brewblox_hass.models import ServiceConfig

LOGGER = brewblox_logger(__name__)


@pytest.fixture(scope='session', autouse=True)
def log_enabled():
    """Sets log level to DEBUG for all test functions.
    Allows all logged messages to be captured during pytest runs"""
    logging.getLogger().setLevel(logging.DEBUG)
    logging.captureWarnings(True)


@pytest.fixture
def app_config() -> ServiceConfig:
    return ServiceConfig(
        # From brewblox_service
        name='test_app',
        host='localhost',
        port=1234,
        debug=True,
        mqtt_protocol='mqtt',
        mqtt_host='eventbus',
        mqtt_port=1883,
        mqtt_path='/eventbus',
        history_topic='brewcast/history',
        state_topic='brewcast/state',

        # From brewblox_hass
        hass_mqtt_protocol='mqtt',
        hass_mqtt_host='eventbus',
        hass_mqtt_port=None,
        hass_mqtt_path='/eventbus',
    )


@pytest.fixture
def sys_args(app_config: ServiceConfig) -> list:
    return [str(v) for v in [
        'app_name',
        '--hass-mqtt-protocol', app_config.hass_mqtt_protocol,
        '--hass-mqtt-host', app_config.hass_mqtt_host,
        '--hass-mqtt-path', app_config.hass_mqtt_path,
        '--debug',
    ]]


@pytest.fixture
def app(app_config):
    app = service.create_app(app_config)
    return app


@pytest.fixture
async def setup(app):
    pass


@pytest.fixture
async def client(app, setup, aiohttp_client, aiohttp_server):
    """Allows patching the app or aiohttp_client before yielding it.

    Any tests wishing to add custom behavior to app can override the fixture
    """
    LOGGER.debug('Available features:')
    for name, impl in app.get(features.FEATURES_KEY, {}).items():
        LOGGER.debug(f'Feature "{name}" = {impl}')
    LOGGER.debug(app.on_startup)

    test_server: test_utils.TestServer = await aiohttp_server(app)
    test_client: test_utils.TestClient = await aiohttp_client(test_server)
    return test_client
