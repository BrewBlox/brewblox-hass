"""
Subscribes to all Spark sensors, and publishes them to the HASS broker
"""


import re
from os import getenv
from typing import Set

import aiomqtt
from aiohttp import web
from brewblox_service import brewblox_logger, features, mqtt

LOGGER = brewblox_logger(__name__)

REPLACE_PATTERN = r'[^a-zA-Z0-9_-]'
SENSOR_TYPES = [
    'TempSensorOneWire',
    'TempSensorCombi',
    'TempSensorMock',
]
SETPOINT_TYPES = [
    'SetpointSensorPair',
]
HANDLED_TYPES = [
    *SENSOR_TYPES,
    *SETPOINT_TYPES,
]
UNITS = {
    'degC': '°C',
    'degF': '°F',
}


class Relay(features.ServiceFeature):

    def __init__(self, app: web.Application, publisher: mqtt.EventHandler):
        super().__init__(app)
        self.publisher: mqtt.EventHandler = publisher
        self.known: Set[str] = set()

    async def startup(self, app: web.Application):
        await mqtt.listen(app, 'brewcast/state/#', self.on_message)
        await mqtt.subscribe(app, 'brewcast/state/#')

    async def shutdown(self, app: web.Application):
        await mqtt.unsubscribe(app, 'brewcast/state/#')
        await mqtt.unlisten(app, 'brewcast/state/#', self.on_message)

    async def on_message(self, topic: str, message: dict):
        if message['type'] != 'Spark.state':
            return

        service = message['key']
        blocks = message['data']['blocks']
        LOGGER.info(f'Received {len(blocks)} blocks from {service}')

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

                published_state[sanitized] = value

                if full not in self.known:
                    LOGGER.info(f'publishing new sensor: {id}')
                    await self.publisher.publish(
                        topic=f'homeassistant/sensor/{full}/config',
                        message={
                            'device_class': 'temperature',
                            'name': f'{id} ({service})',
                            'state_topic': state_topic,
                            'unit_of_measurement': unit,
                            'value_template': '{{ value_json.' + sanitized + ' }}',
                        },
                        retain=True,
                    )
                    self.known.add(full)

            if block['type'] in SETPOINT_TYPES:
                qty = block['data']['setting']
                unit = UNITS.get(qty['unit'], qty['unit'])
                value = qty['value']

                published_state[sanitized] = value

                if full not in self.known:
                    LOGGER.info(f'publishing new setpoint: {id}')
                    await self.publisher.publish(
                        topic=f'homeassistant/sensor/{full}/config',
                        message={
                            'device_class': 'temperature',
                            'name': f'{id} ({service})',
                            'state_topic': state_topic,
                            'unit_of_measurement': unit,
                            'value_template': '{{ value_json.' + sanitized + ' }}',
                        },
                        retain=True,
                    )
                    self.known.add(full)

        LOGGER.info(f'Publishing {len(published_state)} blocks from {service}')
        if published_state:
            await self.publisher.publish(
                topic=state_topic,
                message=published_state,
                err=False,
            )


class PasswordEventHandler(mqtt.EventHandler):

    @staticmethod
    def create_client(config: mqtt.MQTTConfig) -> aiomqtt.Client:
        client = mqtt.EventHandler.create_client(config)
        client.username_pw_set(username=getenv('HASS_MQTT_USERNAME'),
                               password=getenv('HASS_MQTT_PASSWORD'))

        return client


def setup(app: web.Application):
    config = app['config']
    hass_mqtt = {
        'protocol': config['hass_mqtt_protocol'],
        'host': config['hass_mqtt_host'],
        'port': config['hass_mqtt_port'],
        'path': config['hass_mqtt_path'],
    }

    publisher = PasswordEventHandler(app, **hass_mqtt)
    features.add(app, publisher)
    features.add(app, Relay(app, publisher))
