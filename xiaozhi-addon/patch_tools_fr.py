#!/usr/bin/env python3
"""
Patch additif : reponse apres un appel d'outil, et outils Home Assistant en
francais.

Constat du 2026-10-07 (journaux du matin + mesures sur PopLLM, modele qwen-ha) :

  A. Toute demande passant par un outil (« ferme le volet du bureau », « est-ce
     que le volet est ouvert ? ») restait sans reponse. Apres le resultat de
     l'outil, le modele, raisonnement actif, range sa phrase finale dans le
     canal de reflexion : le contenu reste vide et le boitier ne dit rien
     (3 essais sur 3). Raisonnement coupe pour cette seule etape, la phrase
     arrive dans le contenu (3 sur 3, 1,9 s). Le raisonnement reste actif pour
     decider de l'appel, ou il conditionne la fiabilite (patch_ollama_nothink).
  B. Les resultats et messages d'erreur des outils Home Assistant, et l'en-tete
     de la liste des appareils ajoutee au prompt, etaient en chinois. Une erreur
     est prononcee telle quelle (le filtre CJK la remplace alors par « Desole,
     je me suis trompe de langue ») et les resultats poussent le modele vers le
     chinois. Ils sont traduits ; les descriptions d'outils, lues par le modele
     mais jamais prononcees, ne sont pas touchees.

S'applique en fin de build, apres patch_ollama_nothink.py.
Rollback : retirer ce fichier + ses lignes du Dockerfile, rebuild.
"""
import pathlib
import sys


def patch(path, old, new, label, required=True):
    p = pathlib.Path(path)
    if not p.exists():
        if required:
            print(f'[patch_tools_fr] ECHEC : {path} absent', file=sys.stderr)
            sys.exit(1)
        print(f'[patch_tools_fr] ignore ({path} absent) : {label}')
        return
    t = p.read_text(encoding='utf-8')
    if new in t:
        print(f'[patch_tools_fr] deja applique : {label}')
        return
    if old not in t:
        if required:
            print(f'[patch_tools_fr] ECHEC : ancre introuvable pour {label}',
                  file=sys.stderr)
            sys.exit(1)
        print(f'[patch_tools_fr] ignore (ancre absente) : {label}')
        return
    p.write_text(t.replace(old, new), encoding='utf-8')
    print(f'[patch_tools_fr] OK {label}')


# ── A. Reponse apres un resultat d'outil : raisonnement coupe ─────────────
patch(
    'core/providers/llm/ollama/ollama.py',
    '        _extra_nt = {} if self.tools_reasoning else {"reasoning_effort": "none"}\n',
    '        _extra_nt = {} if self.tools_reasoning else {"reasoning_effort": "none"}\n'
    '        # Apres un resultat d\'outil il ne reste qu\'a formuler la reponse. Avec\n'
    '        # le raisonnement actif, qwen-ha range cette phrase dans le canal de\n'
    '        # reflexion et le contenu reste vide : boitier muet (mesure 2026-10-07).\n'
    '        if dialogue and dialogue[-1].get("role") == "tool":\n'
    '            _extra_nt = {"reasoning_effort": "none"}\n',
    'reponse apres outil sans raisonnement (ollama.py)',
)

# ── B. Textes des outils Home Assistant en francais ───────────────────────
TRADUCTIONS = {
    'plugins_func/functions/hass_get_state.py': [
        ('"请求超时"', '"Home Assistant ne répond pas."'),
        ('f"执行Home Assistant操作失败"', '"La lecture de l\'état dans Home Assistant a échoué."'),
        ('"设备状态:"', '"État : "'),
        ('"正在播放的是:"', '"En lecture : "'),
        ('"音量是:"', '"Volume : "'),
        ('"色温是:"', '"Température de couleur : "'),
        ('"rgb颜色是:"', '"Couleur RVB : "'),
        ('"亮度是:"', '"Luminosité : "'),
        ('f"切换失败，错误码: {response.status_code}"',
         'f"Lecture de l\'état impossible, code d\'erreur {response.status_code}."'),
    ],
    'plugins_func/functions/hass_set_state.py': [
        ('"请求超时"', '"Home Assistant ne répond pas."'),
        ('f"执行Home Assistant操作失败"', '"La commande Home Assistant a échoué."'),
        ('"执行失败，错误的设备id"', '"Échec : appareil inconnu."'),
        ('"设备已打开"', '"Appareil allumé ou ouvert."'),
        ('"设备已关闭"', '"Appareil éteint ou fermé."'),
        ('"灯光已调亮"', '"Lumière augmentée."'),
        ('"灯光已调暗"', '"Lumière baissée."'),
        ("f\"亮度已调整到{state['input']}\"", "f\"Luminosité réglée à {state['input']}.\""),
        ("f\"颜色已调整到{state['rgb_color']}\"", "f\"Couleur réglée à {state['rgb_color']}.\""),
        ("f\"色温已调整到{state['input']}K\"", "f\"Température de couleur réglée à {state['input']} K.\""),
        ('"音量已调大"', '"Volume augmenté."'),
        ('"音量已调小"', '"Volume baissé."'),
        ("f\"音量已调整到{state['input']}\"", "f\"Volume réglé à {state['input']}.\""),
        ('f"设备已静音"', '"Son coupé."'),
        ('f"设备已暂停"', '"Mis en pause."'),
        ('f"设备已继续"', '"Lecture reprise."'),
        ("f\"{domain} {state['type']}功能尚未支持\"",
         "f\"Action {state['type']} non prise en charge pour {domain}.\""),
        ('f"设置失败，错误码: {response.status_code}"',
         'f"La commande a échoué, code d\'erreur {response.status_code}."'),
    ],
    'plugins_func/functions/hass_play_music.py': [
        ('f"处理音乐意图错误: {e}"', 'f"Erreur de lecture musicale : {e}"'),
        ('f"正在播放{media_content_id}的音乐"', 'f"Lecture de {media_content_id} lancée."'),
        ('f"音乐播放失败，错误码: {response.status_code}"',
         'f"La lecture musicale a échoué, code d\'erreur {response.status_code}."'),
    ],
    'plugins_func/functions/hass_init.py': [
        ('"\\n下面是我家智能设备列表（位置，设备名，entity_id），可以通过homeassistant控制\\n"',
         '"\\nVoici les appareils de la maison (pièce, nom, entity_id), pilotables par Home Assistant :\\n"'),
    ],
}
for fichier, paires in TRADUCTIONS.items():
    for old, new in paires:
        patch(fichier, old, new, f'{fichier.rsplit("/", 1)[1]} : {new[:40]}', required=False)

print('[patch_tools_fr] OK - reponses apres outil et outils HA en francais')
