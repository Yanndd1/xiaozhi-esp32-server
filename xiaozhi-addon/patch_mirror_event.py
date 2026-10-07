#!/usr/bin/env python3
"""
Patch additif : annonces Home Assistant reservees au boitier (2026-10-07).

Le miroir (core/ha_announce_mirror.py) recopie les annonces destinees au
satellite du salon : elles sortent donc des deux appareils. Pour qu'une
annonce sorte du boitier SEUL (detection Frigate, evenement de la maison...),
le miroir ecoute en plus un evenement Home Assistant dedie :

    action d'automation :
      - event: xiaozhi_announce
        event_data:
          message: "Quelqu'un est detecte sur la camera Yi Portail."

Aucune modification de configuration.yaml : une automation peut declencher un
evenement nativement. Le texte passe par la meme file TTS que le reste
(deduplication 5 s comprise).

Modifie core/ha_announce_mirror.py dans l'image, comme patch_persistent_conn.py,
pour ne pas invalider le cache Docker des couches de modeles.
S'applique apres patch_persistent_conn.py.
Rollback : retirer ce fichier + ses lignes du Dockerfile, rebuild.
"""
import pathlib
import sys

P = pathlib.Path('core/ha_announce_mirror.py')
t = P.read_text(encoding='utf-8')
MARKER = 'xiaozhi_announce'
if MARKER in t:
    print('[patch_mirror_event] deja applique, rien a faire')
    sys.exit(0)

REPLACEMENTS = [
    (
        'abonnement',
        '            ack = await ws.receive_json()\n'
        '            if not ack.get("success"):\n'
        '                raise RuntimeError(f"abonnement refuse : {ack}")\n',
        '            ack = await ws.receive_json()\n'
        '            if not ack.get("success"):\n'
        '                raise RuntimeError(f"abonnement refuse : {ack}")\n'
        '\n'
        '            # Annonces reservees au boitier : evenement xiaozhi_announce\n'
        '            await ws.send_json({"id": 2, "type": "subscribe_events",\n'
        '                                "event_type": "xiaozhi_announce"})\n'
        '            while True:  # un evenement peut preceder l\'accuse de reception\n'
        '                ack2 = await ws.receive_json()\n'
        '                if ack2.get("id") == 2 and ack2.get("type") == "result":\n'
        '                    break\n'
        '            if not ack2.get("success"):\n'
        '                raise RuntimeError(f"abonnement refuse : {ack2}")\n',
    ),
    (
        'journal',
        '            logger.bind(tag=TAG).info(f"miroir actif, services suivis : {noms}")\n',
        '            logger.bind(tag=TAG).info(\n'
        '                f"miroir actif, services suivis : {noms}, evenement xiaozhi_announce")\n',
    ),
    (
        'traitement',
        '                data = (msg.get("event") or {}).get("data") or {}\n'
        '                key = (data.get("domain"), data.get("service"))\n'
        '                if key not in services:\n'
        '                    continue\n'
        '                text = _extract_message(data.get("service_data"))\n',
        '                event = msg.get("event") or {}\n'
        '                data = event.get("data") or {}\n'
        '                if event.get("event_type") == "xiaozhi_announce":\n'
        '                    key = ("event", "xiaozhi_announce")\n'
        '                    text = _extract_message(data)\n'
        '                else:\n'
        '                    key = (data.get("domain"), data.get("service"))\n'
        '                    if key not in services:\n'
        '                        continue\n'
        '                    text = _extract_message(data.get("service_data"))\n',
    ),
]

for label, old, new in REPLACEMENTS:
    if old not in t:
        print(f'[patch_mirror_event] ECHEC : ancre introuvable ({label})', file=sys.stderr)
        sys.exit(1)
    t = t.replace(old, new, 1)
    print(f'[patch_mirror_event] OK {label}')

P.write_text(t, encoding='utf-8')
print('[patch_mirror_event] OK - evenement xiaozhi_announce relaye vers le boitier')
