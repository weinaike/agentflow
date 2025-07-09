#!/bin/bash
CODEBASE=/media/wnk/projects/x265
AUTOGEN_DIR=/home/wnk/code/agentflow
CONTAINER_NAME=agentflow

docker run -it --rm \
    --name $CONTAINER_NAME \
    -v $AUTOGEN_DIR:/root/agentflow \
    -v $CODEBASE:/root/project \
    -e RAG_MINIMUM_MESSAGE_LENGTH=5 \
    -e HASH_LENGTH=8 \
    -e CHROMADB_MAX_BATCH_SIZE=40000 \
    -e OPENAI_API_KEY=sk-E7gOgfTjf0tREnYXEa1767178b7f43499eBdA49389CdD905 \
    -e OPENAI_BASE_URL=https://api2.road2all.com/v1 \
    -e BING_API_KEY=d6d7d9b9edf74eeda368abf160cfae26 \
    -w /root/agentflow \
    -v /usr/local/cuda-12.1:/usr/local/cuda \
    --hostname flow \
    --gpus all \
    csst-agentflow:2.1.0 

    