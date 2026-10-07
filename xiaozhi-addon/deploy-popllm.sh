#!/usr/bin/env bash
# =============================================================================
# Deploiement des changements Claude Code sur PopLLM (192.168.10.84).
# A lancer depuis le PC (Git Bash) quand PopLLM est joignable.
#
#   bash deploy-popllm.sh
#
# Ce script : sauvegarde l'image actuelle, copie les fichiers modifies,
# rebuild, restart, et verifie. Rollback express en cas de probleme :
#   ssh ... 'docker tag xiaozhi-popllm:before-deploy xiaozhi-popllm:latest && \
#            cd ~/xiaozhi-popllm && sudo docker compose -f docker-compose.popllm.yml up -d'
# =============================================================================
set -euo pipefail

# Resolution du dossier .ssh. $HOME n'est pas toujours defini selon le
# contexte d'execution (tache de fond, cron, shell non interactif) ; sans
# ce repli, ssh echouait sur un laconique « Host key verification failed »,
# le fichier known_hosts pointant vers un chemin inexistant.
SSH_DIR="${SSH_DIR:-}"
if [ -z "$SSH_DIR" ]; then
  # On retient le premier dossier qui contient REELLEMENT les deux fichiers.
  # Se contenter d'un dossier existant ne suffit pas : sous Git Bash, $HOME
  # peut valoir /home/<user> alors que les cles sont dans /c/Users/<user>.
  for CAND in "${HOME:-}/.ssh" "${USERPROFILE:-}/.ssh" "/c/Users/${USER:-}/.ssh" \
              "/c/Users/${USERNAME:-}/.ssh"; do
    if [ -f "$CAND/id_ed25519" ] && [ -f "$CAND/kh_popllm" ]; then
      SSH_DIR="$CAND"; break
    fi
  done
fi
if [ -z "$SSH_DIR" ]; then
  echo "[FATAL] dossier .ssh introuvable (cherche id_ed25519 + kh_popllm)." >&2
  echo "        surcharge : SSH_DIR=/chemin/vers/.ssh bash $0" >&2
  exit 1
fi
KEY="${SSH_KEY:-$SSH_DIR/id_ed25519}"
KH="${SSH_KNOWN_HOSTS:-$SSH_DIR/kh_popllm}"
HOST="pop@192.168.10.84"

for F in "$KEY" "$KH"; do
  [ -f "$F" ] || { echo "[FATAL] fichier SSH introuvable : $F" >&2
                   echo "        surcharge possible : SSH_DIR=... bash $0" >&2
                   exit 1; }
done
REMOTE="/home/pop/xiaozhi-popllm"
SRC="$(cd "$(dirname "$0")" && pwd)"

SSH="ssh -o BatchMode=yes -o UserKnownHostsFile=$KH -i $KEY $HOST"
SCP="scp -o BatchMode=yes -o UserKnownHostsFile=$KH -i $KEY"

echo "== 1. Test de connexion =="
$SSH "echo OK && hostname"

echo "== 2. Sauvegarde de l'image actuelle (rollback) =="
$SSH "sudo docker tag xiaozhi-popllm:latest xiaozhi-popllm:before-deploy 2>/dev/null || true; sudo docker images xiaozhi-popllm"

echo "== 2b. Controle des fins de ligne (pre-vol) =="
# Un fichier enregistre en CRLF depuis Windows casse le shebang cote Linux :
# le conteneur boucle alors en Restarting (127) avec
# « /usr/bin/env: 'bash\r': No such file or directory » (vecu le 2026-09-01).
# On corrige sur place plutot que d'echouer : c'est sans risque et idempotent.
CRLF_FIXED=0
for F in popllm-entrypoint.sh patch_server.py patch_claude_notify.py \
         patch_ollama_nothink.py patch_ha_tls.py patch_no_chinese.py \
         patch_persistent_conn.py agent-base-prompt-fr.txt patch_tools_fr.py \
         patch_mirror_event.py \
         claude_decide.py Dockerfile.popllm .env.popllm.example; do
  if [ -f "$SRC/$F" ] && grep -qU $'\r' "$SRC/$F" 2>/dev/null; then
    python3 -c "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n'))" "$SRC/$F"
    echo "   CRLF corrige : $F"
    CRLF_FIXED=$((CRLF_FIXED+1))
  fi
done
[ "$CRLF_FIXED" -eq 0 ] && echo "   tous les fichiers sont deja en LF"

echo "== 3. Copie des fichiers modifies =="
# patch_server.py et patch_ollama_nothink.py ajoutes le 2026-09-01 :
# le premier a ete modifie (threads ASR + detection int8/fp32), le second
# est nouveau (raisonnement + plafond de verbosite du provider Ollama).
$SCP "$SRC/popllm-entrypoint.sh" \
     "$SRC/patch_server.py" \
     "$SRC/patch_claude_notify.py" \
     "$SRC/patch_ollama_nothink.py" \
     "$SRC/patch_ha_tls.py" \
     "$SRC/patch_claude_resolve.py" \
     "$SRC/claude_decide.py" \
     "$SRC/patch_no_chinese.py" \
     "$SRC/patch_persistent_conn.py" \
     "$SRC/agent-base-prompt-fr.txt" \
     "$SRC/patch_tools_fr.py" \
     "$SRC/patch_mirror_event.py" \
     "$SRC/Dockerfile.popllm" \
     "$SRC/.env.popllm.example" \
     "$HOST:$REMOTE/"

echo "== 4. Rebuild (detache, survit a une coupure SSH) =="
# Le build dure plusieurs minutes et retelecharge environ 1 Go de modeles des
# que patch_server.py change. En avant-plan il mourait avec la session SSH :
# vecu le 2026-09-01, « Connection reset by peer » a mi-parcours, tout perdu.
# setsid + nohup le detachent : la coupure ne l'interrompt plus.
$SSH "cd $REMOTE && rm -f build.log && \
      setsid nohup sudo docker compose -f docker-compose.popllm.yml build \
      > build.log 2>&1 < /dev/null & sleep 2; echo '   build lance en tache de fond'"

echo "   suivi (une coupure ici n'interrompt pas le build distant)"
while true; do
  # On teste le LOG D'ABORD, jamais pgrep en premier : `pgrep -f 'compose.*build'`
  # se matche lui-meme a travers la ligne de commande SSH, donc il repond
  # toujours RUNNING et la boucle n'aboutit jamais (vecu deux fois le
  # 2026-09-01, sur des builds pourtant termines).
  STATE=$($SSH "cd $REMOTE
    if grep -qiE 'Image .* Built|successfully built|writing image' build.log 2>/dev/null; then echo DONE
    elif grep -qiE '^ERROR|failed to solve' build.log 2>/dev/null; then echo FAILED
    elif pgrep -x 'buildkitd|dockerd' >/dev/null 2>&1 && [ -s build.log ]; then echo RUNNING
    else echo RUNNING; fi" 2>/dev/null || echo UNREACHABLE)
  case "$STATE" in
    RUNNING)     $SSH "cd $REMOTE && tail -1 build.log" 2>/dev/null; sleep 20 ;;
    DONE)        echo "   build termine"; break ;;
    UNREACHABLE) echo "   hote injoignable, nouvelle tentative dans 20 s"; sleep 20 ;;
    *)           echo "[FATAL] build echoue. 30 dernieres lignes :" >&2
                 $SSH "cd $REMOTE && tail -30 build.log" >&2
                 echo "Rollback : sudo docker tag xiaozhi-popllm:before-deploy xiaozhi-popllm:latest" >&2
                 exit 1 ;;
  esac
done

echo "== 5. Restart =="
$SSH "cd $REMOTE && sudo docker compose -f docker-compose.popllm.yml up -d"
sleep 8

echo "== 6. Verification =="
$SSH "sudo docker ps --filter name=xiaozhi-popllm --format '{{.Status}}'"
echo "-- Routes Claude presentes ? --"
$SSH "sudo docker exec xiaozhi-popllm grep -c 'claude_decision_handler\|api/claude/notify' /opt/xiaozhi-esp32-server/core/http_server.py"
echo "-- Plugin claude_decide present ? --"
$SSH "sudo docker exec xiaozhi-popllm test -f /opt/xiaozhi-esp32-server/plugins_func/functions/claude_decide.py && echo PRESENT || echo ABSENT"
echo "-- ASR actif (log) --"
$SSH "sudo docker logs xiaozhi-popllm 2>&1 | grep -E 'ASR=|Loading.*Transducer|Loading.*model' | tail -3"
echo "-- Correctif latence applique ? (doit afficher reasoning_effort) --"
$SSH "sudo docker exec xiaozhi-popllm grep -c 'reasoning_effort' /opt/xiaozhi-esp32-server/core/providers/llm/ollama/ollama.py"
echo "-- Backend et plafond de verbosite --"
$SSH "sudo docker logs xiaozhi-popllm 2>&1 | grep -E 'LLM=|plafonnees|Intent=' | tail -4"
echo "-- Connexion permanente : registre nettoye + pong actif ? (doit afficher 1 et true) --"
$SSH "sudo docker exec xiaozhi-popllm grep -c 'ACTIVE_CLAUDE_CONNS.discard(self)' /opt/xiaozhi-esp32-server/core/connection.py"
$SSH "sudo docker exec xiaozhi-popllm grep '^enable_websocket_ping' /opt/xiaozhi-esp32-server/data/.config.yaml"
echo "-- Reponse apres outil sans raisonnement ? (doit afficher 1) --"
$SSH "sudo docker exec xiaozhi-popllm grep -c 'dialogue\[-1\].get(\"role\") == \"tool\"' /opt/xiaozhi-esp32-server/core/providers/llm/ollama/ollama.py"
echo "-- Evenement xiaozhi_announce ecoute par le miroir ? (doit afficher 1 ou plus) --"
$SSH "sudo docker exec xiaozhi-popllm grep -c 'xiaozhi_announce' /opt/xiaozhi-esp32-server/core/ha_announce_mirror.py"
echo "-- Prompt enrichi francais ? (doit afficher agent-base-prompt-fr.txt) --"
$SSH "sudo docker exec xiaozhi-popllm grep '^prompt_template' /opt/xiaozhi-esp32-server/data/.config.yaml"
echo "-- Phrase de repli correctement accentuee ? --"
$SSH "sudo docker exec xiaozhi-popllm grep -c 'Désolé, je me suis trompé de langue' /opt/xiaozhi-esp32-server/core/providers/tts/base.py"

echo ""
echo "== Deploiement termine. Test rapide : =="
echo "curl -X POST http://192.168.10.84:8003/api/claude/notify -H 'Content-Type: application/json' -d '{\"text\":\"Deploiement valide\"}'"
