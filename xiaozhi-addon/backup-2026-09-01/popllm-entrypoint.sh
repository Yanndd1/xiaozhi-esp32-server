#!/usr/bin/env bash
# =============================================================================
# Entrypoint standalone PopLLM — génère data/.config.yaml depuis l'environnement
# puis lance le serveur. Reproduit à l'identique le YAML de l'add-on HAOS
# (svc-xiaozhi/run) ; seul change : LLM = Ollama local, HA via API externe.
# Aucun secret en dur : tout vient de variables d'environnement (.env).
# =============================================================================
set -euo pipefail

SERVER_DIR="/opt/xiaozhi-esp32-server"
CONFIG_FILE="${SERVER_DIR}/data/.config.yaml"

# ── Paramètres (défauts sûrs ; surchargés par .env / compose) ────────
LLM_BACKEND="${LLM_BACKEND:-popllm}"
POPLLM_URL="${POPLLM_URL:-http://127.0.0.1:11434}"
POPLLM_MODEL="${POPLLM_MODEL:-qwen-ha:latest}"
HA_BASE_URL="${HA_BASE_URL:-http://192.168.10.205:8123}"
HA_TOKEN="${HA_TOKEN:-}"
HA_DEVICES="${HA_DEVICES:-salon,exemple,light.exemple}"
ESP32_MAC="${ESP32_MAC:-3c:0f:02:de:a8:18}"
PUBLIC_IP="${PUBLIC_IP:-192.168.10.84}"
LANGUAGE="${LANGUAGE:-fr}"
ASR_BACKEND="${ASR_BACKEND:-parakeet}"
ASR_LANGUAGE="${ASR_LANGUAGE:-${LANGUAGE}}"
PROMPT="${PROMPT:-Tu es un assistant vocal domotique francais, concis et naturel. Tu peux consulter et controler la maison via Home Assistant.}"

# ── Garde-fous ───────────────────────────────────────────────────────
if [ -z "${HA_TOKEN}" ]; then
  echo "[FATAL] HA_TOKEN vide. Renseigne-le dans .env (token longue durée HA)." >&2
  exit 1
fi
if echo "${POPLLM_URL}" | grep -q "localhost"; then
  echo "[WARN] POPLLM_URL=localhost — en network_mode host c'est OK (Ollama sur PopLLM)." >&2
fi

# ── Bloc LLM selon backend ───────────────────────────────────────────
if [ "${LLM_BACKEND}" = "claude" ]; then
  LLM_MODULE="ClaudeLLM"
  LLM_BLOCK="  ClaudeLLM:
    type: Claude
    model_name: \"${MODEL_NAME:-claude-haiku-4-5-20251001}\"
    api_key: \"${ANTHROPIC_API_KEY:-}\"
    max_tokens: 4096
    temperature: 0.7"
else
  LLM_MODULE="PopLLM"
  LLM_BLOCK="  PopLLM:
    type: ollama
    model_name: \"${POPLLM_MODEL}\"
    base_url: \"${POPLLM_URL}\""
fi

AUTH_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# ── Bloc ASR selon backend (parakeet = multilangue auto / whisper = langue forcee) ─
if [ "${ASR_BACKEND}" = "whisper" ]; then
  ASR_BLOCK="  SherpaASR:
    type: sherpa_onnx_local
    model_dir: models/sherpa-onnx-whisper-small
    output_dir: tmp/
    model_type: whisper
    language: \"${ASR_LANGUAGE}\""
else
  ASR_BLOCK="  SherpaASR:
    type: sherpa_onnx_local
    model_dir: models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8
    output_dir: tmp/
    model_type: transducer"
fi

mkdir -p "${SERVER_DIR}/data" "${SERVER_DIR}/tmp"

cat > "${CONFIG_FILE}" <<ENDOFCONFIG
# Auto-genere par popllm-entrypoint.sh (deploiement standalone PopLLM)
server:
  ip: 0.0.0.0
  port: 8000
  http_port: 8003
  websocket: "ws://${PUBLIC_IP}:8000/xiaozhi/v1/"
  vision_explain: "http://${PUBLIC_IP}:8003/mcp/vision/explain"
  timezone_offset: +1
  auth:
    enabled: true
    allowed_devices:
      - "${ESP32_MAC}"
  auth_key: "${AUTH_KEY}"
  mqtt_gateway: null
  mqtt_signature_key: null
  udp_gateway: null

selected_module:
  VAD: SileroVAD
  ASR: SherpaASR
  LLM: ${LLM_MODULE}
  TTS: LocalTTS
  Memory: nomem
  Intent: function_call

LLM:
${LLM_BLOCK}

TTS:
  LocalTTS:
    type: sherpa_tts
    model_dir: models/vits-piper-fr_FR-siwis-medium
    model_file: fr_FR-siwis-medium.onnx
    speed: 1.0
    speaker_id: 0
    output_dir: tmp/

ASR:
${ASR_BLOCK}

VAD:
  SileroVAD:
    type: silero
    threshold: 0.5
    threshold_low: 0.3
    model_dir: models/snakers4_silero-vad
    min_silence_duration_ms: 200

Intent:
  function_call:
    type: function_call
    functions:
      - change_role
      - hass_get_state
      - hass_set_state
      - hass_play_music
      - claude_decide

plugins:
  home_assistant:
    devices: "${HA_DEVICES}"
    base_url: "${HA_BASE_URL}"
    api_key: "${HA_TOKEN}"

prompt: |
  ${PROMPT}
ENDOFCONFIG

# Label ASR reel pour le log (reflete ASR_BACKEND)
if [ "${ASR_BACKEND}" = "whisper" ]; then
  ASR_LABEL="Whisper small (langue=${ASR_LANGUAGE} forcee)"
else
  ASR_LABEL="Parakeet V3 (multilangue auto)"
fi

echo "[OK] Config generee -> ${CONFIG_FILE}"
echo "[OK] LLM=${LLM_MODULE} (${POPLLM_MODEL} @ ${POPLLM_URL}) | HA=${HA_BASE_URL} | ASR=${ASR_LABEL} | TTS=Piper local"

cd "${SERVER_DIR}"
exec python3 app.py
