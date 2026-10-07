#!/usr/bin/env python3
"""
Patch additif et isole — integration Claude Code <-> Xiaozhi.

S'execute pendant le BUILD Docker, apres patch_server.py. Ne modifie aucun
fichier existant du repo source local ; modifie uniquement le code clone dans
l'image Docker, comme patch_server.py.

Fonctions ajoutees au serveur Xiaozhi (port 8003) :
  - POST /api/claude/notify            : fait prononcer un texte (TTS Piper).
                                         Body : {text, device_id?, decision_id?}
                                         Si decision_id present, enregistre une
                                         "decision en attente" que le plugin LLM
                                         claude_decide pourra resoudre a la voix.
  - GET  /api/claude/decision/{id}     : poll de la decision (allow|deny|null).
                                         Consomme la decision une fois lue.
  - POST /api/claude/decision/{id}/cancel : annule une decision en attente
                                         (utilise quand le Flipper a repondu en
                                         premier).

Etat partage (dans core/connection.py) :
  - ACTIVE_CLAUDE_CONNS       : set des connexions device actives
  - CLAUDE_PENDING_DECISIONS  : {decision_id: {"decision": None|"allow"|"deny"}}
  - CLAUDE_LATEST_DECISION_ID : [dernier id en attente] (pour le plugin vocal)

Rollback : supprimer ce fichier + sa ligne dans Dockerfile.popllm, rebuild.
"""
import pathlib

# ── Patch A : etat partage dans connection.py ─────────────────────────────
p = pathlib.Path('core/connection.py')
t = p.read_text(encoding='utf-8')

# A.1 — Registry connexions + decisions en attente (apres TAG = __name__)
if "ACTIVE_CLAUDE_CONNS" not in t:
    t = t.replace(
        'TAG = __name__',
        'TAG = __name__\n'
        '\n'
        '# === Claude Code integration : etat partage ===\n'
        'ACTIVE_CLAUDE_CONNS = set()  # connexions device actives\n'
        'CLAUDE_PENDING_DECISIONS = {}  # decision_id -> {"decision": None|"allow"|"deny"}\n'
        'CLAUDE_LATEST_DECISION_ID = [None]  # conteneur mutable : dernier id en attente\n',
        1,
    )

# A.2 — Enregistrer la connexion juste apres que device_id soit defini
if "ACTIVE_CLAUDE_CONNS.add(self)" not in t:
    t = t.replace(
        '            self.device_id = self.headers.get("device-id", None)',
        '            self.device_id = self.headers.get("device-id", None)\n'
        '            # Claude Code integration : enregistrer cette connexion\n'
        '            ACTIVE_CLAUDE_CONNS.add(self)',
        1,
    )

p.write_text(t, encoding='utf-8')
print('[patch_claude] connection.py: etat partage (conns + decisions) installe')


# ── Patch B : routes HTTP dans http_server.py ─────────────────────────────
p = pathlib.Path('core/http_server.py')
t = p.read_text(encoding='utf-8')

# B.1 — Imports supplementaires
if "from core.connection import ACTIVE_CLAUDE_CONNS" not in t:
    t = t.replace(
        'from core.api.vision_handler import VisionHandler',
        'from core.api.vision_handler import VisionHandler\n'
        'from core.connection import (\n'
        '    ACTIVE_CLAUDE_CONNS,\n'
        '    CLAUDE_PENDING_DECISIONS,\n'
        '    CLAUDE_LATEST_DECISION_ID,\n'
        ')\n'
        'from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType\n'
        'import json as _json_claude\n'
        'import uuid as _uuid_claude',
    )

# B.2 — Handlers (notify + decision poll + decision cancel)
if "claude_notify_handler" not in t:
    t = t.replace(
        '    def _get_websocket_url(self, local_ip: str, port: int) -> str:',
        '    async def claude_notify_handler(self, request):\n'
        '        """POST /api/claude/notify : fait prononcer un texte par le device.\n'
        '\n'
        '        Body : {"text": str, "device_id"?: str, "decision_id"?: str}\n'
        '        Si decision_id present, enregistre une decision en attente.\n'
        '        """\n'
        '        try:\n'
        '            body = await request.json()\n'
        '        except Exception as e:\n'
        '            return _make_json_response({"status": "error", "reason": f"bad json: {e}"}, 400)\n'
        '        text = (body or {}).get("text", "").strip()\n'
        '        device_id = (body or {}).get("device_id")\n'
        '        decision_id = (body or {}).get("decision_id")\n'
        '        if not text:\n'
        '            return _make_json_response({"status": "error", "reason": "empty text"}, 400)\n'
        '\n'
        '        target = None\n'
        '        for conn in list(ACTIVE_CLAUDE_CONNS):\n'
        '            if device_id and conn.device_id != device_id:\n'
        '                continue\n'
        '            if getattr(conn, "tts", None) is None:\n'
        '                continue\n'
        '            target = conn\n'
        '            break\n'
        '        if target is None:\n'
        '            return _make_json_response(\n'
        '                {"status": "no_device", "reason": "no active Xiaozhi connection found"}, 503\n'
        '            )\n'
        '\n'
        '        # Enregistrer la decision en attente (avant de parler)\n'
        '        if decision_id:\n'
        '            CLAUDE_PENDING_DECISIONS[decision_id] = {"decision": None}\n'
        '            CLAUDE_LATEST_DECISION_ID[0] = decision_id\n'
        '\n'
        '        # Sequence TTS FIRST -> MIDDLE(text) -> LAST\n'
        '        try:\n'
        '            sid = _uuid_claude.uuid4().hex\n'
        '            target.sentence_id = sid\n'
        '            target.tts.tts_text_queue.put(TTSMessageDTO(\n'
        '                sentence_id=sid, sentence_type=SentenceType.FIRST,\n'
        '                content_type=ContentType.ACTION,\n'
        '            ))\n'
        '            target.tts.tts_text_queue.put(TTSMessageDTO(\n'
        '                sentence_id=sid, sentence_type=SentenceType.MIDDLE,\n'
        '                content_type=ContentType.TEXT, content_detail=text,\n'
        '            ))\n'
        '            target.tts.tts_text_queue.put(TTSMessageDTO(\n'
        '                sentence_id=sid, sentence_type=SentenceType.LAST,\n'
        '                content_type=ContentType.ACTION,\n'
        '            ))\n'
        '        except Exception as e:\n'
        '            return _make_json_response(\n'
        '                {"status": "error", "reason": f"tts queue push failed: {e}"}, 500\n'
        '            )\n'
        '\n'
        '        return _make_json_response({\n'
        '            "status": "ok",\n'
        '            "device_id": target.device_id,\n'
        '            "session_id": getattr(target, "session_id", None),\n'
        '            "decision_id": decision_id,\n'
        '            "text": text[:80],\n'
        '        }, 200)\n'
        '\n'
        '    async def claude_decision_handler(self, request):\n'
        '        """GET /api/claude/decision/{id} : poll de la decision (consomme une fois resolue)."""\n'
        '        did = request.match_info.get("decision_id", "")\n'
        '        entry = CLAUDE_PENDING_DECISIONS.get(did)\n'
        '        if entry is None:\n'
        '            return _make_json_response({"status": "not_found", "decision": None}, 200)\n'
        '        decision = entry.get("decision")\n'
        '        if decision is not None:\n'
        '            CLAUDE_PENDING_DECISIONS.pop(did, None)\n'
        '            if CLAUDE_LATEST_DECISION_ID[0] == did:\n'
        '                CLAUDE_LATEST_DECISION_ID[0] = None\n'
        '        return _make_json_response({"status": "ok", "decision": decision}, 200)\n'
        '\n'
        '    async def claude_decision_cancel_handler(self, request):\n'
        '        """POST /api/claude/decision/{id}/cancel : annule une decision en attente."""\n'
        '        did = request.match_info.get("decision_id", "")\n'
        '        CLAUDE_PENDING_DECISIONS.pop(did, None)\n'
        '        if CLAUDE_LATEST_DECISION_ID[0] == did:\n'
        '            CLAUDE_LATEST_DECISION_ID[0] = None\n'
        '        return _make_json_response({"status": "ok"}, 200)\n'
        '\n'
        '    def _get_websocket_url(self, local_ip: str, port: int) -> str:',
    )

# B.3 — Helper de reponse JSON (avant la classe)
if "def _make_json_response" not in t:
    t = t.replace(
        'TAG = __name__',
        'TAG = __name__\n'
        '\n'
        'def _make_json_response(data, status=200):\n'
        '    return web.json_response(data, status=status, headers={"Access-Control-Allow-Origin": "*"})\n',
        1,
    )

# B.4 — Enregistrer les routes
if 'web.post("/api/claude/notify"' not in t:
    t = t.replace(
        '                # 添加路由\n'
        '                app.add_routes(\n'
        '                    [\n'
        '                        web.get("/mcp/vision/explain", self.vision_handler.handle_get),\n'
        '                        web.post(\n'
        '                            "/mcp/vision/explain", self.vision_handler.handle_post\n'
        '                        ),\n'
        '                        web.options(\n'
        '                            "/mcp/vision/explain", self.vision_handler.handle_options\n'
        '                        ),',
        '                # 添加路由\n'
        '                app.add_routes(\n'
        '                    [\n'
        '                        web.get("/mcp/vision/explain", self.vision_handler.handle_get),\n'
        '                        web.post(\n'
        '                            "/mcp/vision/explain", self.vision_handler.handle_post\n'
        '                        ),\n'
        '                        web.options(\n'
        '                            "/mcp/vision/explain", self.vision_handler.handle_options\n'
        '                        ),\n'
        '                        # Claude Code integration\n'
        '                        web.post("/api/claude/notify", self.claude_notify_handler),\n'
        '                        web.options("/api/claude/notify", lambda r: _make_json_response({"ok": True})),\n'
        '                        web.get("/api/claude/decision/{decision_id}", self.claude_decision_handler),\n'
        '                        web.post("/api/claude/decision/{decision_id}/cancel", self.claude_decision_cancel_handler),',
    )

p.write_text(t, encoding='utf-8')
print('[patch_claude] http_server.py: routes notify + decision installees')
print('[patch_claude] OK — Claude Code integration (notif + validation vocale) prete')
