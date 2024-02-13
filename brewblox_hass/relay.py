"""
Subscribes to all Spark sensors, and publishes them to the HASS broker
"""


import asyncio
import json
import logging
import re
from contextvars import ContextVar

from . import mqtt, utils

REPLACE_PATTERN = r'[^a-zA-Z0-9_]'
SENSOR_TYPES = [
    'TempSensorOneWire',
    'TempSensorCombi',
    'TempSensorMock',
    'TempSensorExternal',
]
SETPOINT_TYPES = [
    'SetpointSensorPair',
]
PROFILE_TYPES = [
    'SetpointProfile',
]
HANDLED_TYPES = [
    *SENSOR_TYPES,
    *SETPOINT_TYPES,
    *PROFILE_TYPES,
]
UNITS = {
    'degC': '°C',
    'degF': '°F',
    'degP': '°P',
}


LOGGER = logging.getLogger(__name__)
CV_KNOWN: ContextVar[set[str]] = ContextVar('relay.known')


def fallback(data: dict, k1: str, k2: str):
    return data.get(k1, data.get(k2))


def binary_sensor_state(value: bool):
    return 'ON' if value else 'OFF'


async def handle_spark_state(message: dict):
    known = CV_KNOWN.get()
    publisher = mqtt.CV_HASS.get()
    service = message['key']
    blocks = message['data']['blocks']

    state_topic = f'homeassistant/brewblox/{service}/state'
    published_state = {}

    for block in blocks:
        if block['type'] not in HANDLED_TYPES:
            continue

        id: str = block['id']
        sanitized = re.sub(REPLACE_PATTERN, '', id)
        full = f'{service}__{sanitized}'

        if id.startswith('New|'):
            # Skip generated names
            continue

        if block['type'] in SENSOR_TYPES:
            qty = block['data']['value']
            unit = UNITS.get(qty['unit'], qty['unit'])
            value = qty['value']

            if value is not None:
                value = round(value, 2)

            published_state[sanitized] = value

            if full not in known:
                LOGGER.info(f'publishing new sensor: {id}')
                publisher.publish(
                    f'homeassistant/sensor/{full}/config',
                    {
                        'device_class': 'temperature',
                        'name': f'{id} ({service})',
                        'state_topic': state_topic,
                        'unit_of_measurement': unit,
                        'value_template': '{{ value_json.' + sanitized + ' }}',
                    },
                    retain=True,
                )
                known.add(full)

        if block['type'] in SETPOINT_TYPES:
            qty = block['data']['setting']
            unit = UNITS.get(qty['unit'], qty['unit'])
            value = qty['value']

            if value is not None:
                value = round(value, 2)

            published_state[sanitized] = value

            if full not in known:
                LOGGER.info(f'publishing new setpoint: {id}')
                publisher.publish(
                    f'homeassistant/sensor/{full}/config',
                    {
                        'device_class': 'temperature',
                        'name': f'{id} ({service})',
                        'state_topic': state_topic,
                        'unit_of_measurement': unit,
                        'value_template': '{{ value_json.' + sanitized + ' }}',
                    },
                    retain=True,
                )
                known.add(full)

        if block['type'] in PROFILE_TYPES:
            qty = block['data']['setting']
            value = qty['value']

            published_state[sanitized] = binary_sensor_state(value is not None)

            if full not in known:
                LOGGER.info(f'publishing new profile state: {id}')
                publisher.publish(
                    f'homeassistant/binary_sensor/{full}/config',
                    {
                        'device_class': 'running',
                        'name': f'{id} ({service})',
                        'state_topic': state_topic,
                        'value_template': '{{ value_json.' + sanitized + ' }}',
                    },
                    retain=True,
                )
                known.add(full)

    if published_state:
        publisher.publish(state_topic, published_state)


async def handle_tilt_state(message: dict):
    known = CV_KNOWN.get()
    publisher = mqtt.CV_HASS.get()
    service = message['key']
    name = message['name']
    sanitized = re.sub(REPLACE_PATTERN, '_', name)
    full = f'{service}_{sanitized}'
    state_topic = f'homeassistant/brewblox/{full}/state'

    if full not in known:
        LOGGER.info(f'publishing new Tilt: {service} {name}')
        publisher.publish(
            f'homeassistant/sensor/{full}_temp_c/config',
            {
                'device_class': 'temperature',
                'name': f'{service} {name} temperature',
                'state_topic': state_topic,
                'unit_of_measurement': UNITS['degC'],
                'value_template': '{{ value_json.temp_c }}',
            },
            retain=True,
        )
        publisher.publish(
            f'homeassistant/sensor/{full}_sg/config',
            {
                'name': f'{service} {name} SG',
                'state_topic': state_topic,
                'value_template': '{{ value_json.sg }}',
            },
            retain=True,
        )
        publisher.publish(
            f'homeassistant/sensor/{full}_plato/config',
            {
                'name': f'{service} {name} Plato',
                'state_topic': state_topic,
                'unit_of_measurement': UNITS['degP'],
                'value_template': '{{ value_json.plato }}',
            },
            retain=True,
        )
        known.add(full)

    data = message['data']
    publisher.publish(
        state_topic,
        {
            'temp_c': data['temperature[degC]'],
            'sg': data['specificGravity'],
            'plato': data['plato[degP]'],
        },
    )


def setup():
    config = utils.get_config()
    mqtt_in = mqtt.CV_LOCAL.get()
    CV_KNOWN.set(set())

    @mqtt_in.subscribe(config.state_topic + '/#')
    async def on_state_message(client, topic, payload, qos, properties):
        message = json.loads(payload)

        if message['type'] == 'Spark.state':
            asyncio.create_task(handle_spark_state(message))
            return

        if message['type'] == 'Tilt.state':
            asyncio.create_task(handle_tilt_state(message))
            return
