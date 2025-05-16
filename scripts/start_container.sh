#!/bin/bash


# Docker run
docker run -p 8084:8084 \
  --name token-streaming-server-container \
  --network signaling-network \
  -it \
  --env-file .env \
  -e PYTHONUNBUFFERED=1 \
  -v $(pwd)/src:/app \
  token-streaming-server-image