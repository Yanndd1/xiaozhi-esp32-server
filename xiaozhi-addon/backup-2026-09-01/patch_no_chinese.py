#!/usr/bin/env python3
"""
Patch additif — Filtre anti-chinois sur la sortie LLM/TTS.

Le LLM Ollama (gemma/qwen) bascule parfois en chinois sur des entrees
ambigues. Pour garantir que le device Xiaozhi ne prononcera JAMAIS de
caracteres CJK, ce patch intercepte `to_tts_stream` (le point de passage
obligatoire avant la generation audio Piper) et :
  - si le texte contient quelques CJK isoles : les supprime
  - si le texte est majoritairement CJK : remplace par un fallback francais

IMPORTANT — les accents sont obligatoires dans cette phrase. Piper
phonemise litteralement ce qu'on lui donne : "Desole ... francais" sans
accents se prononce "deuh-zole ... fran-ka-is". Bug entendu et corrige
le 2026-09-01. Meme regle pour toute chaine francaise de ce depot.

S'applique pendant le build Docker, apres patch_server.py et
patch_claude_notify.py. Aucun fichier source local Windows modifie.

Rollback : retirer ce fichier + ligne Dockerfile, rebuild.
"""
import pathlib

p = pathlib.Path('core/providers/tts/base.py')
t = p.read_text(encoding='utf-8')

# A. Marqueur d'idempotence + injection du filtre au debut de to_tts_stream
MARKER = "# NO-CHINESE filter (Claude Buddy integration)"
if MARKER not in t:
    t = t.replace(
        '    def to_tts_stream(self, text, opus_handler: Callable[[bytes], None] = None) -> None:',
        '    def to_tts_stream(self, text, opus_handler: Callable[[bytes], None] = None) -> None:\n'
        '        ' + MARKER + '\n'
        '        if text:\n'
        '            import re as _re_no_zh\n'
        '            _cjk = _re_no_zh.findall(r"[\\u4e00-\\u9fff\\u3400-\\u4dbf]", text)\n'
        '            if _cjk:\n'
        '                _ratio = len(_cjk) / max(len(text), 1)\n'
        '                if _ratio > 0.05:\n'
        '                    text = "Désolé, je me suis trompé de langue."\n'
        '                else:\n'
        '                    text = _re_no_zh.sub(r"[\\u4e00-\\u9fff\\u3400-\\u4dbf]", "", text).strip()\n'
        '                    if not text:\n'
        '                        return  # rien a dire apres nettoyage\n',
        1,
    )

# B. Securite supplementaire : filtre aussi to_tts (chemin non-stream, si jamais utilise)
if "def to_tts(self, text):" in t and t.count(MARKER) < 2:
    t = t.replace(
        '    def to_tts(self, text):',
        '    def to_tts(self, text):\n'
        '        ' + MARKER + ' (non-stream path)\n'
        '        if text:\n'
        '            import re as _re_no_zh2\n'
        '            _cjk = _re_no_zh2.findall(r"[\\u4e00-\\u9fff\\u3400-\\u4dbf]", text)\n'
        '            if _cjk:\n'
        '                if len(_cjk) / max(len(text), 1) > 0.05:\n'
        '                    text = "Désolé, je me suis trompé de langue."\n'
        '                else:\n'
        '                    text = _re_no_zh2.sub(r"[\\u4e00-\\u9fff\\u3400-\\u4dbf]", "", text).strip()\n'
        '                    if not text:\n'
        '                        return None\n',
        1,
    )

p.write_text(t, encoding='utf-8')
print('[patch_no_chinese] base.py: filtre CJK installe sur to_tts_stream + to_tts')
