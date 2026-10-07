# Intégration Claude Code → Xiaozhi (notification vocale)

> Ajoute une route HTTP `POST /api/claude/notify` au serveur Xiaozhi qui permet à un script externe (les hooks Claude Code sur le PC Windows) de faire **prononcer un texte arbitraire** par le device Xiaozhi via Piper TTS local.

## Architecture

```
PC Windows                                   PopLLM (192.168.10.84)
─────────────                                ─────────────────────
hooks Claude  ──── HTTP POST ──────────► port 8003  /api/claude/notify
(_xiaozhi_client.py)                              │
                                                  ▼
                                          ConnectionHandler (registry)
                                                  │
                                                  ▼
                                       tts.tts_text_queue.put(text)
                                                  │
                                                  ▼ WebSocket :8000
                                          Device Xiaozhi ESP32
                                          (prononce le texte via Piper)
```

## Ce qui change

| Fichier | État |
|---|---|
| `patch_claude_notify.py` (nouveau) | À copier sur PopLLM |
| `Dockerfile.popllm` (existant) | **+2 lignes** ajoutées après le RUN de `patch_server.py` |
| `core/*.py` du serveur cloné dans l'image | Modifié **au moment du build** (comme les 6 autres patches) |
| Repo source Windows `xiaozhi-esp32-server/` | **Inchangé** |
| Code firmware ESP32 | **Inchangé** |
| Plugins Home Assistant | **Inchangés** |

**Rollback complet** : retirer les 2 lignes du Dockerfile + supprimer `patch_claude_notify.py` + rebuild. Retour au comportement initial garanti.

## Procédure de déploiement (à faire sur PopLLM)

### 1. Récupérer les fichiers sur PopLLM

Depuis le PC Windows, transférer (au choix : `scp`, partage SMB, Git push, USB) ces 2 fichiers vers le dossier `xiaozhi-addon/` sur PopLLM :

- `C:\Users\yannd\Documents\claudecodelocal\xiaozhi\xiaozhi-esp32-server\xiaozhi-addon\patch_claude_notify.py`
- `C:\Users\yannd\Documents\claudecodelocal\xiaozhi\xiaozhi-esp32-server\xiaozhi-addon\Dockerfile.popllm` (modifié)

> Si le repo est versionné en Git et que PopLLM le pull, un simple `git pull` suffit.

### 2. (Optionnel) Sauvegarder l'image actuelle avant rebuild

```bash
ssh yannd@192.168.10.84
cd /chemin/vers/xiaozhi-esp32-server/xiaozhi-addon
docker tag xiaozhi-popllm:latest xiaozhi-popllm:before-claude-notify
docker images | grep xiaozhi-popllm  # confirme la sauvegarde
```

### 3. Rebuild et restart

```bash
cd /chemin/vers/xiaozhi-esp32-server/xiaozhi-addon
docker compose -f docker-compose.popllm.yml build --no-cache
docker compose -f docker-compose.popllm.yml up -d
```

Vérifier les logs au démarrage :
```bash
docker logs -f xiaozhi-popllm 2>&1 | grep -E "patch|Claude"
```

Tu dois voir, en plus des 6 messages habituels :
```
[patch_claude] connection.py: registry ACTIVE_CLAUDE_CONNS installe
[patch_claude] http_server.py: route POST /api/claude/notify installee
[patch_claude] OK — Claude Code integration prete
```

### 4. Vérifier que le device fonctionne normalement

Avant tout test Claude, **fais une interaction vocale standard** avec le Xiaozhi (genre demander la météo, contrôler une lampe HA). Ça doit marcher exactement comme avant. Si non → rollback (`docker tag xiaozhi-popllm:before-claude-notify xiaozhi-popllm:latest && docker compose up -d`).

### 5. Tester la nouvelle route

Depuis le PC Windows :

```powershell
# Test 1 : sans device id (utilise le 1er device actif)
curl -X POST http://192.168.10.84:8003/api/claude/notify `
     -H "Content-Type: application/json" `
     -d '{"text":"Bonjour, je suis Claude qui parle via Xiaozhi"}'
```

Réponse attendue :
- Si le device est connecté et idle :
  ```json
  {"status":"ok","device_id":"3c:0f:02:de:a8:18","session_id":"...","text":"Bonjour..."}
  ```
  Et le device prononce la phrase.
- Si pas de device connecté :
  ```json
  {"status":"no_device","reason":"no active Xiaozhi connection found"}
  ```

### 6. Activer côté PC

Dans la session PowerShell où tu utilises Claude Code (ou via les variables d'env système) :

```powershell
$env:ENABLE_XIAOZHI_NOTIFY = "1"
$env:XIAOZHI_NOTIFY_URL = "http://192.168.10.84:8003/api/claude/notify"
```

Pour rendre ça permanent :
```powershell
[System.Environment]::SetEnvironmentVariable("ENABLE_XIAOZHI_NOTIFY", "1", "User")
[System.Environment]::SetEnvironmentVariable("XIAOZHI_NOTIFY_URL", "http://192.168.10.84:8003/api/claude/notify", "User")
```

Redémarre une session Claude Code → les hooks utilisent maintenant le client.

## Comportement attendu

| Événement Claude Code | Message vocal Xiaozhi |
|---|---|
| `PermissionRequest` (Bash/Edit/Write…) | "Claude sur `<projet>` demande l'autorisation pour `<tool>`. `<détail>`. Approuve ou refuse." |
| `TaskCompleted` (subagent terminé) | "Tâche `<nom>` terminée sur `<projet>`." |
| `Stop` interrompu | "Tour interrompu sur `<projet>`." |
| `StopFailure` (erreur API) | "Erreur API `<type>` sur `<projet>`." |
| `Stop` "turn complete" normal | (rien — trop verbeux à la voix, garde le Flipper) |

## Sécurité

- La route `/api/claude/notify` n'a **pas d'authentification** dans cette V1. Le serveur écoute sur `0.0.0.0:8003` donc accessible depuis tout le LAN. Si tu veux durcir, ajouter un token vérifié dans le handler.
- L'utilisateur peut faire prononcer n'importe quel texte au device → si quelqu'un d'autre est sur le LAN, il peut faire dire des choses au Xiaozhi. Acceptable en réseau de confiance.

## Désinstallation

Sur PopLLM :
```bash
cd /chemin/vers/xiaozhi-esp32-server/xiaozhi-addon
# 1. Annuler les modif du Dockerfile (retirer les 4 lignes ajoutées)
git checkout Dockerfile.popllm        # si versionné
# OU edit manuel
# 2. Retirer le fichier
rm patch_claude_notify.py
# 3. Rebuild
docker compose -f docker-compose.popllm.yml build --no-cache
docker compose -f docker-compose.popllm.yml up -d
```

Sur le PC Windows :
```powershell
[System.Environment]::SetEnvironmentVariable("ENABLE_XIAOZHI_NOTIFY", $null, "User")
```

Les hooks continueront à tourner mais en mode no-op (le client xz.notify retourne False immédiatement).

## Connexion permanente (2026-10-06)

Jusqu'ici, presque toutes les annonces se perdaient : le firmware d'origine (1.6.6) n'ouvrait sa connexion WebSocket que pendant une conversation et la refermait au premier toucher, après 120 s sans message ou au moindre redémarrage du serveur. Entre le 12 septembre et le 6 octobre, le boîtier ne s'est connecté que deux fois, et aucune des ~2 500 notifications ni des 70 annonces Home Assistant n'a été entendue.

Deux changements, à garder ensemble :

| Côté | Changement | Où |
|---|---|---|
| Boîtier | Firmware v2.2.3 modifié : connexion ouverte dès le démarrage et rouverte seule, ping toutes les 30 s au repos, annonce reçue au repos puis retour en veille, toucher pendant l'écoute sans raccrocher, fin de conversation après 15 s de silence, mot d'éveil « Hi ESP », interface en français | `../../firmware-build/` (image flashée, patch source, LISEZMOI.txt) |
| Serveur | `patch_persistent_conn.py` : connexion retirée du registre à sa fermeture, choix de la connexion vivante la plus récente pour notify, resolve et miroir HA, pings journalisés en DEBUG | ce dossier, appliqué en fin de `Dockerfile.popllm` |
| Serveur | `enable_websocket_ping: true` : le serveur répond pong, et le ping garde la session active | `popllm-entrypoint.sh` |
| Serveur | Prompt enrichi en français (`agent-base-prompt-fr.txt`, via `prompt_template`) : le modèle d'amont, en chinois, s'appliquait dès qu'une connexion durait et faisait répondre Qwen en chinois (d'où « Désolé, je me suis trompé de langue »). Il donne aussi l'heure et la date, recalculées à chaque requête | `agent-base-prompt-fr.txt`, `popllm-entrypoint.sh`, point E du patch |
| Serveur | Annonces réservées au boîtier : le miroir écoute aussi l'événement Home Assistant `xiaozhi_announce` (`event_data: {message: ...}`). Une automation le déclenche, seul le boîtier parle (pas le satellite du salon) | `patch_mirror_event.py` |
| Home Assistant | 10 automatisations « Xiaozhi - ... » (2026-10-07). Boîtier seul : personne détectée par Frigate, sonnette, spa à température, fin de charge d'Elena, visage inconnu (maison occupée), caméra hors ligne. Les deux appareils (via `assist_satellite.announce`, recopié par le miroir) : fumée, coupure et retour du courant, porte d'entrée la nuit, rappel du câble d'Elena à 21 h. Plus la correction de `pi_voice_tesla_autonomie_faible`. Sources : `../../ha-annonces-xiaozhi.yaml` | Home Assistant |
| PC | Annonces « Sous-agent terminé » coupées (une par minute avec les workflows). Réactivables avec la variable utilisateur `XIAOZHI_SUBAGENT_NOTIFY=1` | `flipper-claude-buddy-win/plugin/scripts/on-subagent-stop.py` |
| Serveur | Accents conservés sur l'écran : la police du firmware v2 les a, seuls l'apostrophe typographique, les points de suspension, œ, les tirets longs et € sont remplacés | point F du patch |

Conséquence pour les hooks : `/api/claude/notify` dit maintenant la vérité. `{"status":"ok"}` signifie qu'une connexion vivante a reçu le texte ; boîtier injoignable, la réponse est `503 no_device`, ou `200 pending_only` avec `"spoken": false` si une décision est en jeu (elle reste validable par bouton).

Vérifications utiles :

```bash
# Le boîtier est-il connecté ? (dernières connexions et déconnexions)
ssh pop@192.168.10.84 'sudo docker exec xiaozhi-popllm sh -c "grep -a -E \"conn - Headers|客户端断开\" /opt/xiaozhi-esp32-server/tmp/server.log | tail -4"'
# Les annonces Home Assistant passent-elles ?
ssh pop@192.168.10.84 'sudo docker exec xiaozhi-popllm sh -c "grep -a ha_announce_mirror /opt/xiaozhi-esp32-server/tmp/server.log | tail -5"'
```

## Phase 2 (à venir — pas dans cette livraison)

- Validation vocale "approuve / refuse" via plugin LLM custom
- Coordination Flipper ↔ Xiaozhi (premier qui répond gagne)

---

*V1 — Notification unidirectionnelle Claude → Xiaozhi*  
*Compatible avec l'addon PopLLM existant (Whisper/Parakeet ASR, Piper TTS, Ollama LLM, HA plugin)*
