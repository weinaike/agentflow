ARG PYTHON_BASE_IMAGE=docker.io/library/python:3.11.4-slim-bullseye
FROM $PYTHON_BASE_IMAGE
ENV TZ=Asia/Shanghai
ENV DEBIAN_FRONTEND=noninteractive
ARG PYPI_REPOSITORY=https://pypi.tuna.tsinghua.edu.cn/simple
# https://mirrors.aliyun.com/pypi/simple

WORKDIR /app

ARG REQUIREMENTS_TXT_PATH=requirement.txt
ARG STUDIO_REQUIREMENTS_TXT_PATH=studio/requirements.txt
ARG PYPI_TIMEOUT=15

COPY $REQUIREMENTS_TXT_PATH ./requirement.txt
COPY $STUDIO_REQUIREMENTS_TXT_PATH ./studio/requirements.txt
#COPY $REQUIREMENTS_TXT_PATH /tmp/requirements.txt
#COPY $STUDIO_REQUIREMENTS_TXT_PATH /tmp/studio/requirements.txt

RUN pip install --no-cache-dir -i $PYPI_REPOSITORY packaging

#WORKDIR /app
#RUN pip install --no-cache-dir -i $PYPI_REPOSITORY -r /tmp/requirements.txt

#WORKDIR /app/studio
#RUN pip install --no-cache-dir -i $PYPI_REPOSITORY -r /tmp/studio/requirements.txt
RUN pip install --no-cache-dir -i $PYPI_REPOSITORY -r requirement.txt \
    && pip install --no-cache-dir -i $PYPI_REPOSITORY -r studio/requirements.txt

ARG SRC_PATH=./
COPY $SRC_PATH /app/
COPY --chmod=755 container/entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
