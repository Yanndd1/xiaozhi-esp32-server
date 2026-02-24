ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
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
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements-addon.txt \
    && rm /tmp/requirements-addon.txt

# Download server code from the repository
RUN curl -L https://github.com/Yanndd1/xiaozhi-esp32-server/archive/refs/heads/master.tar.gz \
    | tar xz --strip-components=2 --wildcards '*/main/xiaozhi-server/*' \
    && mkdir -p data tmp

# Download SherpaASR model (SenseVoice multilingual, ~80 MB)
RUN mkdir -p models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 && \
    curl -L -o models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/model.int8.onnx" && \
    curl -L -o models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/tokens.txt \
    "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt"

# Download SileroVAD ONNX model (~2 MB)
RUN mkdir -p models/snakers4_silero-vad/src/silero_vad/data && \
    curl -L -o models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx \
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT []
CMD ["/entrypoint.sh"]
