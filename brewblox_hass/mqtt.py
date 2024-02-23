from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar

from fastapi_mqtt.config import MQTTConfig
from fastapi_mqtt.fastmqtt import FastMQTT

from . import utils

CV_LOCAL: ContextVar[FastMQTT] = ContextVar('mqtt.client.local')
CV_HASS: ContextVar[FastMQTT] = ContextVar('mqtt.client.hass')


def setup():
    config = utils.get_config()
    hass_credentials = utils.get_hass_credentials()

    mqtt_config = MQTTConfig(host=config.mqtt_host,
                             port=config.mqtt_port,
                             ssl=(config.mqtt_protocol == 'mqtts'),
                             reconnect_retries=-1)
    fmqtt = FastMQTT(config=mqtt_config)
    CV_LOCAL.set(fmqtt)

    hass_mqtt_config = MQTTConfig(host=config.hass_mqtt_host,
                                  port=config.hass_mqtt_port,
                                  ssl=(config.hass_mqtt_protocol == 'mqtts'),
                                  username=hass_credentials.mqtt_username,
                                  password=hass_credentials.mqtt_password,
                                  reconnect_retries=-1)
    hass_fmqtt = FastMQTT(config=hass_mqtt_config)
    CV_HASS.set(hass_fmqtt)


@asynccontextmanager
async def mqtt_lifespan(fmqtt: FastMQTT):
    await fmqtt.connection()
    yield
    await fmqtt.client.disconnect()


@asynccontextmanager
async def lifespan():
    async with AsyncExitStack() as stack:
        # Order matters here: we want to be able to publish
        # before we start receiving messages
        await stack.enter_async_context(mqtt_lifespan(CV_HASS.get()))
        await stack.enter_async_context(mqtt_lifespan(CV_LOCAL.get()))
        yield
