#!/usr/bin/env python3
"""
Patch additif : resoudre une demande d'autorisation Claude Code SANS la voix.

POURQUOI
--------
patch_claude_notify.py installe deja tout le circuit de validation :
  POST /api/claude/notify                        (avec decision_id optionnel)
  GET  /api/claude/decision/{id}                 (poll cote PC)
  POST /api/claude/decision/{id}/cancel
Mais la seule facon de REPONDRE etait le plugin LLM `claude_decide`, qui exige
Intent=function_call. Or le deploiement du 2026-09-01 est passe en
LLM_BACKEND=ha, donc Intent=nointent : la validation vocale est desactivee.
Sans ce patch, une demande d'autorisation ne peut plus etre resolue du tout.

Ce patch ajoute la brique manquante, volontairement generique : n'importe quel
bouton peut resoudre la decision (Home Assistant, ecran tactile OpenHASP,
Flipper, raccourci telephone, favori navigateur). Aucune modification du
firmware ESP32, aucun ASR, aucun LLM.

ROUTES AJOUTEES
---------------
  POST /api/claude/decision/{id}/resolve      body {"decision": "allow"|"deny"}
  GET  /api/claude/decision/{id}/resolve?decision=allow
        Variante GET pour les clients embarques qui ne savent pas poster du
        JSON (OpenHASP, ESPHome, favori navigateur). Meme effet.
  GET  /api/claude/pending
        Ce qui est en attente, pour qu'un ecran puisse l'afficher.

`{id}` accepte le mot-cle `latest` : un bouton physique ne connait pas
l'identifiant de la decision, il resout donc la plus recente en attente.
C'est le mode d'emploi normal.

SECURITE
--------
Comme /api/claude/notify, ces routes ne sont pas authentifiees et le serveur
ecoute sur 0.0.0.0:8003. Quiconque est sur le LAN peut approuver une demande
Claude Code. C'est le meme niveau de confiance que l'existant, mais l'enjeu est
plus eleve (autoriser une commande). Pour durcir : definir CLAUDE_RESOLVE_TOKEN
dans l'environnement du conteneur ; les routes exigeront alors ce jeton, en
en-tete `X-Claude-Token` ou en parametre `token`.

S'applique pendant le build Docker, APRES patch_claude_notify.py.
Rollback : retirer ce fichier + les 2 lignes du Dockerfile, rebuild.
"""
import pathlib
import sys

p = pathlib.Path('core/http_server.py')
t = p.read_text(encoding='utf-8')

MARKER = "claude_resolve_handler"
if MARKER in t:
    print('[patch_resolve] deja applique, rien a faire')
    sys.exit(0)

# Le patch notify doit etre passe avant : on s'appuie sur son etat partage.
if "claude_decision_handler" not in t:
    print('[patch_resolve] ECHEC : patch_claude_notify.py doit etre applique avant',
          file=sys.stderr)
    sys.exit(1)

applied = []

# ── A. Handlers ──────────────────────────────────────────────────────
HANDLERS = (
    '    def _claude_check_token(self, request):\n'
    '        """Retourne None si autorise, sinon une reponse d\'erreur.\n'
    '\n'
    '        Sans CLAUDE_RESOLVE_TOKEN defini, tout le LAN peut resoudre :\n'
    '        c\'est le comportement historique de /api/claude/notify.\n'
    '        """\n'
    '        import os as _os_cr\n'
    '        expected = _os_cr.environ.get("CLAUDE_RESOLVE_TOKEN", "").strip()\n'
    '        if not expected:\n'
    '            return None\n'
    '        given = (request.headers.get("X-Claude-Token")\n'
    '                 or request.query.get("token", "")).strip()\n'
    '        if given == expected:\n'
    '            return None\n'
    '        return _make_json_response({"status": "forbidden"}, 403)\n'
    '\n'
    '    def _claude_resolve_id(self, raw_id):\n'
    '        """Resout le mot-cle `latest` vers la decision en attente."""\n'
    '        if raw_id in ("latest", "last", ""):\n'
    '            return CLAUDE_LATEST_DECISION_ID[0]\n'
    '        return raw_id\n'
    '\n'
    '    async def claude_resolve_handler(self, request):\n'
    '        """Resout une decision en attente : allow ou deny.\n'
    '\n'
    '        POST /api/claude/decision/{id}/resolve  body {"decision": "allow"}\n'
    '        GET  /api/claude/decision/{id}/resolve?decision=allow\n'
    '        {id} peut valoir `latest` : c\'est le cas d\'usage d\'un bouton.\n'
    '        """\n'
    '        denied = self._claude_check_token(request)\n'
    '        if denied is not None:\n'
    '            return denied\n'
    '\n'
    '        decision = (request.query.get("decision") or "").strip().lower()\n'
    '        if not decision and request.method == "POST":\n'
    '            try:\n'
    '                body = await request.json()\n'
    '                decision = str((body or {}).get("decision", "")).strip().lower()\n'
    '            except Exception:\n'
    '                decision = ""\n'
    '\n'
    '        # On accepte les formulations naturelles, pour que le bouton d\'un\n'
    '        # ecran ou d\'une automation HA n\'ait pas a connaitre notre jargon.\n'
    '        if decision in ("allow", "approve", "approuve", "oui", "ok", "valide", "yes", "1", "true"):\n'
    '            value = "allow"\n'
    '        elif decision in ("deny", "refuse", "non", "no", "0", "false", "cancel"):\n'
    '            value = "deny"\n'
    '        else:\n'
    '            return _make_json_response(\n'
    '                {"status": "error",\n'
    '                 "reason": "decision manquante ou invalide (allow|deny)"}, 400)\n'
    '\n'
    '        did = self._claude_resolve_id(request.match_info.get("decision_id", ""))\n'
    '        if not did or did not in CLAUDE_PENDING_DECISIONS:\n'
    '            return _make_json_response(\n'
    '                {"status": "no_pending",\n'
    '                 "reason": "aucune demande Claude en attente"}, 404)\n'
    '\n'
    '        CLAUDE_PENDING_DECISIONS[did]["decision"] = value\n'
    '        self.logger.bind(tag="claude").info(\n'
    '            f"decision {value} pour {did[:8]} via /resolve")\n'
    '\n'
    '        # Un bouton de dashboard Home Assistant ouvre simplement cette URL\n'
    '        # dans le navigateur. Lui renvoyer du JSON brut serait deroutant :\n'
    '        # on sert une page de confirmation quand le client veut du HTML.\n'
    '        if "text/html" in (request.headers.get("Accept") or ""):\n'
    '            libelle = "C\'est validé." if value == "allow" else "C\'est refusé."\n'
    '            couleur = "#1e8c75" if value == "allow" else "#c0392b"\n'
    '            page = (\n'
    '                "<!DOCTYPE html><html lang=fr><head><meta charset=utf-8>"\n'
    '                "<meta name=viewport content=\\"width=device-width,initial-scale=1\\">"\n'
    '                "<title>" + libelle + "</title><style>"\n'
    '                "html,body{height:100%;margin:0;font-family:-apple-system,"\n'
    '                "BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif}"\n'
    '                "body{display:flex;align-items:center;justify-content:center;"\n'
    '                "background:" + couleur + ";color:#fff;font-size:30px;"\n'
    '                "font-weight:650;text-align:center;padding:24px}"\n'
    '                "</style></head><body>" + libelle + "</body></html>"\n'
    '            )\n'
    '            return web.Response(text=page, content_type="text/html",\n'
    '                                charset="utf-8")\n'
    '\n'
    '        # Accuse de reception parle, pour que le geste soit confirme sans\n'
    '        # avoir a regarder un ecran.\n'
    '        try:\n'
    '            spoken = "C\'est validé." if value == "allow" else "C\'est refusé."\n'
    '            for conn in list(ACTIVE_CLAUDE_CONNS):\n'
    '                if getattr(conn, "tts", None) is None:\n'
    '                    continue\n'
    '                sid = _uuid_claude.uuid4().hex\n'
    '                conn.sentence_id = sid\n'
    '                conn.tts.tts_text_queue.put(TTSMessageDTO(\n'
    '                    sentence_id=sid, sentence_type=SentenceType.FIRST,\n'
    '                    content_type=ContentType.ACTION))\n'
    '                conn.tts.tts_text_queue.put(TTSMessageDTO(\n'
    '                    sentence_id=sid, sentence_type=SentenceType.MIDDLE,\n'
    '                    content_type=ContentType.TEXT, content_detail=spoken))\n'
    '                conn.tts.tts_text_queue.put(TTSMessageDTO(\n'
    '                    sentence_id=sid, sentence_type=SentenceType.LAST,\n'
    '                    content_type=ContentType.ACTION))\n'
    '                break\n'
    '        except Exception:\n'
    '            pass  # l\'accuse vocal est un confort, jamais un bloquant\n'
    '\n'
    '        return _make_json_response(\n'
    '            {"status": "ok", "decision": value, "decision_id": did}, 200)\n'
    '\n'
    '    async def claude_pending_handler(self, request):\n'
    '        """GET /api/claude/pending : ce qui attend une reponse.\n'
    '\n'
    '        Permet a un ecran (OpenHASP, dashboard HA) d\'afficher la demande\n'
    '        et de n\'allumer ses boutons que s\'il y a vraiment quelque chose.\n'
    '        """\n'
    '        did = CLAUDE_LATEST_DECISION_ID[0]\n'
    '        entry = CLAUDE_PENDING_DECISIONS.get(did) if did else None\n'
    '        if not did or entry is None:\n'
    '            return _make_json_response({"status": "idle", "pending": False}, 200)\n'
    '        return _make_json_response({\n'
    '            "status": "ok",\n'
    '            "pending": entry.get("decision") is None,\n'
    '            "decision_id": did,\n'
    '            "decision": entry.get("decision"),\n'
    '        }, 200)\n'
    '\n'
    '    async def claude_panel_handler(self, request):\n'
    '        """GET /api/claude/panel : page de validation autonome.\n'
    '\n'
    '        Deux gros boutons, rafraichie toute seule. Pensee pour un\n'
    '        telephone, un onglet epingle ou un ecran mural. Elle n\'est pas\n'
    '        prevue pour un iframe depuis Home Assistant : HA est servi en\n'
    '        https et ce serveur en http, le navigateur bloquerait le contenu\n'
    '        mixte. On l\'ouvre donc en page pleine.\n'
    '        """\n'
    '        import os as _os_panel\n'
    '        chemin = _os_panel.path.join("static", "claude_panel.html")\n'
    '        try:\n'
    '            with open(chemin, "r", encoding="utf-8") as fh:\n'
    '                return web.Response(text=fh.read(), content_type="text/html",\n'
    '                                    charset="utf-8")\n'
    '        except FileNotFoundError:\n'
    '            return _make_json_response(\n'
    '                {"status": "error", "reason": "panneau absent de l image"}, 404)\n'
    '\n'
)

ANCHOR = '    async def claude_decision_cancel_handler(self, request):'
if ANCHOR not in t:
    print('[patch_resolve] ECHEC : ancre des handlers introuvable', file=sys.stderr)
    sys.exit(1)
t = t.replace(ANCHOR, HANDLERS + ANCHOR, 1)
applied.append('handlers resolve + pending')

# ── B. Enregistrement des routes ─────────────────────────────────────
ROUTE_ANCHOR = ('                        web.post("/api/claude/decision/{decision_id}/cancel", '
                'self.claude_decision_cancel_handler),')
if ROUTE_ANCHOR not in t:
    print('[patch_resolve] ECHEC : ancre des routes introuvable', file=sys.stderr)
    sys.exit(1)
t = t.replace(
    ROUTE_ANCHOR,
    ROUTE_ANCHOR + '\n'
    '                        # Validation sans voix : n\'importe quel bouton\n'
    '                        web.post("/api/claude/decision/{decision_id}/resolve", self.claude_resolve_handler),\n'
    '                        web.get("/api/claude/decision/{decision_id}/resolve", self.claude_resolve_handler),\n'
    '                        web.get("/api/claude/pending", self.claude_pending_handler),\n'
    '                        web.get("/api/claude/panel", self.claude_panel_handler),',
    1,
)
applied.append('routes resolve (POST + GET) et pending')

# ── C. Enregistrer la decision meme si le boitier dort ────────────────
# Sans ca, /notify renvoie 503 AVANT d'enregistrer la demande : plus rien
# n'est validable, ni a la voix ni au bouton. Or le boitier se deconnecte
# des qu'il est au repos, donc le cas est frequent. On enregistre d'abord,
# on cherche un boitier ensuite : la demande reste validable par un bouton
# externe (Home Assistant, ecran, telephone) meme sans annonce vocale.
OLD_GUARD = (
    '        if target is None:\n'
    '            return _make_json_response(\n'
    '                {"status": "no_device", "reason": "no active Xiaozhi connection found"}, 503\n'
    '            )\n'
    '\n'
    '        # Enregistrer la decision en attente (avant de parler)\n'
    '        if decision_id:\n'
    '            CLAUDE_PENDING_DECISIONS[decision_id] = {"decision": None}\n'
    '            CLAUDE_LATEST_DECISION_ID[0] = decision_id\n'
)
NEW_GUARD = (
    '        # Enregistrer la demande AVANT de chercher un boitier : si le\n'
    '        # boitier dort, elle doit rester validable par un bouton externe.\n'
    '        if decision_id:\n'
    '            CLAUDE_PENDING_DECISIONS[decision_id] = {\n'
    '                "decision": None, "text": text[:240],\n'
    '            }\n'
    '            CLAUDE_LATEST_DECISION_ID[0] = decision_id\n'
    '\n'
    '        if target is None:\n'
    '            if decision_id:\n'
    '                return _make_json_response({\n'
    '                    "status": "pending_only",\n'
    '                    "spoken": False,\n'
    '                    "reason": "aucun boitier connecte ; validable par bouton",\n'
    '                    "decision_id": decision_id,\n'
    '                }, 200)\n'
    '            return _make_json_response(\n'
    '                {"status": "no_device", "reason": "no active Xiaozhi connection found"}, 503\n'
    '            )\n'
)
if OLD_GUARD in t:
    t = t.replace(OLD_GUARD, NEW_GUARD, 1)
    applied.append('demande enregistree meme boitier endormi')
else:
    print('[patch_resolve] ECHEC : garde no_device introuvable dans notify',
          file=sys.stderr)
    sys.exit(1)

# Exposer le texte de la demande dans /pending, pour qu'un ecran l'affiche.
t = t.replace(
    '            "decision": entry.get("decision"),\n'
    '        }, 200)\n',
    '            "decision": entry.get("decision"),\n'
    '            "text": entry.get("text", ""),\n'
    '        }, 200)\n',
    1,
)

p.write_text(t, encoding='utf-8')
for a in applied:
    print(f'[patch_resolve] OK {a}')
print('[patch_resolve] OK - validation par bouton disponible sur /resolve')
