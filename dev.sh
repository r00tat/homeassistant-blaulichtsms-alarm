#!/bin/bash
# setup dev environment
set -eo pipefail

if [[ -z "$(which uv)" ]]; then
  echo "uv required!"
  echo "see https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  uv venv
  uv pip install -r requirements.txt
fi

mkdir -p config

rsync -avz custom_components/blaulichtsms_alarm/ config/custom_components/blaulichtsms_alarm/

if [ ! "$(docker ps -a -q -f name=homeassistant)" ]; then
  docker run -d \
    --name homeassistant \
    --privileged \
    --restart=unless-stopped \
    -e TZ=Europe/Vienna \
    -v $PWD/config:/config \
    -v /run/dbus:/run/dbus:ro \
    -p 8123:8123 \
    ghcr.io/home-assistant/home-assistant:stable
else
  docker restart homeassistant
fi
docker logs -n 10 -f homeassistant
