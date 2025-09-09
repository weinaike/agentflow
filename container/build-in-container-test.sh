#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
mkdir -p /tmp/build/containers
podman run --rm \
    -v /tmp/build/containers:/var/lib/containers \
    -v $SCRIPT_DIR/..:/code \
    --privileged \
    -e PYTHON_BASE_IMAGE=m.lab.zverse.space/docker.io/library/python:3.11.4-slim-bullseye \
    -e PYPI_REPOSITORY=https://pypi.tuna.tsinghua.edu.cn/simple \
    -e PYPI_TIMEOUT=1800 \
    -e IMAGE=agentflow:latest \
    -it m.lab.zverse.space/quay.io/containers/buildah:v1.35.4 \
    bash /code/container/build.sh
