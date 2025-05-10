#!/bin/bash


# Docker run
docker run -p 8083:8083 \
  --name transcription-server-container \
  -it \
  --env-file .env \
  -e PYTHONUNBUFFERED=1 \
  -v $(pwd)/src:/app \
  transcription-server-image