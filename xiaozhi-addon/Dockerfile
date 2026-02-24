ARG BUILD_FROM
FROM ${BUILD_FROM}

# ── System dependencies (Debian bookworm) ─────────────────────────────
# Note: Debian base is required for onnxruntime/sherpa_onnx (glibc).
# Alpine (musl) is NOT supported — manylinux wheels are incompatible.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev python3-venv \
        libopus-dev libopus0 ffmpeg curl jq gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/xiaozhi-esp32-server

# ── Native packages: onnxruntime + sherpa_onnx ───────────────────────
RUN pip3 install --no-cache-dir --break-system-packages \
        onnxruntime sherpa-onnx
RUN python3 -c "import onnxruntime; print(f'onnxruntime {onnxruntime.__version__} OK')"
RUN python3 -c "import sherpa_onnx; print('sherpa_onnx OK')"

# ── Python dependencies ──────────────────────────────────────────────
COPY requirements-addon.txt /tmp/requirements-addon.txt
RUN pip3 install --no-cache-dir --break-system-packages \
    -r /tmp/requirements-addon.txt \
    && rm /tmp/requirements-addon.txt

# ── Server code ──────────────────────────────────────────────────────
RUN curl -L -o /tmp/repo.tar.gz \
    https://github.com/Yanndd1/xiaozhi-esp32-server/archive/refs/heads/main.tar.gz \
    && tar xzf /tmp/repo.tar.gz -C /tmp \
    && cp -r /tmp/xiaozhi-esp32-server-main/main/xiaozhi-server/* . \
    && rm -rf /tmp/repo.tar.gz /tmp/xiaozhi-esp32-server-main \
    && mkdir -p data tmp

# ── ASR model (SenseVoice multilingual, ~80 MB) ─────────────────────
RUN mkdir -p models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 \
    && curl -L -o models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/model.int8.onnx" \
    && curl -L -o models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/tokens.txt \
    "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt"

# ── VAD model (SileroVAD, ~2 MB) ────────────────────────────────────
RUN mkdir -p models/snakers4_silero-vad/src/silero_vad/data \
    && curl -L -o models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx \
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"

# ── S6 overlay service files ────────────────────────────────────────
COPY rootfs /
