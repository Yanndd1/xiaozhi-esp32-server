ARG BUILD_FROM=python:3.11-slim-bookworm
FROM ${BUILD_FROM}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopus-dev \
    libopus0 \
    ffmpeg \
    curl \
    jq \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/xiaozhi-esp32-server

# Copy and install Python dependencies (lightweight, no torch)
COPY requirements-addon.txt /tmp/requirements-addon.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements-addon.txt \
    && rm /tmp/requirements-addon.txt

# Download server code from the repository
RUN curl -L -o /tmp/repo.tar.gz \
    https://github.com/Yanndd1/xiaozhi-esp32-server/archive/refs/heads/master.tar.gz \
    && tar xzf /tmp/repo.tar.gz -C /tmp \
    && cp -r /tmp/xiaozhi-esp32-server-master/main/xiaozhi-server/* . \
    && rm -rf /tmp/repo.tar.gz /tmp/xiaozhi-esp32-server-master \
    && mkdir -p data tmp

# Download SherpaASR model (SenseVoice multilingual, ~80 MB)
RUN mkdir -p models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 \
    && curl -L -o models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/model.int8.onnx" \
    && curl -L -o models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/tokens.txt \
    "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt"

# Download SileroVAD ONNX model (~2 MB)
RUN mkdir -p models/snakers4_silero-vad/src/silero_vad/data \
    && curl -L -o models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx \
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT []
CMD ["/entrypoint.sh"]
