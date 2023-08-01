"""
Subscribes to all Spark sensors, and publishes them to the HASS broker
"""


import json
import re
from os import getenv
from typing import Set

from aiohttp import web
from brewblox_service import brewblox_logger, features, mqtt

from brewblox_hass.models import ServiceConfig

LOGGER = brewblox_logger(__name__)

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


def fallback(data: dict, k1: str, k2: str):
    return data.get(k1, data.get(k2))


def binary_sensor_state(value: bool):
    return 'ON' if value else 'OFF'


class Relay(features.ServiceFeature):

    def __init__(self, app: web.Application, publisher: mqtt.EventHandler):
        super().__init__(app)
        config: ServiceConfig = app['config']
        self.topic = f'{config.state_topic}/#'
        self.publisher: mqtt.EventHandler = publisher
        self.known: Set[str] = set()

    async def startup(self, app: web.Application):
        await mqtt.listen(app, self.topic, self.on_message)
        await mqtt.subscribe(app, self.topic)

    async def shutdown(self, app: web.Application):
        await mqtt.unsubscribe(app, self.topic)
        await mqtt.unlisten(app, self.topic, self.on_message)

    async def handle_spark_state(self, message: dict):
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

                if full not in self.known:
                    LOGGER.info(f'publishing new sensor: {id}')
                    await self.publisher.publish(
                        topic=f'homeassistant/sensor/{full}/config',
                        message=json.dumps({
                            'device_class': 'temperature',
                            'name': f'{id} ({service})',
                            'state_topic': state_topic,
                            'unit_of_measurement': unit,
                            'value_template': '{{ value_json.' + sanitized + ' }}',
                        }),
                        retain=True,
                    )
                    self.known.add(full)

            if block['type'] in SETPOINT_TYPES:
                qty = block['data']['setting']
                unit = UNITS.get(qty['unit'], qty['unit'])
                value = qty['value']

                if value is not None:
                    value = round(value, 2)

                published_state[sanitized] = value

                if full not in self.known:
                    LOGGER.info(f'publishing new setpoint: {id}')
                    await self.publisher.publish(
                        topic=f'homeassistant/sensor/{full}/config',
                        message=json.dumps({
                            'device_class': 'temperature',
                            'name': f'{id} ({service})',
                            'state_topic': state_topic,
                            'unit_of_measurement': unit,
                            'value_template': '{{ value_json.' + sanitized + ' }}',
                        }),
                        retain=True,
                    )
                    self.known.add(full)

            if block['type'] in PROFILE_TYPES:
                qty = block['data']['setting']
                value = qty['value']

                published_state[sanitized] = binary_sensor_state(value is not None)

                if full not in self.known:
                    LOGGER.info(f'publishing new profile state: {id}')
                    await self.publisher.publish(
                        topic=f'homeassistant/binary_sensor/{full}/config',
                        payload=json.dumps({
                            'device_class': 'running',
                            'name': f'{id} ({service})',
                            'state_topic': state_topic,
                            'value_template': '{{ value_json.' + sanitized + ' }}',
                        }),
                        retain=True,
                    )
                    self.known.add(full)

        if published_state:
            await self.publisher.publish(
                topic=state_topic,
                message=json.dumps(published_state),
                err=False,
            )

    async def handle_tilt_state(self, message: dict):
        service = message['key']
        name = message['name']
        sanitized = re.sub(REPLACE_PATTERN, '_', name)
        full = f'{service}_{sanitized}'
        state_topic = f'homeassistant/brewblox/{full}/state'

        if full not in self.known:
            LOGGER.info(f'publishing new Tilt: {service} {name}')
            await self.publisher.publish(
                topic=f'homeassistant/sensor/{full}_temp_c/config',
                message=json.dumps({
                    'device_class': 'temperature',
                    'name': f'{service} {name} temperature',
                    'state_topic': state_topic,
                    'unit_of_measurement': UNITS['degC'],
                    'value_template': '{{ value_json.temp_c }}',
                }),
                retain=True,
            )
            await self.publisher.publish(
                topic=f'homeassistant/sensor/{full}_sg/config',
                message=json.dumps({
                    'name': f'{service} {name} SG',
                    'state_topic': state_topic,
                    'value_template': '{{ value_json.sg }}',
                }),
                retain=True,
            )
            await self.publisher.publish(
                topic=f'homeassistant/sensor/{full}_plato/config',
                message=json.dumps({
                    'name': f'{service} {name} Plato',
                    'state_topic': state_topic,
                    'unit_of_measurement': UNITS['degP'],
                    'value_template': '{{ value_json.plato }}',
                }),
                retain=True,
            )
            self.known.add(full)

        data = message['data']
        await self.publisher.publish(
            topic=state_topic,
            message=json.dumps({
                'temp_c': data['temperature[degC]'],
                'sg': data['specificGravity'],
                'plato': data['plato[degP]'],
            }),
            err=False,
        )

    async def on_message(self, topic: str, payload: str):
        message = json.loads(payload)

        if message['type'] == 'Spark.state':
            return await self.handle_spark_state(message)

        if message['type'] == 'Tilt.state':
            return await self.handle_tilt_state(message)


def setup(app: web.Application):
    config: ServiceConfig = app['config']

    publisher = mqtt.EventHandler(app,
                                  protocol=config.hass_mqtt_protocol,
                                  host=config.hass_mqtt_host,
                                  port=config.hass_mqtt_port,
                                  path=config.hass_mqtt_path)
    publisher.client._client.username_pw_set(username=getenv('HASS_MQTT_USERNAME'),
                                             password=getenv('HASS_MQTT_PASSWORD'))

    features.add(app, publisher)
    features.add(app, Relay(app, publisher))
