"""
Tests message relay
"""

import asyncio
import json
from contextlib import AsyncExitStack, asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from brewblox_hass import mqtt, relay, utils


class MqttListener:
    def __init__(self) -> None:
        self.sensors = []
        self.state = []
        self.done = asyncio.Event()

    def setup(self):
        mqtt_hass = mqtt.CV_HASS.get()

        @mqtt_hass.subscribe('homeassistant/sensor/#')
        async def on_hass_sensor(client, topic, payload, qos, properties):
            self.sensors.append(json.loads(payload))

        @mqtt_hass.subscribe('homeassistant/brewblox/#')
        async def on_hass_state(client, topic, payload, qos, properties):
            self.state.append(json.loads(payload))
            self.done.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mqtt.lifespan())
        yield


@pytest.fixture
def m_pub_listener() -> MqttListener:
    return MqttListener()


@pytest.fixture
def app(m_pub_listener: MqttListener) -> FastAPI:
    mqtt.setup()
    relay.setup()
    m_pub_listener.setup()
    app = FastAPI(lifespan=lifespan)
    return app


async def test_state_events(client: AsyncClient, m_pub_listener: MqttListener):
    config = utils.get_config()
    mqtt_local = mqtt.CV_LOCAL.get()

    with open('test/state_event_spark.json') as f:
        spark_evt = json.load(f)
        spark_key = spark_evt['key']

    mqtt_local.publish(f'{config.state_topic}/{spark_key}', spark_evt)

    await asyncio.wait_for(m_pub_listener.done.wait(), timeout=5)
    assert m_pub_listener.sensors == [
        {
            'device_class': 'temperature',
            'name': 'Sensor 1 (spark-four)',
            'state_topic': 'homeassistant/brewblox/spark-four/state',
            'unit_of_measurement': '°C',
            'value_template': '{{ value_json.Sensor1 }}'
        },
        {
            'device_class': 'temperature',
            'name': 'Sensor 2 (spark-four)',
            'state_topic': 'homeassistant/brewblox/spark-four/state',
            'unit_of_measurement': '°C',
            'value_template': '{{ value_json.Sensor2 }}'
        },
        {
            'device_class': 'temperature',
            'name': 'Sensor 3 (spark-four)',
            'state_topic': 'homeassistant/brewblox/spark-four/state',
            'unit_of_measurement': '°C',
            'value_template': '{{ value_json.Sensor3 }}'
        }
    ]
    assert m_pub_listener.state == [{
        'Sensor1': pytest.approx(20.88),
        'Sensor2': None,
        'Sensor3': None,
    }]

    m_pub_listener.sensors.clear()
    m_pub_listener.state.clear()
    m_pub_listener.done.clear()

    with open('test/state_event_tilt.json') as f:
        tilt_evt = json.load(f)
        tilt_key = tilt_evt['key']

    mqtt_local.publish(f'{config.state_topic}/{tilt_key}', tilt_evt)

    await asyncio.wait_for(m_pub_listener.done.wait(), timeout=5)
    assert m_pub_listener.sensors == [
        {
            'device_class': 'temperature',
            'name': 'tilt Purple temperature',
            'state_topic': 'homeassistant/brewblox/tilt_Purple/state',
            'unit_of_measurement': '°C',
            'value_template': '{{ value_json.temp_c }}'
        },
        {
            'name': 'tilt Purple SG',
            'state_topic': 'homeassistant/brewblox/tilt_Purple/state',
            'value_template': '{{ value_json.sg }}'
        },
        {
            'name': 'tilt Purple Plato',
            'state_topic': 'homeassistant/brewblox/tilt_Purple/state',
            'unit_of_measurement': '°P',
            'value_template': '{{ value_json.plato }}'
        }
    ]
    assert m_pub_listener.state == [{
        'temp_c': pytest.approx(20),
        'sg': pytest.approx(0.997),
        'plato': pytest.approx(-0.781),
    }]
