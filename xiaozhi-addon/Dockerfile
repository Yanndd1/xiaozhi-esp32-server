ARG BUILD_FROM
FROM ${BUILD_FROM}

# ── System dependencies ──────────────────────────────────────────────
# Auto-detects Alpine (apk) vs Debian (apt-get) base image.
# HAOS may use either depending on build.yaml resolution.
RUN if command -v apk >/dev/null 2>&1; then \
        echo "=== Alpine base detected ===" && \
        apk add --no-cache \
            python3 py3-pip python3-dev opus-dev ffmpeg curl jq \
            gcc g++ musl-dev linux-headers libffi-dev openssl-dev \
            gcompat libstdc++ libgomp unzip; \
    elif command -v apt-get >/dev/null 2>&1; then \
        echo "=== Debian base detected ===" && \
        apt-get update && apt-get install -y --no-install-recommends \
            python3 python3-pip python3-dev python3-venv \
            libopus-dev libopus0 ffmpeg curl jq gcc g++ unzip \
        && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /opt/xiaozhi-esp32-server

# ── Native packages: onnxruntime + sherpa_onnx ───────────────────────
# On Debian (glibc): pip install works directly.
# On Alpine (musl): download manylinux wheels + extract with gcompat.
RUN if pip3 install --no-cache-dir --break-system-packages \
        onnxruntime sherpa-onnx 2>/dev/null; then \
        echo "=== onnxruntime + sherpa_onnx installed via pip ==="; \
    else \
        echo "=== Falling back to manylinux wheel extraction ===" \
        && PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')") \
        && SITE_PKG=$(python3 -c "import site; print(site.getsitepackages()[0])") \
        && ARCH=$(uname -m) \
        && mkdir -p /tmp/wheels \
        && pip3 download onnxruntime --no-deps --only-binary :all: \
            --platform "manylinux_2_17_${ARCH}" \
            --python-version "${PYVER}" --abi "cp${PYVER}" \
            -d /tmp/wheels/ \
        && pip3 download sherpa-onnx --no-deps --only-binary :all: \
            --platform "manylinux_2_17_${ARCH}" \
            --python-version "${PYVER}" --abi "cp${PYVER}" \
            -d /tmp/wheels/ \
        && for whl in /tmp/wheels/*.whl; do unzip -o "$whl" -d "${SITE_PKG}"; done \
        && rm -rf /tmp/wheels; \
    fi
RUN python3 -c "import onnxruntime; print(f'onnxruntime {onnxruntime.__version__} OK')"
RUN python3 -c "import sherpa_onnx; print('sherpa_onnx OK')"

# ── Python dependencies ──────────────────────────────────────────────
COPY requirements-addon.txt /tmp/requirements-addon.txt
RUN pip3 install --no-cache-dir --break-system-packages \
    -r /tmp/requirements-addon.txt \
    && rm /tmp/requirements-addon.txt

# ── Server code ──────────────────────────────────────────────────────
RUN curl -L -o /tmp/repo.tar.gz \
    https://github.com/Yanndd1/xiaozhi-esp32-server/archive/refs/heads/master.tar.gz \
    && tar xzf /tmp/repo.tar.gz -C /tmp \
    && cp -r /tmp/xiaozhi-esp32-server-master/main/xiaozhi-server/* . \
    && rm -rf /tmp/repo.tar.gz /tmp/xiaozhi-esp32-server-master \
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
