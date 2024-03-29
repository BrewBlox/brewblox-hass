# Relay between Brewblox and Home Assistant

This is a Proof of Concept implementation for sharing data between Brewblox and Home Assistant (HA).
It will automatically publish all sensor and setpoint values to HA.

Be aware that at time of writing, there is no ETA for further HA integration.
We like the concept (and tooling) of sharing Brewblox block data to HA.
There also are multiple other projects on the backlog that are more important.
We'll probably get around to extending this service, but it will take some time.

## Getting started

First, enable MQTT discovery in HA: <https://www.home-assistant.io/integrations/mqtt>.

Then, add the brewblox-hass service to your docker-compose.yml file:

```yml
version: '3.7'
services:
  # <= Other services in your config go here
  hass:
    image: ghcr.io/brewblox/brewblox-hass:${BREWBLOX_RELEASE}
    restart: unless-stopped
    environment:
      - BREWBLOX_HASS_HASS_MQTT_HOST={ADDRESS}
```

Replace `{ADDRESS}` with the hostname or IP address of the machine where your HA mosquitto broker is running.

If your broker requires a username and password, add the following entries to your `brewblox/.env` file:

```env
HASS_MQTT_USERNAME=changeme
HASS_MQTT_PASSWORD=changeme
```

Then extend your `hass` service environment:

```yml
version: '3.7'
services:
  # <= Other services in your config go here
  hass:
    image: ghcr.io/brewblox/brewblox-hass:${BREWBLOX_RELEASE}
    restart: unless-stopped
    environment:
      - BREWBLOX_HASS_HASS_MQTT_HOST={HOSTNAME}
      - HASS_MQTT_USERNAME
      - HASS_MQTT_PASSWORD
```
