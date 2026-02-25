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

# ── Patches for HAOS compatibility ────────────────────────────────────
# 1. Make modelscope import optional (models pre-downloaded)
# 2. Add HTTP request logging middleware (diagnostics)
# 3. Add OTA routes without trailing slash (ESP32 device compatibility)
# 4. Add Whisper + Parakeet V3 (NeMo Transducer) ASR support
COPY patch_server.py /tmp/patch_server.py
RUN python3 /tmp/patch_server.py && rm /tmp/patch_server.py

# ── ASR model: Parakeet V3 (25 European langs incl. French, ~640 MB) ─
RUN mkdir -p models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8 \
    && curl -L -o models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/encoder.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/resolve/main/encoder.int8.onnx" \
    && curl -L -o models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/decoder.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/resolve/main/decoder.int8.onnx" \
    && curl -L -o models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/joiner.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/resolve/main/joiner.int8.onnx" \
    && curl -L -o models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/tokens.txt \
    "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/resolve/main/tokens.txt"

# ── ASR model: Whisper small (fallback, ~370 MB) ─────────────────────
RUN mkdir -p models/sherpa-onnx-whisper-small \
    && curl -L -o models/sherpa-onnx-whisper-small/small-encoder.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-whisper-small/resolve/main/small-encoder.int8.onnx" \
    && curl -L -o models/sherpa-onnx-whisper-small/small-decoder.int8.onnx \
    "https://huggingface.co/csukuangfj/sherpa-onnx-whisper-small/resolve/main/small-decoder.int8.onnx" \
    && curl -L -o models/sherpa-onnx-whisper-small/small-tokens.txt \
    "https://huggingface.co/csukuangfj/sherpa-onnx-whisper-small/resolve/main/small-tokens.txt"

# ── TTS model: Piper fr_FR-siwis-medium (~55 MB) ─────────────────────
COPY sherpa_tts.py core/providers/tts/sherpa_tts.py
RUN curl -L -o /tmp/tts-model.tar.bz2 \
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-fr_FR-siwis-medium.tar.bz2" \
    && tar xjf /tmp/tts-model.tar.bz2 -C models/ \
    && rm /tmp/tts-model.tar.bz2

# ── VAD model (SileroVAD, ~2 MB) ────────────────────────────────────
RUN mkdir -p models/snakers4_silero-vad/src/silero_vad/data \
    && curl -L -o models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx \
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"

# ── S6 overlay service files ────────────────────────────────────────
COPY rootfs /
