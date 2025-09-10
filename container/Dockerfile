ARG PYTHON_BASE_IMAGE=docker.io/library/python:3.11.4-slim-bullseye
FROM $PYTHON_BASE_IMAGE
ENV TZ=Asia/Shanghai
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

ARG PYPI_REPOSITORY=https://pypi.tuna.tsinghua.edu.cn/simple
# https://mirrors.aliyun.com/pypi/simple
ARG PYPI_TIMEOUT=15
ENV PIP_INDEX_URL=$PYPI_REPOSITORY

ARG SRC_PATH=./
COPY $SRC_PATH /app/

RUN pip install --no-cache-dir packaging \
    && pip install --no-cache-dir -r requirement.txt \
    && pip install --no-cache-dir -e .

RUN cd /app/studio \
    && pip install --no-cache-dir -r requirements.txt

COPY --chmod=755 container/entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
