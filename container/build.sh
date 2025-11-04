#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 可配置参数（通过环境变量覆盖）
IMAGE=${IMAGE:-agentflow-shrimp:1.0.1}
PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE:-docker.io/library/python:3.11.4-slim-bullseye}
PYPI_REPOSITORY=${PYPI_REPOSITORY:-https://pypi.tuna.tsinghua.edu.cn/simple}
PYPI_TIMEOUT=${PYPI_TIMEOUT:-15}
BUILD_ENGINE=${BUILD_ENGINE:-podman}
MONGO_URI=${MONGO_URI:-mongodb://host.containers.internal:27017}
DATABASE_NAME=${DATABASE_NAME:-shrimp_db}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-4444}
DEBUG=${DEBUG:-false}

# 检查构建引擎
if [ "$BUILD_ENGINE" = "podman" ]; then
    BUILDER="buildah --tls-verify=false bud --format docker"
elif [ "$BUILD_ENGINE" = "docker" ]; then
    BUILDER="docker build"
else
    echo "错误: 不支持的构建引擎 '$BUILD_ENGINE'，请使用 'podman' 或 'docker'"
    exit 1
fi

echo "使用构建引擎: $BUILD_ENGINE"
echo "构建镜像: $IMAGE"
echo "Python基础镜像: $PYTHON_BASE_IMAGE"

# 构建镜像
$BUILDER \
  --build-arg PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE} \
  --build-arg PYPI_REPOSITORY=${PYPI_REPOSITORY} \
  --build-arg PYPI_TIMEOUT=${PYPI_TIMEOUT} \
  -f ${SCRIPT_DIR}/Dockerfile \
  -t $IMAGE $SCRIPT_DIR/..

echo "镜像构建完成: $IMAGE"
