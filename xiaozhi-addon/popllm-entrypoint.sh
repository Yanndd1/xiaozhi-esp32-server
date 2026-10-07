#!/usr/bin/env bash
# =============================================================================
# Entrypoint standalone PopLLM : génère data/.config.yaml depuis l'environnement
# puis lance le serveur. Aucun secret en dur : tout vient de variables
# d'environnement (.env).
#
# Révision 2026-09-01 : correctifs latence / verbosité / prononciation.
# Mesures ayant motivé ces changements (modèle qwen-ha:latest, endpoint /v1
# d'Ollama sur PopLLM, 6 essais par réglage) :
#   conversation, réglages d'origine ........ 16 à 31 s, réponse VIDE
#   conversation, raisonnement coupé ........ 0,4 à 1,0 s
#   commande avec outils, raisonnement ...... 7,1 s médian, appel émis 6/6
#   commande avec outils, sans raisonnement . 1,0 s médian, appel émis 2/6
# D'où LLM_BACKEND=ha, qui confie les commandes au moteur d'intentions
# déterministe de Home Assistant et supprime complètement cet arbitrage.
# =============================================================================
set -euo pipefail

SERVER_DIR="/opt/xiaozhi-esp32-server"
CONFIG_FILE="${SERVER_DIR}/data/.config.yaml"

# ── Paramètres (défauts sûrs ; surchargés par .env / compose) ────────
LLM_BACKEND="${LLM_BACKEND:-popllm}"      # popllm | claude | ha
POPLLM_URL="${POPLLM_URL:-http://127.0.0.1:11434}"
POPLLM_MODEL="${POPLLM_MODEL:-qwen-ha:latest}"
HA_BASE_URL="${HA_BASE_URL:-http://192.168.10.205:8123}"
HA_TOKEN="${HA_TOKEN:-}"
HA_DEVICES="${HA_DEVICES:-salon,exemple,light.exemple}"
HA_AGENT_ID="${HA_AGENT_ID:-conversation.home_assistant}"
ESP32_MAC="${ESP32_MAC:-3c:0f:02:de:a8:18}"
PUBLIC_IP="${PUBLIC_IP:-192.168.10.84}"
LANGUAGE="${LANGUAGE:-fr}"
ASR_BACKEND="${ASR_BACKEND:-parakeet}"
ASR_LANGUAGE="${ASR_LANGUAGE:-${LANGUAGE}}"
# Le Ryzen 9 3900X a 24 threads. Le défaut amont de 4 laissait la machine
# largement inutilisée pendant la transcription.
ASR_THREADS="${ASR_THREADS:-12}"
# Plafond de longueur des réponses. En mode outils, la réflexion de qwen-ha
# consomme ce budget avant la réponse (100 à 300 jetons) : en dessous, la
# réponse sort vide (vécu le 2026-10-07 à 140). Voir .env.popllm.example.
LLM_MAX_TOKENS="${LLM_MAX_TOKENS:-1024}"
LLM_TEMPERATURE="${LLM_TEMPERATURE:-0.3}"

# Durée de silence avant que le serveur ferme la session, en secondes.
# Le défaut amont est 120, pensé pour un assistant conversationnel : on parle,
# il répond, il raccroche. Mais le boîtier ne rouvre la connexion que sur mot
# de réveil, donc passé ce délai il devient injoignable et les notifications
# Claude Code repartent en « no_device ». Pour un compagnon de bureau posé en
# permanence sur USB, on garde la session ouverte. Le firmware, lui, désactive
# sa propre mise en veille dès qu'il détecte la charge.
# Repasser à 120 si l'appareil est sur batterie et qu'on veut préserver l'autonomie.
# Depuis le firmware modifié du 2026-10-06, le boîtier se reconnecte tout seul et
# ses pings (enable_websocket_ping plus bas) gardent la session active : ce délai
# ne joue plus qu'en l'absence de ping, par exemple avec un firmware d'origine.
CLOSE_NO_VOICE_TIME="${CLOSE_NO_VOICE_TIME:-86400}"

# Conservation des enregistrements après transcription. `true` par défaut,
# comme en amont : rien n'est gardé. Passer à `false` UNIQUEMENT le temps
# d'un diagnostic de captation (niveau, saturation, bruit de fond), puis
# remettre `true` et vider tmp-popllm/. Les fichiers contiennent la voix.
DELETE_AUDIO="${DELETE_AUDIO:-true}"

# Prompt par défaut : ACCENTUÉ (Piper phonémise littéralement : un texte
# sans accents se prononce faux, cf. bug « deux zoles / franquais ») et
# contraint en longueur, l'adjectif « concis » seul ne bridant rien.
#
# NB : le défaut passe par une variable intermédiaire. Une apostrophe placée
# directement dans un ${VAR:-défaut} ouvre une chaîne pour bash et casse le
# script (« unexpected EOF while looking for matching ' »).
DEFAULT_PROMPT="Tu es l'assistant vocal de la maison. Réponds toujours en français, en une seule phrase courte, sans préambule ni reformulation de la question. Tu peux consulter et contrôler la maison via Home Assistant. Si tu ne sais pas, dis-le en trois mots."
PROMPT="${PROMPT:-$DEFAULT_PROMPT}"

# ── Garde-fous ───────────────────────────────────────────────────────
if [ -z "${HA_TOKEN}" ]; then
  echo "[FATAL] HA_TOKEN vide. Renseigne-le dans .env (token longue durée HA)." >&2
  exit 1
fi
case "${LLM_BACKEND}" in
  popllm|claude|ha) ;;
  *) echo "[FATAL] LLM_BACKEND='${LLM_BACKEND}' invalide (popllm|claude|ha)." >&2; exit 1 ;;
esac
if echo "${POPLLM_URL}" | grep -q "localhost"; then
  echo "[WARN] POPLLM_URL=localhost, en network_mode host c'est OK (Ollama sur PopLLM)." >&2
fi

# ── Bloc LLM + mode d'intention selon backend ────────────────────────
# nointent avec le backend `ha` : Home Assistant possède son propre moteur
# d'intentions (déterministe, sub-seconde). Superposer celui de xiaozhi
# ferait travailler deux fois et rendrait la main au LLM pour rien.
INTENT_MODE="function_call"
case "${LLM_BACKEND}" in
  claude)
    LLM_MODULE="ClaudeLLM"
    LLM_BLOCK="  ClaudeLLM:
    type: Claude
    model_name: \"${MODEL_NAME:-claude-haiku-4-5-20251001}\"
    api_key: \"${ANTHROPIC_API_KEY:-}\"
    max_tokens: ${LLM_MAX_TOKENS}
    temperature: ${LLM_TEMPERATURE}"
    ;;
  ha)
    LLM_MODULE="HomeAssistantLLM"
    INTENT_MODE="nointent"
    # `language` est obligatoire : sans elle, le moteur d'intentions de Home
    # Assistant repond en anglais et le boitier prononce « Sorry, I couldn't
    # understand that » avec la voix francaise.
    LLM_BLOCK="  HomeAssistantLLM:
    type: homeassistant
    base_url: \"${HA_BASE_URL}\"
    api_key: \"${HA_TOKEN}\"
    agent_id: \"${HA_AGENT_ID}\"
    language: \"${LANGUAGE}\""
    ;;
  *)
    LLM_MODULE="PopLLM"
    LLM_BLOCK="  PopLLM:
    type: ollama
    model_name: \"${POPLLM_MODEL}\"
    base_url: \"${POPLLM_URL}\"
    max_tokens: ${LLM_MAX_TOKENS}
    temperature: ${LLM_TEMPERATURE}"
    ;;
esac

AUTH_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# ── Bloc ASR (parakeet = multilangue auto / whisper = langue forcée) ──
if [ "${ASR_BACKEND}" = "whisper" ]; then
  # ASR_MODEL=medium recommande : Parakeet fait de la detection automatique
  # de langue et bascule en anglais sur les phrases courtes ou bruitees
  # (« Uh maybe » pour du francais, constate le 2026-09-01). Whisper accepte
  # une langue forcee, donc pas de derive, mais `small` transcrivait mal
  # (« Bonne-moi le billion d'energie »). `medium` corrige la precision sans
  # rouvrir le probleme de langue.
  ASR_MODEL="${ASR_MODEL:-medium}"
  ASR_DIR_W="models/sherpa-onnx-whisper-${ASR_MODEL}"
  if [ ! -d "${SERVER_DIR}/${ASR_DIR_W}" ]; then
    echo "[WARN] ${ASR_DIR_W} absent de l'image, repli sur whisper-small." >&2
    ASR_DIR_W="models/sherpa-onnx-whisper-small"
  fi
  ASR_BLOCK="  SherpaASR:
    type: sherpa_onnx_local
    model_dir: ${ASR_DIR_W}
    output_dir: tmp/
    model_type: whisper
    num_threads: ${ASR_THREADS}
    language: \"${ASR_LANGUAGE}\""
else
  # Le dossier peut contenir la variante int8 ou fp32 : le chargeur détecte
  # les fichiers réellement présents (cf. patch_server.py).
  ASR_DIR="models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
  if [ -d "${SERVER_DIR}/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3" ]; then
    ASR_DIR="models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3"
  fi
  ASR_BLOCK="  SherpaASR:
    type: sherpa_onnx_local
    model_dir: ${ASR_DIR}
    output_dir: tmp/
    model_type: transducer
    num_threads: ${ASR_THREADS}"
fi

# ── Prompt multi-ligne indenté proprement pour le bloc YAML ──────────
# Sans ça, un PROMPT contenant un saut de ligne cassait l'indentation du
# scalaire `prompt: |` et produisait un YAML invalide.
PROMPT_YAML="$(printf '%s\n' "${PROMPT}" | sed 's/^/  /')"

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
  Intent: ${INTENT_MODE}

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
  nointent:
    type: nointent

# Silence tolere avant fermeture de la session (voir commentaire en tete).
close_connection_no_voice_time: ${CLOSE_NO_VOICE_TIME}

# Reponse pong aux {"type":"ping"} que le firmware modifie envoie toutes les
# 30 s quand il est au repos. Le pong evite que le boitier juge la connexion
# morte (delai de 120 s cote firmware), et le ping rafraichit l'horodatage
# d'activite, sans quoi le serveur fermerait la session inactive au bout de
# close_connection_no_voice_time.
enable_websocket_ping: true

# Modele du prompt enrichi. Celui d'amont (agent-base-prompt.txt) est
# entierement en chinois : des qu'il s'applique, Qwen repond en chinois et le
# filtre fait dire « Desole, je me suis trompe de langue ». Avec une connexion
# permanente il s'applique toujours (vecu le 2026-10-06). La version francaise
# donne aussi l'heure et la date, et ne declenche pas la geolocalisation par IP
# (service chinois qui bloquait la construction du prompt pendant des minutes).
prompt_template: agent-base-prompt-fr.txt

# Effacement des enregistrements apres transcription.
delete_audio: ${DELETE_AUDIO}

# Message de fin de session. Le defaut amont est un prompt CHINOIS, qui
# faisait repondre le modele en chinois puis declenchait le filtre anti-CJK :
# le boitier prononcait alors « Desole, je me suis trompe de langue ».
end_prompt:
  enable: true
  prompt: |
    Termine la conversation en une phrase courte et chaleureuse, en francais,
    sans poser de question.

plugins:
  home_assistant:
    devices: "${HA_DEVICES}"
    base_url: "${HA_BASE_URL}"
    api_key: "${HA_TOKEN}"

prompt: |
${PROMPT_YAML}
ENDOFCONFIG

# Validation du YAML avant de lancer le serveur : jusqu'ici un fichier
# invalide produisait un plantage obscur au démarrage.
python3 -c "import yaml; yaml.safe_load(open('${CONFIG_FILE}', encoding='utf-8')); print('[OK] YAML valide')" \
  || { echo "[FATAL] data/.config.yaml invalide, arret." >&2; exit 1; }

if [ "${ASR_BACKEND}" = "whisper" ]; then
  # Le libelle disait « small » en dur, quelle que soit la taille reellement
  # chargee. Un journal qui ment sur sa configuration coute cher a debugger.
  ASR_LABEL="Whisper $(basename "${ASR_DIR_W}" | sed 's/^sherpa-onnx-whisper-//') (langue=${ASR_LANGUAGE} forcee)"
else
  ASR_LABEL="Parakeet V3 (multilangue auto, detection de langue)"
fi

echo "[OK] Config generee -> ${CONFIG_FILE}"
case "${LLM_BACKEND}" in
  ha)
    echo "[OK] LLM=Home Assistant (agent ${HA_AGENT_ID}) | Intent=nointent (moteur HA)"
    echo "[OK] Les commandes passent par le moteur d'intentions HA : deterministe, sub-seconde."
    ;;
  claude)
    echo "[OK] LLM=Claude (${MODEL_NAME:-claude-haiku-4-5-20251001}) | Intent=${INTENT_MODE}"
    ;;
  *)
    echo "[OK] LLM=PopLLM (${POPLLM_MODEL} @ ${POPLLM_URL}) | Intent=${INTENT_MODE}"
    echo "[OK] Raisonnement coupe en conversation, conserve sur les commandes"
    echo "     (OLLAMA_TOOLS_REASONING=${OLLAMA_TOOLS_REASONING:-on})"
    ;;
esac
echo "[OK] HA=${HA_BASE_URL} | ASR=${ASR_LABEL} ${ASR_THREADS} threads | TTS=Piper local"
echo "[OK] Reponses plafonnees a ${LLM_MAX_TOKENS} tokens, temperature ${LLM_TEMPERATURE}"

cd "${SERVER_DIR}"
exec python3 app.py
