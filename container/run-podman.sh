#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 可配置参数（通过环境变量覆盖）
IMAGE=${IMAGE:-localhost/agentflow-shrimp:1.0.1}
CONTAINER_NAME=${CONTAINER_NAME:-agentflow-shrimp}

# 使用非特权端口
API_PORT=${API_PORT:-9444}  # 使用 9444
AGENT_PORT=${AGENT_PORT:-9084}  # 使用 9084

# 停止并删除已存在的容器（如果存在）
echo "停止并删除已存在的容器..."
podman stop $CONTAINER_NAME 2>/dev/null || true
podman rm $CONTAINER_NAME 2>/dev/null || true

# 启动新容器（使用非特权端口）
echo "使用 rootless podman 启动 agentflow 容器..."
podman run --rm -d \
  --name $CONTAINER_NAME \
  --hostname agentflow \
  -p $API_PORT:4444/tcp \
  -p $AGENT_PORT:8084/tcp \
  -v $SCRIPT_DIR/../workspace:/app/workspace:rw \
  -v $SCRIPT_DIR/../logs:/var/log:rw \
  -e PYTHONUNBUFFERED=1 \
  -e TZ=Asia/Shanghai \
  -e MONGO_URI=mongodb://host.containers.internal:27017/shrimp_db \
  -e DATABASE_NAME=shrimp_db \
  -e HOST=0.0.0.0 \
  -e PORT=4444 \
  -e DEBUG=false \
  --add-host=host.containers.internal:host-gateway \
  $IMAGE

echo "容器已启动！"
echo "容器名称: $CONTAINER_NAME"
echo "镜像: $IMAGE"
echo "访问地址:"
echo "  shrimp 服务: http://localhost:$API_PORT/api/health"
echo "  agentflow 服务: http://localhost:$AGENT_PORT/static/ws-test.html"
echo ""

# 等待服务启动并执行健康检查
echo "等待服务启动..."
sleep 5

echo "执行健康检查:"
echo -n "  检查 shrimp API 服务... "
if curl -s -f -m 10 "http://localhost:$API_PORT/api/health" > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 异常或未启动"
fi

echo -n "  检查 agentflow 服务... "
if curl -s -f -m 10 "http://localhost:$AGENT_PORT/static/ws-test.html" > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 异常或未启动"
fi

echo ""
echo "查看容器状态: podman ps"
echo "查看容器日志: podman logs $CONTAINER_NAME"
echo "进入容器: podman exec -it $CONTAINER_NAME bash"
echo "停止容器: podman stop $CONTAINER_NAME"