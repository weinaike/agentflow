ARG PYTHON_BASE_IMAGE=docker.io/library/python:3.11.4-slim-bullseye
FROM $PYTHON_BASE_IMAGE
ENV TZ=Asia/Shanghai
ENV DEBIAN_FRONTEND=noninteractive

# Configure China mirror for apt
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# Install system dependencies for both services
RUN apt-get update && apt-get install -y \
    supervisor \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

ARG PYPI_REPOSITORY=https://pypi.tuna.tsinghua.edu.cn/simple
# https://mirrors.aliyun.com/pypi/simple
ARG PYPI_TIMEOUT=15
ENV PIP_INDEX_URL=$PYPI_REPOSITORY

ARG SRC_PATH=./
COPY $SRC_PATH /app/

# Clone shrimp-backend repository
RUN git clone https://gitlab.zhejianglab.com/weinaike/shrimp-backend.git /app/shrimp
# Install Shrimp Python dependencies
RUN if [ -d "/app/shrimp" ]; then \
        cd /app/shrimp && pip install --no-cache-dir -e .; \
    else \
        echo "Warning: /app/shrimp directory not found, skipping shrimp installation"; \
    fi

# Install AgentFlow Python dependencies
RUN pip install --no-cache-dir packaging || (echo "Failed to install packaging" && exit 1)

RUN if [ -f "/app/setup.py" ] || [ -f "/app/pyproject.toml" ]; then \
        pip install --no-cache-dir -e . || (echo "Failed to install AgentFlow package" && exit 1); \
    else \
        echo "Warning: No package setup files found, skipping AgentFlow installation"; \
    fi
# Install Studio Python dependencies
RUN cd /app/studio \
    && if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then \
        pip install --no-cache-dir -e . || (echo "Failed to install studio package" && exit 1); \
    else \
        echo "Warning: No studio package setup files found, skipping"; \
    fi

# Copy configuration files
COPY container/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 4444 8084

# Start supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
