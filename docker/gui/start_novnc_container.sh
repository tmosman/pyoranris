#!/usr/bin/env bash
# Start the noVNC container. Access UI at http://localhost:6080
docker compose -f docker/gui/docker-compose.novnc.yml up --build
