# Déploiement Xiaozhi sur PopLLM (offload du Pi5)

But : sortir le serveur Xiaozhi du Raspberry Pi 5 (qui est en épuisement mémoire,
~828 Mo + CPU rendus) et le faire tourner sur **PopLLM** (192.168.10.84 — Ryzen 9
3900X, 31 Gio RAM, GTX 1070 Ti, Ubuntu 24.04), **avec le LLM en Ollama local**
(zéro coût API, ASR Parakeet + LLM co-localisés).

Architecture cible : ESP32 → `ws://192.168.10.84:8000` → Xiaozhi (Docker, PopLLM)
→ Ollama `127.0.0.1:11434` (LLM) + Parakeet V3 (ASR) + Piper (TTS) en local →
Home Assistant `http://192.168.10.205:8123` (API + token).

> Le vocal **critique/proactif** (Geiger, intrusion, tempo, Tesla) reste sur le
> satellite AIY + HA, 24/7 sur le Pi5 → **éteindre PopLLM n'impacte que le
> conversationnel Xiaozhi** (acceptable).

---

## 0. Pré-requis (sur PopLLM, déjà OK au 2026-05-19)

```
ssh -i /c/Users/yannd/.ssh/id_ed25519 -o UserKnownHostsFile=/c/Users/yannd/.ssh/kh_popllm -o StrictHostKeyChecking=accept-new pop@192.168.10.84 'docker --version; ollama list | grep -E "qwen-ha|qwen3.5"'
```

Doit afficher Docker ≥ 24 et le modèle `qwen-ha:latest` (ou `qwen3.5:9b`). Si le
modèle manque : `ollama pull qwen3.5:9b`.

## 1. Copier le bundle sur PopLLM (depuis Windows, Git-Bash)

```
scp -i /c/Users/yannd/.ssh/id_ed25519 -o UserKnownHostsFile=/c/Users/yannd/.ssh/kh_popllm -o StrictHostKeyChecking=accept-new -r "/c/Users/yannd/Documents/claudecodelocal/xiaozhi/xiaozhi-esp32-server/xiaozhi-addon" pop@192.168.10.84:~/xiaozhi-popllm
```

## 2. Configurer le secret (sur PopLLM)

Créer un **token longue durée** dans HA (Profil → Jetons d'accès longue durée), puis :

```
ssh -i /c/Users/yannd/.ssh/id_ed25519 -o UserKnownHostsFile=/c/Users/yannd/.ssh/kh_popllm pop@192.168.10.84
```
```
cd ~/xiaozhi-popllm && cp .env.popllm.example .env && nano .env
```

Renseigner `HA_TOKEN=...` (et adapter `HA_DEVICES`, `ESP32_MAC` si besoin).
**Ne jamais commiter `.env`.**

## 3. Build + lancement

```
cd ~/xiaozhi-popllm && docker compose -f docker-compose.popllm.yml up -d --build
```

Le build télécharge les modèles (~1 Go : Parakeet 640 Mo + Whisper 370 Mo +
Piper + VAD) — quelques minutes, une seule fois.

## 4. Vérification

```
docker logs -f xiaozhi-popllm
```
Attendre `Config generee` puis le démarrage du serveur. Puis :
```
curl -fsS http://192.168.10.84:8003/xiaozhi/ota/ && echo OK
```

## 5. Repointer l'ESP32

Sur l'ESP32 (mode config — appui long bouton), régler l'adresse OTA sur :

```
http://192.168.10.84:8003/xiaozhi/ota/
```

Le device récupère ensuite automatiquement le websocket
`ws://192.168.10.84:8000/xiaozhi/v1/` (champ `server.websocket` de la config).

## 6. Réseau (UDR7)

ESP32 = `192.168.10.132`, PopLLM = `192.168.10.84` → **même sous-réseau
`192.168.10.0/24` (VLAN TRUSTED `br10`)** : a priori **aucune règle inter-VLAN
nécessaire**. Vérifier juste que l'ESP32 joint PopLLM :
```
ssh -i /c/Users/yannd/.ssh/id_ed25519 -o UserKnownHostsFile=/c/Users/yannd/.ssh/kh_popllm pop@192.168.10.84 'ss -tlnp | grep -E ":8000|:8003"'
```
Si l'ESP32 est en réalité sur un autre VLAN : ajouter une règle UDR7
*allow* `192.168.10.132 → 192.168.10.84 tcp 8000,8003`.

## 7. Bascule + repli

Une fois validé end-to-end, **arrêter l'add-on sur le Pi5** (HA → Terminal & SSH) :

```
ha addons stop local_xiaozhi-server
```

→ ~828 Mo + CPU rendus au Pi5 (le P0 mémoire est réglé). **Le garder installé
mais stoppé** = repli à froid sans coût RAM.

**Rollback** : `ha addons start local_xiaozhi-server` sur le Pi5 + repointer
l'ESP32 sur `http://192.168.10.205:8003/xiaozhi/ota/`.

---

## Notes

- **Extinction de PopLLM** : Xiaozhi devient indisponible (acceptable, cf. découpage
  par rôle). Option « à la demande » : Wake-on-LAN de PopLLM déclenché par une
  automation HA, réveil ~30 s.
- **GPU (optimisation future)** : l'image utilise `onnxruntime` CPU (le 3900X suffit,
  bien plus rapide que le Pi5). Pour exploiter la GTX 1070 Ti : remplacer par
  `onnxruntime-gpu` + base CUDA dans `Dockerfile.popllm` et `--gpus all`.
- **IP** : PopLLM = `192.168.10.84` (fixe). Les helpers `~/.ssh/popllm.sh` /
  `~/.ssh/config` pointent encore l'ancienne `.104` — à corriger séparément.
- **Sécurité** : aucun secret dans les fichiers versionnés ; tout via `.env`
  (non commité). Le `data/.config.yaml` est régénéré à chaque démarrage.
