#!/usr/bin/env python3
"""
Patch additif : boitier connecte en permanence (firmware modifie le 2026-10-06).

Le firmware du boitier garde desormais sa connexion WebSocket ouverte au repos,
la rouvre tout seul apres une coupure et envoie {"type":"ping"} toutes les 30 s.
Ce patch adapte le serveur :

  A. connection.py : une connexion est retiree du registre ACTIVE_CLAUDE_CONNS
     des sa fermeture. Avant, elle n'en sortait jamais : /api/claude/notify
     choisissait une connexion morte et repondait "ok" sans rien prononcer, et
     chaque connexion fermee gardait en memoire son propre modele Piper.
  B. connection.py : claude_live_conns() renvoie les connexions vivantes
     (WebSocket ouvert, pas en cours de fermeture, TTS initialise), la plus
     recente d'abord. Un boitier qui se reconnecte avant que l'ancienne socket
     ne tombe (jusqu'a ~40 s) a deux entrees : on prend la neuve.
  C. http_server.py et ha_announce_mirror.py : les trois points qui choisissent
     un boitier (notify, resolve, miroir HA) passent par claude_live_conns().
     ha_announce_mirror.py est modifie ici plutot qu'a la source pour ne pas
     invalider le cache Docker des couches de modeles (2 Go a retelecharger).
  D. textMessageProcessor.py : les ping de maintien passent en DEBUG, un INFO
     toutes les 30 s noyait le journal.
  E. dialogue.py : {{current_date}} est remplace a chaque requete par la date
     du jour en francais, comme {{current_time}} l'est deja par l'heure. Une
     connexion qui dure des jours garderait sinon la date figee a la
     construction du prompt. Utilise par agent-base-prompt-fr.txt.
  F. sendAudioHandle.py : les accents sont conserves sur l'ecran. La police du
     firmware v2 contient les lettres accentuees latines ; seuls l'apostrophe typographique, les points de suspension, oe, les tirets longs et l'euro,
     absents de la police, sont remplaces. L'ancien firmware 1.6.6 n'avait pas
     les accents, d'ou la suppression systematique faite jusqu'ici.

La reponse pong existe deja en amont (pingMessageHandler). Elle est activee par
enable_websocket_ping: true, ecrit par popllm-entrypoint.sh ; elle rafraichit
aussi l'horodatage d'activite, sans quoi le serveur fermerait la session
inactive apres close_connection_no_voice_time.

S'applique en fin de build, apres patch_claude_notify.py, patch_claude_resolve.py
et patch_ha_mirror.py. Rollback : retirer ce fichier + ses lignes du Dockerfile.
"""
import pathlib
import sys


def patch(path, old, new, label, required=True, count=1):
    """Remplace old par new (count=0 : toutes les occurrences, au moins une)."""
    p = pathlib.Path(path)
    t = p.read_text(encoding='utf-8')
    if new in t:
        print(f'[patch_persist] deja applique : {label}')
        return
    n = t.count(old)
    if n < max(count, 1):
        if required:
            print(f'[patch_persist] ECHEC : ancre introuvable pour {label} ({path})',
                  file=sys.stderr)
            sys.exit(1)
        print(f'[patch_persist] ignore (ancre absente) : {label}')
        return
    t = t.replace(old, new) if count == 0 else t.replace(old, new, count)
    p.write_text(t, encoding='utf-8')
    print(f'[patch_persist] OK {label}')


# ── A. Registre : horodatage a l'entree, retrait a la fermeture ───────────
patch(
    'core/connection.py',
    '            # Claude Code integration : enregistrer cette connexion\n'
    '            ACTIVE_CLAUDE_CONNS.add(self)\n',
    '            # Claude Code integration : enregistrer cette connexion\n'
    '            self.claude_registered_at = time.time()\n'
    '            ACTIVE_CLAUDE_CONNS.add(self)\n',
    'horodatage a l enregistrement',
)
patch(
    'core/connection.py',
    '    async def close(self, ws=None):\n'
    '        """资源清理方法"""\n'
    '        try:\n',
    '    async def close(self, ws=None):\n'
    '        """资源清理方法"""\n'
    '        # Claude Code integration : une connexion fermee ne doit plus etre choisie\n'
    '        ACTIVE_CLAUDE_CONNS.discard(self)\n'
    '        try:\n',
    'retrait du registre a la fermeture',
)

# ── B. Selection des connexions vivantes ──────────────────────────────────
patch(
    'core/connection.py',
    'CLAUDE_LATEST_DECISION_ID = [None]  # conteneur mutable : dernier id en attente\n',
    'CLAUDE_LATEST_DECISION_ID = [None]  # conteneur mutable : dernier id en attente\n'
    '\n'
    '\n'
    'def claude_live_conns():\n'
    '    """Connexions boitier utilisables pour une annonce, la plus recente d abord."""\n'
    '    from websockets.protocol import State\n'
    '    live = []\n'
    '    for c in list(ACTIVE_CLAUDE_CONNS):\n'
    '        ws = getattr(c, "websocket", None)\n'
    '        stop = getattr(c, "stop_event", None)\n'
    '        if ws is None or getattr(ws, "state", None) is not State.OPEN:\n'
    '            continue\n'
    '        if stop is not None and stop.is_set():\n'
    '            continue\n'
    '        if getattr(c, "tts", None) is None:\n'
    '            continue\n'
    '        live.append(c)\n'
    '    live.sort(key=lambda c: getattr(c, "claude_registered_at", 0.0), reverse=True)\n'
    '    return live\n',
    'claude_live_conns()',
)

# ── C. Les trois points de choix du boitier ───────────────────────────────
patch(
    'core/http_server.py',
    'from core.connection import (\n'
    '    ACTIVE_CLAUDE_CONNS,\n',
    'from core.connection import (\n'
    '    ACTIVE_CLAUDE_CONNS,\n'
    '    claude_live_conns,\n',
    'import dans http_server.py',
)
patch(
    'core/http_server.py',
    'for conn in list(ACTIVE_CLAUDE_CONNS):',
    'for conn in claude_live_conns():',
    'notify + resolve (http_server.py)',
    count=0,
)
patch(
    'core/ha_announce_mirror.py',
    'from core.connection import ACTIVE_CLAUDE_CONNS',
    'from core.connection import claude_live_conns',
    'import dans ha_announce_mirror.py',
)
patch(
    'core/ha_announce_mirror.py',
    'for conn in list(ACTIVE_CLAUDE_CONNS):',
    'for conn in claude_live_conns():',
    'miroir HA (ha_announce_mirror.py)',
)

# ── D. Journal : ping de maintien en DEBUG ────────────────────────────────
patch(
    'core/handle/textMessageProcessor.py',
    '                conn.logger.bind(tag=TAG).info(f"收到{message_type}消息：{message}")\n',
    '                if message_type == "ping":\n'
    '                    conn.logger.bind(tag=TAG).debug(f"收到{message_type}消息：{message}")\n'
    '                else:\n'
    '                    conn.logger.bind(tag=TAG).info(f"收到{message_type}消息：{message}")\n',
    'ping en DEBUG',
    required=False,
)

# ── E. Date du jour recalculee a chaque requete ───────────────────────────
patch(
    'core/utils/dialogue.py',
    '            enhanced_system_prompt = enhanced_system_prompt.replace(\n'
    '                "{{current_time}}", datetime.now().strftime("%H:%M")\n'
    '            )\n',
    '            enhanced_system_prompt = enhanced_system_prompt.replace(\n'
    '                "{{current_time}}", datetime.now().strftime("%H:%M")\n'
    '            )\n'
    '            # Date du jour en francais, recalculee a chaque requete (connexion permanente)\n'
    '            if "{{current_date}}" in enhanced_system_prompt:\n'
    '                _now = datetime.now()\n'
    '                _jours = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")\n'
    '                _mois = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet",\n'
    '                         "août", "septembre", "octobre", "novembre", "décembre")\n'
    '                enhanced_system_prompt = enhanced_system_prompt.replace(\n'
    '                    "{{current_date}}",\n'
    '                    f"{_jours[_now.weekday()]} {_now.day} {_mois[_now.month - 1]} {_now.year}",\n'
    '                )\n',
    'date du jour dynamique (dialogue.py)',
)

# ── F. Accents conserves sur l'ecran (police du firmware v2) ──────────────
patch(
    'core/handle/sendAudioHandle.py',
    'def _strip_accents(text):\n'
    '    """Remove accents for ESP32 display (font lacks accented chars)."""\n'
    '    if not text:\n'
    '        return text\n'
    "    nfkd = unicodedata.normalize('NFKD', text)\n"
    "    return ''.join(c for c in nfkd if not unicodedata.combining(c))\n",
    'def _strip_accents(text):\n'
    '    """Adapt text to the ESP32 display font.\n'
    '\n'
    '    The firmware v2 font has the Latin-1 accented letters (patch of 2026-10-06):\n'
    '    keep them and only replace the few typographic characters it lacks.\n'
    '    """\n'
    '    if not text:\n'
    '        return text\n'
    '    for src, dst in (("\\u2019", "\'"), ("\\u2018", "\'"), ("\\u2026", "..."),\n'
    '                     ("\\u0153", "oe"), ("\\u0152", "OE"), ("\\u2013", "-"),\n'
    '                     ("\\u2014", "-"), ("\\u20ac", "euros"), ("\\u202f", " "),\n'
    '                     ("\\u00a0", " ")):\n'
    '        text = text.replace(src, dst)\n'
    '    return text\n',
    'accents conserves a l ecran (sendAudioHandle.py)',
)

# Controle final : plus aucun choix de boitier sur le registre brut
for f in ('core/http_server.py', 'core/ha_announce_mirror.py'):
    if 'list(ACTIVE_CLAUDE_CONNS)' in pathlib.Path(f).read_text(encoding='utf-8'):
        print(f'[patch_persist] ECHEC : {f} choisit encore sur le registre brut',
              file=sys.stderr)
        sys.exit(1)
print('[patch_persist] OK - connexion permanente prise en charge')
