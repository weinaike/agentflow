#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 可配置参数（通过环境变量覆盖）
IMAGE=${IMAGE:-agentflow:1.0.0}
PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE:-docker.io/library/python:3.11.4-slim-bullseye}
PYPI_REPOSITORY=${PYPI_REPOSITORY:-https://pypi.tuna.tsinghua.edu.cn/simple}
PYPI_TIMEOUT=${PYPI_TIMEOUT:-15}

# 构建镜像
buildah --tls-verify=false build \
  --build-arg PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE} \
  --build-arg PYPI_REPOSITORY=${PYPI_REPOSITORY} \
  --build-arg PYPI_TIMEOUT=${PYPI_TIMEOUT} \
  -f ${SCRIPT_DIR}/Dockerfile \
  -t $IMAGE $SCRIPT_DIR/..
