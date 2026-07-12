#!/usr/bin/env bash
# Helper to run the X11 container with appropriate xhost permissions on Linux hosts.
if [ -z "$DISPLAY" ]; then
  echo "DISPLAY not set. Are you on a GUI host?"
  exit 1
fi
echo "Allowing local docker to connect to X server (xhost +local:docker). Revoke when finished with xhost -local:docker."
xhost +local:docker
docker compose -f docker/gui/docker-compose.x11.yml up --build
# when stopping remember to run:
# xhost -local:docker
