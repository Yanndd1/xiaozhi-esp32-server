#!/usr/bin/env python3
"""
Patch additif : acces HTTPS a Home Assistant + timeouts.

CONSTAT (2026-09-01) : le certificat de Home Assistant a ete emis le
6 aout 2026 (CN=homeassistant.local, auto-signe). Depuis cette date, HA
ne repond plus du tout en HTTP clair sur le port 8123 :

    http://192.168.10.205:8123/api/   -> HTTP 000 (Empty reply from server)
    https://192.168.10.205:8123/api/  -> HTTP 401 puis 200 avec le token

Le `.env` pointait toujours en http, donc le conteneur xiaozhi etait
coupe de Home Assistant depuis environ quatre semaines : aucune commande
domotique ne pouvait aboutir.

Passer en https ne suffit pas : le certificat est auto-signe et son CN est
`homeassistant.local`, un nom que ni l'hote ni le conteneur ne resolvent.
La verification TLS echouerait donc sur l'adresse IP. Deux choix :

  HA_VERIFY_TLS=false  (defaut) transport chiffre, pas d'authentification
                       du certificat. Equivalent de `curl -k`. Acceptable
                       sur le VLAN de confiance, ou HA est joint par IP fixe.
  HA_VERIFY_TLS=/chemin/ca.crt   verification contre le CA local. Suppose
                       d'utiliser une URL en `https://homeassistant.local:8123`
                       et donc que ce nom resolve depuis le conteneur.

Ajoute aussi des timeouts : le provider LLM homeassistant appelait
`requests.post` SANS timeout, donc une non-reponse de HA bloquait le
boitier indefiniment.

S'applique pendant le build Docker, apres patch_server.py.
Rollback : retirer ce fichier + les 2 lignes du Dockerfile, rebuild.
"""
import pathlib
import sys

MARKER = "# HA TLS (patch_ha_tls)"

HELPER = (
    MARKER + "\n"
    "import os as _os_tls\n"
    "\n"
    "def _ha_verify():\n"
    "    \"\"\"False, ou chemin d'un CA bundle, selon HA_VERIFY_TLS.\"\"\"\n"
    "    _v = _os_tls.environ.get('HA_VERIFY_TLS', 'false').strip()\n"
    "    if _v.lower() in ('', 'false', '0', 'no', 'off'):\n"
    "        try:\n"
    "            import urllib3 as _u3\n"
    "            _u3.disable_warnings(_u3.exceptions.InsecureRequestWarning)\n"
    "        except Exception:\n"
    "            pass\n"
    "        return False\n"
    "    if _v.lower() in ('true', '1', 'yes', 'on'):\n"
    "        return True\n"
    "    return _v\n"
    "\n"
    "_HA_VERIFY = _ha_verify()\n"
    "_HA_TIMEOUT = float(_os_tls.environ.get('HA_TIMEOUT', '15'))\n"
)

applied = []


def patch(path, anchor, helper_after, calls):
    """Insere le helper puis reecrit les appels requests listes."""
    global applied
    p = pathlib.Path(path)
    if not p.exists():
        print(f"[patch_ha_tls] ABSENT {path}", file=sys.stderr)
        return False
    t = p.read_text(encoding='utf-8')
    if MARKER in t:
        applied.append(f"{path} (deja fait)")
        return True
    if anchor not in t:
        print(f"[patch_ha_tls] ancre introuvable dans {path}", file=sys.stderr)
        return False
    t = t.replace(anchor, anchor + helper_after + HELPER, 1)
    for old, new in calls:
        if old not in t:
            print(f"[patch_ha_tls] appel introuvable dans {path}: {old[:60]}",
                  file=sys.stderr)
            return False
        t = t.replace(old, new, 1)
    p.write_text(t, encoding='utf-8')
    applied.append(path)
    return True


ok = True

# 1. Provider LLM homeassistant : verify + timeout + LANGUE
#
# La langue est indispensable : sans elle, le moteur d'intentions de Home
# Assistant repond en anglais. L'utilisateur entendait « Sorry, I couldn't
# understand that » prononce par la voix francaise de Piper. Avec
# "language": "fr", le meme moteur repond « Desole, je n'ai pas compris ».
ok &= patch(
    'core/providers/llm/homeassistant/homeassistant.py',
    'from core.providers.llm.base import LLMProviderBase',
    '\n\n',
    [(
        '        self.api_url = f"{self.base_url}/api/conversation/process"',
        '        self.api_url = f"{self.base_url}/api/conversation/process"\n'
        '        # Sans langue explicite, HA repond en anglais (voir docstring).\n'
        '        self.language = config.get("language") or _os_tls.environ.get("LANGUAGE", "fr")'
    ),
     (
        '            "conversation_id": session_id,  # 使用 session_id 作为 conversation_id\n'
        '        }',
        '            "conversation_id": session_id,  # 使用 session_id 作为 conversation_id\n'
        '            "language": self.language,\n'
        '        }'
    ),
     (
        'response = requests.post(self.api_url, json=payload, headers=headers)',
        'response = requests.post(\n'
        '            self.api_url, json=payload, headers=headers,\n'
        '            verify=_HA_VERIFY, timeout=_HA_TIMEOUT,\n'
        '        )'
    )],
)

# 2. Plugin hass_get_state
ok &= patch(
    'plugins_func/functions/hass_get_state.py',
    'import requests',
    '\n',
    [(
        'response = requests.get(url, headers=headers, timeout=5)',
        'response = requests.get(url, headers=headers, timeout=5, verify=_HA_VERIFY)'
    )],
)

# 3. Plugin hass_set_state
ok &= patch(
    'plugins_func/functions/hass_set_state.py',
    'import requests',
    '\n',
    [(
        'response = requests.post(url, headers=headers, json=data, timeout=5)',
        'response = requests.post(url, headers=headers, json=data, timeout=5, verify=_HA_VERIFY)'
    )],
)

if not ok:
    print('[patch_ha_tls] ECHEC : le code amont a change, patch a revoir',
          file=sys.stderr)
    sys.exit(1)

for a in applied:
    print(f'[patch_ha_tls] OK {a}')
print('[patch_ha_tls] OK - HTTPS Home Assistant + timeouts installes')
