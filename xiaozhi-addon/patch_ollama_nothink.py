#!/usr/bin/env python3
"""
Patch additif : Latence et verbosite du provider Ollama.

CONSTAT MESURE (PopLLM, 2026-09-01, modele qwen-ha:latest via /v1) :

  Chemin conversation (sans outils)
    defaut                  : 16 a 31 s, finish_reason=length, contenu VIDE
                              (le modele consomme tout son budget en raisonnement
                               interne, qu'Ollama n'expose pas sur /v1)
    reasoning_effort=none   : 0,42 a 0,98 s, reponse correcte

  Chemin commande (avec outils), 6 essais par reglage
    defaut                  : 1er token median 7,10 s, appel outil emis 6/6
    reasoning_effort=none   : 1er token median 0,97 s, appel outil emis 2/6

Conclusion : ce modele a BESOIN de son raisonnement pour emettre un appel de
fonction fiable. Desactiver partout rendrait le boitier rapide mais menteur
(il annonce l'action sans l'executer). Le patch separe donc les deux chemins :

  - response()                -> reasoning_effort=none  (gain x17, aucun risque)
  - response_with_functions() -> raisonnement conserve  (fiabilite 6/6)

Le chemin outils est pilotable par variable d'environnement si tu veux
arbitrer autrement :
    OLLAMA_TOOLS_REASONING=on   (defaut) fiable, ~7 s
    OLLAMA_TOOLS_REASONING=off            rapide, ~1 s, execution non garantie

Ajoute aussi max_tokens (anti-verbosite) et temperature, que le provider
d'origine ignorait totalement.

NOTE : ni `think:false`, ni `chat_template_kwargs`, ni le prefixe `/no_think`
n'ont d'effet sur l'endpoint /v1 d'Ollama (mesure du 2026-09-01). Le garde-fou
`/no_think` present dans le provider d'origine est donc inoperant, et il ne se
declenchait de toute facon jamais : il teste `model_name.startswith("qwen3")`,
or les modeles deployes s'appellent `qwen-ha:latest` et `gemma4:e4b`.

S'applique pendant le build Docker, apres patch_server.py.
Rollback : retirer ce fichier + les 2 lignes du Dockerfile, rebuild.
"""
import pathlib
import sys

p = pathlib.Path('core/providers/llm/ollama/ollama.py')
t = p.read_text(encoding='utf-8')

MARKER = "# NO-THINK / anti-verbosite (patch_ollama_nothink)"
if MARKER in t:
    print('[patch_ollama] deja applique, rien a faire')
    sys.exit(0)

applied = []

# ── A. Lire max_tokens / temperature / mode outils depuis la config ──
OLD_INIT = '''        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url", "http://localhost:11434")'''
NEW_INIT = '''        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url", "http://localhost:11434")
        ''' + MARKER + '''
        import os as _os_nt
        # Plafond de longueur : le provider d'origine n'en posait aucun, d'ou
        # des reponses vocales interminables. 96 tokens ~ 2 phrases parlees.
        self.max_tokens = int(config.get("max_tokens", 96) or 96)
        self.temperature = float(config.get("temperature", 0.3) or 0.3)
        # Raisonnement sur le chemin outils : conserve par defaut (fiabilite
        # d'appel mesuree 6/6 contre 2/6 sans). Cf. docstring du patch.
        self.tools_reasoning = _os_nt.environ.get(
            "OLLAMA_TOOLS_REASONING", "on"
        ).strip().lower() not in ("off", "0", "false", "no")'''
if OLD_INIT in t:
    t = t.replace(OLD_INIT, NEW_INIT, 1)
    applied.append('init(max_tokens/temperature/tools_reasoning)')

# ── B. Chemin conversation : raisonnement coupe ──────────────────────
OLD_CHAT = '''        responses = self.client.chat.completions.create(
            model=self.model_name, messages=dialogue, stream=True
        )'''
NEW_CHAT = '''        # Sans outils, rien a executer : le raisonnement ne sert qu'a faire
        # attendre. Mesure : 16-31 s (reponse vide) -> 0,4-1,0 s.
        responses = self.client.chat.completions.create(
            model=self.model_name,
            messages=dialogue,
            stream=True,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            extra_body={"reasoning_effort": "none"},
        )'''
if OLD_CHAT in t:
    t = t.replace(OLD_CHAT, NEW_CHAT, 1)
    applied.append('response() reasoning_effort=none')

# ── C. Chemin outils : raisonnement conserve (fiabilite) ─────────────
OLD_TOOLS = '''        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=dialogue,
            stream=True,
            tools=functions,
        )'''
NEW_TOOLS = '''        # Avec outils, le raisonnement est ce qui rend l'appel de fonction
        # fiable (6/6 avec, 2/6 sans). On le garde sauf demande explicite.
        _extra_nt = {} if self.tools_reasoning else {"reasoning_effort": "none"}
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=dialogue,
            stream=True,
            tools=functions,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            extra_body=_extra_nt,
        )'''
if OLD_TOOLS in t:
    t = t.replace(OLD_TOOLS, NEW_TOOLS, 1)
    applied.append('response_with_functions() max_tokens/temperature')

# ── D. Filtrer reasoning_content s'il fuit dans le flux ──────────────
# Certains modeles exposent leur raisonnement dans un champ separe. S'il
# arrivait au TTS, le boitier lirait le monologue interne a voix haute.
OLD_DELTA = '''                content = delta.content if hasattr(delta, "content") else ""'''
NEW_DELTA = '''                if getattr(delta, "reasoning_content", None):
                    continue  # monologue interne : ne jamais l'envoyer au TTS
                content = delta.content if hasattr(delta, "content") else ""'''
if OLD_DELTA in t:
    t = t.replace(OLD_DELTA, NEW_DELTA, 1)
    applied.append('response() filtre reasoning_content')

OLD_DELTA2 = '''                content = delta.content if hasattr(delta, "content") else None'''
NEW_DELTA2 = '''                if getattr(delta, "reasoning_content", None):
                    continue  # monologue interne : ne jamais l'envoyer au TTS
                content = delta.content if hasattr(delta, "content") else None'''
if OLD_DELTA2 in t:
    t = t.replace(OLD_DELTA2, NEW_DELTA2, 1)
    applied.append('response_with_functions() filtre reasoning_content')

# ── Garde-fou : echouer bruyamment si l'amont a change ───────────────
EXPECTED = 5
if len(applied) != EXPECTED:
    print(f'[patch_ollama] ECHEC : {len(applied)}/{EXPECTED} remplacements '
          f'appliques -> {applied}', file=sys.stderr)
    print('[patch_ollama] le fichier amont ollama.py a change, patch a revoir',
          file=sys.stderr)
    sys.exit(1)

p.write_text(t, encoding='utf-8')
for a in applied:
    print(f'[patch_ollama] OK {a}')
print('[patch_ollama] OK - latence conversation /17, verbosite plafonnee')
