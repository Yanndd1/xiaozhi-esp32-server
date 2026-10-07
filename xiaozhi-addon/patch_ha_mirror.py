#!/usr/bin/env python3
"""
Patch additif : demarrer le miroir des annonces Home Assistant.

Le module core/ha_announce_mirror.py est copie par le Dockerfile. Ce patch se
contente de lancer sa boucle au demarrage du serveur, a cote des taches
websocket et http existantes, et de l'annuler proprement a l'arret.

Le module s'auto-desactive si HA_MIRROR_ANNOUNCE n'est pas a "on", donc ce
patch est sans effet tant que la variable n'est pas positionnee.

S'applique pendant le build Docker, apres patch_claude_notify.py (le miroir
reutilise son etat partage ACTIVE_CLAUDE_CONNS).
Rollback : retirer ce fichier + les lignes du Dockerfile, rebuild.
"""
import pathlib
import sys

p = pathlib.Path('app.py')
t = p.read_text(encoding='utf-8')

MARKER = "ha_announce_mirror"
if MARKER in t:
    print('[patch_mirror] deja applique, rien a faire')
    sys.exit(0)

applied = []

# ── A. Import du module ──────────────────────────────────────────────
OLD_IMPORT = 'from core.utils.gc_manager import get_gc_manager'
NEW_IMPORT = ('from core.utils.gc_manager import get_gc_manager\n'
              'from core.ha_announce_mirror import run_mirror as _ha_mirror_run')
if OLD_IMPORT not in t:
    print('[patch_mirror] ECHEC : ancre d import introuvable', file=sys.stderr)
    sys.exit(1)
t = t.replace(OLD_IMPORT, NEW_IMPORT, 1)
applied.append('import du module')

# ── B. Demarrage de la tache ─────────────────────────────────────────
OLD_START = ('    ota_server = SimpleHttpServer(config)\n'
             '    ota_task = asyncio.create_task(ota_server.start())')
NEW_START = ('    ota_server = SimpleHttpServer(config)\n'
             '    ota_task = asyncio.create_task(ota_server.start())\n'
             '\n'
             '    # Miroir des annonces vocales Home Assistant vers le boitier.\n'
             '    # Inactif tant que HA_MIRROR_ANNOUNCE != on.\n'
             '    mirror_task = asyncio.create_task(_ha_mirror_run(config))')
if OLD_START not in t:
    print('[patch_mirror] ECHEC : ancre de demarrage introuvable', file=sys.stderr)
    sys.exit(1)
t = t.replace(OLD_START, NEW_START, 1)
applied.append('tache demarree')

# ── C. Arret propre ──────────────────────────────────────────────────
OLD_STOP = ('        stdin_task.cancel()\n'
            '        ws_task.cancel()')
NEW_STOP = ('        stdin_task.cancel()\n'
            '        ws_task.cancel()\n'
            '        mirror_task.cancel()')
if OLD_STOP not in t:
    print('[patch_mirror] ECHEC : ancre d arret introuvable', file=sys.stderr)
    sys.exit(1)
t = t.replace(OLD_STOP, NEW_STOP, 1)
applied.append('annulation a l arret')

p.write_text(t, encoding='utf-8')
for a in applied:
    print(f'[patch_mirror] OK {a}')
print('[patch_mirror] OK - miroir des annonces HA pret')
