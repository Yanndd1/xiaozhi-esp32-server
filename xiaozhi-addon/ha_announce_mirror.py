"""Miroir des annonces vocales Home Assistant vers le boitier Xiaozhi.

POURQUOI CE MODULE PLUTOT QU'UNE AUTOMATION HOME ASSISTANT
----------------------------------------------------------
La facon habituelle de renvoyer une annonce vers un appareil tiers est un
`rest_command` declare dans configuration.yaml, appele par une automation.
Cela suppose un acces en ecriture au fichier de configuration de HA, que nous
n'avons pas (SSH ferme sur l'instance). Ce module fait donc l'inverse : il
s'abonne au flux d'evenements de Home Assistant et recopie lui-meme les
annonces. Consequence : AUCUNE modification cote Home Assistant, ni fichier,
ni automation, ni helper. Desactiver = une variable d'environnement.

CE QU'IL ECOUTE
---------------
Releve du 2026-09-01 sur les 23 automations d'annonce existantes :
    assist_satellite.announce  -> 18 automations (satellite Pi)
    tts.speak                  ->  4 automations (Piper, HA Cloud)
Ecouter le seul `assist_satellite.announce` en aurait donc rate un cinquieme,
dont l'alerte radioactivite critique. Les deux services sont couverts.

REGLAGES (variables d'environnement du conteneur)
-------------------------------------------------
    HA_MIRROR_ANNOUNCE   on | off   (defaut off)
    HA_MIRROR_SERVICES   liste "domaine.service" separee par des virgules
                         (defaut "assist_satellite.announce,tts.speak")
    HA_BASE_URL          reutilise la configuration existante
    HA_TOKEN             idem
    HA_VERIFY_TLS        idem (false par defaut, certificat auto-signe)
"""
import asyncio
import os
import ssl
import time
import uuid

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# Deux annonces identiques a moins de 5 s d'intervalle : on n'en dit qu'une.
# Certaines automations HA se declenchent deux fois sur un meme changement
# d'etat, et on ne veut pas que le boitier begaie.
_DEDUP_WINDOW_S = 5.0
_last_spoken = {"text": "", "at": 0.0}


def _enabled():
    return os.environ.get("HA_MIRROR_ANNOUNCE", "off").strip().lower() in (
        "on", "1", "true", "yes"
    )


def _services():
    raw = os.environ.get(
        "HA_MIRROR_SERVICES", "assist_satellite.announce,tts.speak"
    )
    out = set()
    for item in raw.split(","):
        item = item.strip()
        if "." in item:
            domain, service = item.split(".", 1)
            out.add((domain.strip(), service.strip()))
    return out


def _ssl_context():
    verify = os.environ.get("HA_VERIFY_TLS", "false").strip().lower()
    if verify in ("", "false", "0", "no", "off"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if verify in ("true", "1", "yes", "on"):
        return None  # verification standard
    return ssl.create_default_context(cafile=verify)


def _extract_message(service_data):
    """Recupere le texte a prononcer, quel que soit le service appelant."""
    if not isinstance(service_data, dict):
        return ""
    for key in ("message", "announce_text", "text"):
        value = service_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _speak(text):
    """Pousse le texte dans la file TTS du premier boitier connecte.

    Retourne False si aucun boitier n'ecoute : c'est normal, l'appareil se
    deconnecte au repos. On ne met rien en file d'attente, une annonce
    meteo rejouee deux heures plus tard n'aurait aucun sens.
    """
    try:
        from core.connection import ACTIVE_CLAUDE_CONNS
        from core.providers.tts.dto.dto import (
            TTSMessageDTO, SentenceType, ContentType,
        )
    except Exception as e:  # patch_claude_notify absent
        logger.bind(tag=TAG).error(f"etat partage indisponible : {e}")
        return False

    for conn in list(ACTIVE_CLAUDE_CONNS):
        if getattr(conn, "tts", None) is None:
            continue
        try:
            sid = uuid.uuid4().hex
            conn.sentence_id = sid
            conn.tts.tts_text_queue.put(TTSMessageDTO(
                sentence_id=sid, sentence_type=SentenceType.FIRST,
                content_type=ContentType.ACTION))
            conn.tts.tts_text_queue.put(TTSMessageDTO(
                sentence_id=sid, sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.TEXT, content_detail=text))
            conn.tts.tts_text_queue.put(TTSMessageDTO(
                sentence_id=sid, sentence_type=SentenceType.LAST,
                content_type=ContentType.ACTION))
            return True
        except Exception as e:
            logger.bind(tag=TAG).error(f"echec de mise en file TTS : {e}")
    return False


async def _session(base_url, token, services):
    """Une session websocket complete. Leve en cas de coupure."""
    import aiohttp

    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = ws_url.rstrip("/") + "/api/websocket"
    ctx = _ssl_context()

    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(ws_url, ssl=ctx, heartbeat=30) as ws:
            hello = await ws.receive_json()
            if hello.get("type") != "auth_required":
                raise RuntimeError(f"accueil inattendu : {hello.get('type')}")
            await ws.send_json({"type": "auth", "access_token": token})
            auth = await ws.receive_json()
            if auth.get("type") != "auth_ok":
                raise RuntimeError("authentification refusee par Home Assistant")

            await ws.send_json({"id": 1, "type": "subscribe_events",
                                "event_type": "call_service"})
            ack = await ws.receive_json()
            if not ack.get("success"):
                raise RuntimeError(f"abonnement refuse : {ack}")

            noms = ", ".join(sorted(f"{d}.{s}" for d, s in services))
            logger.bind(tag=TAG).info(f"miroir actif, services suivis : {noms}")

            async for raw in ws:
                if raw.type != aiohttp.WSMsgType.TEXT:
                    continue
                try:
                    msg = raw.json()
                except Exception:
                    continue
                if msg.get("type") != "event":
                    continue
                data = (msg.get("event") or {}).get("data") or {}
                key = (data.get("domain"), data.get("service"))
                if key not in services:
                    continue
                text = _extract_message(data.get("service_data"))
                if not text:
                    continue

                now = time.time()
                if (text == _last_spoken["text"]
                        and now - _last_spoken["at"] < _DEDUP_WINDOW_S):
                    continue
                _last_spoken["text"] = text
                _last_spoken["at"] = now

                spoken = _speak(text)
                logger.bind(tag=TAG).info(
                    f"annonce {key[0]}.{key[1]} "
                    f"{'relayee' if spoken else 'ignoree (aucun boitier)'} : "
                    f"{text[:70]}"
                )
            raise RuntimeError("flux websocket ferme par Home Assistant")


async def run_mirror(config=None):
    """Boucle principale, relancee indefiniment avec un recul progressif."""
    if not _enabled():
        logger.bind(tag=TAG).info(
            "miroir des annonces desactive (HA_MIRROR_ANNOUNCE=off)")
        return

    base_url = os.environ.get("HA_BASE_URL", "").strip()
    token = os.environ.get("HA_TOKEN", "").strip()
    if not base_url or not token:
        logger.bind(tag=TAG).error(
            "miroir impossible : HA_BASE_URL ou HA_TOKEN absent")
        return

    services = _services()
    delay = 3
    while True:
        try:
            await _session(base_url, token, services)
        except asyncio.CancelledError:
            logger.bind(tag=TAG).info("miroir arrete")
            raise
        except Exception as e:
            logger.bind(tag=TAG).warning(
                f"miroir interrompu ({e}), nouvelle tentative dans {delay}s")
        await asyncio.sleep(delay)
        delay = min(delay * 2, 60)  # recul progressif, plafonne a 1 minute
