"""
Example of how to import and use the brewblox service
"""

from argparse import ArgumentParser

from brewblox_service import brewblox_logger, mqtt, scheduler, service

from brewblox_hass import relay
from brewblox_hass.models import ServiceConfig

LOGGER = brewblox_logger(__name__)


def create_parser() -> ArgumentParser:
    parser: ArgumentParser = service.create_parser('hass')

    group = parser.add_argument_group('HASS broker config')
    group.add_argument('--hass-mqtt-protocol',
                       help='Transport protocol used for HASS MQTT events. [%(default)s]',
                       choices=['mqtt', 'mqtts', 'ws', 'wss'],
                       default='mqtt')
    group.add_argument('--hass-mqtt-host',
                       help='Hostname at which the HASS broker can be reached [%(default)s]',
                       default='eventbus')
    group.add_argument('--hass-mqtt-port',
                       help='Port at which the HASS can be reached [%(default)s]',
                       type=int)
    group.add_argument('--hass-mqtt-path',
                       help='Path used for HASS MQTT events. Only applies if a ws protocol is used. [%(default)s]',
                       default='/eventbus')

    return parser


def main():
    parser = create_parser()
    config = service.create_config(parser, model=ServiceConfig)
    app = service.create_app(config)

    async def setup():
        scheduler.setup(app)
        mqtt.setup(app)
        relay.setup(app)

    service.run_app(app, setup())


if __name__ == '__main__':
    main()
