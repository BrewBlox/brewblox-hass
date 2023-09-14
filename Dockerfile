FROM python:3.11-bookworm as base

COPY ./dist /app/dist

ENV PIP_EXTRA_INDEX_URL=https://www.piwheels.org/simple
ENV PIP_FIND_LINKS=/wheeley

RUN <<EOF
    set -ex

    mkdir /wheeley
    pip3 install --upgrade pip wheel setuptools
    pip3 wheel --wheel-dir=/wheeley -r /app/dist/requirements.txt
    pip3 wheel --wheel-dir=/wheeley /app/dist/*.tar.gz
EOF

FROM python:3.11-slim-bookworm
EXPOSE 5000
WORKDIR /app

COPY --from=base /wheeley /wheeley

RUN <<EOF
    set -ex

    pip3 install --no-index --find-links=/wheeley brewblox-hass
    pip3 freeze
    rm -rf /wheeley
EOF

ENTRYPOINT ["python3", "-m", "brewblox_hass"]
