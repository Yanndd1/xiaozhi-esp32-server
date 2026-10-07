#!/usr/bin/env python3
"""
Patch additif : normalisation du niveau audio avant transcription.

MESURE (enregistrement reel du 2026-09-01, phrase de 4,14 s, 16 kHz mono) :
    crete ............ -22,0 dBFS   (ideal : -6 a -12)
    parole (RMS) ..... -35,9 dBFS   (ideal : -20 a -26)
    saturation ....... 0 echantillon
    bruit de fond .... silence numerique exact
Le signal est donc PROPRE mais environ 15 dB trop faible. Le micro unique de
l'ESP32-S3 n'a pas de controle automatique de gain, et la suppression de bruit
WebRTC met les silences a zero absolu : il n'y a aucun risque a amplifier.

Whisper medium transcrit correctement a ce niveau quand on parle de pres, mais
une phrase plus lointaine ou plus douce passe sous son seuil de tolerance, ce
qui explique les transcriptions absurdes observees jusqu'ici
(« Bonne-moi le billion d'energie », « et non mais je me l'usent pour le car »).

Ce patch remonte le niveau juste avant de nourrir le modele. Il agit sur RMS
avec une garde de crete, plutot qu'en normalisation de crete simple : un seul
claquement de langue suffirait sinon a annuler tout le gain.

REGLAGES (variables d'environnement)
    ASR_AUTO_GAIN        on | off   (defaut on)
    ASR_GAIN_TARGET_DBFS cible RMS de la parole (defaut -23)
    ASR_GAIN_MAX_DB      gain maximal applique  (defaut 25)

S'applique pendant le build Docker, apres patch_server.py.
Rollback : retirer ce fichier + les 2 lignes du Dockerfile, rebuild.
"""
import pathlib
import sys

p = pathlib.Path('core/providers/asr/sherpa_onnx_local.py')
t = p.read_text(encoding='utf-8')

MARKER = "# GAIN ASR (patch_asr_gain)"
if MARKER in t:
    print('[patch_gain] deja applique, rien a faire')
    sys.exit(0)

OLD = ('            samples_float32 = samples_float32 / 32768\n'
       '            return samples_float32, f.getframerate()')

NEW = ('            samples_float32 = samples_float32 / 32768\n'
       '            ' + MARKER + '\n'
       '            samples_float32 = _asr_normaliser(samples_float32)\n'
       '            return samples_float32, f.getframerate()')

if OLD not in t:
    print('[patch_gain] ECHEC : read_wave a change en amont', file=sys.stderr)
    sys.exit(1)
t = t.replace(OLD, NEW, 1)

HELPER = '''

''' + MARKER + '''
import os as _os_gain
import math as _math_gain


def _asr_normaliser(samples):
    """Remonte le niveau de parole vers une cible RMS, sans jamais saturer.

    Le micro du boitier delivre environ 15 dB sous le niveau utile et n'a pas
    d'AGC. On mesure le RMS des seuls echantillons non nuls : la suppression de
    bruit ayant mis les silences a zero, les inclure ecraserait la mesure et on
    sous-amplifierait les phrases entrecoupees de pauses.
    """
    if _os_gain.environ.get("ASR_AUTO_GAIN", "on").strip().lower() in (
        "off", "0", "false", "no"
    ):
        return samples
    try:
        import numpy as _np_gain

        actifs = samples[_np_gain.abs(samples) > 1e-4]
        if actifs.size < 160:  # moins de 10 ms de parole : rien a normaliser
            return samples
        rms = float(_np_gain.sqrt(_np_gain.mean(actifs.astype(_np_gain.float64) ** 2)))
        if rms <= 0:
            return samples

        cible_db = float(_os_gain.environ.get("ASR_GAIN_TARGET_DBFS", "-23"))
        gain_max_db = float(_os_gain.environ.get("ASR_GAIN_MAX_DB", "25"))
        gain = (10.0 ** (cible_db / 20.0)) / rms
        gain = min(gain, 10.0 ** (gain_max_db / 20.0))
        if gain <= 1.0:
            return samples  # deja assez fort, on ne baisse jamais

        # Garde de crete : on plafonne pour rester sous -1 dBFS.
        crete = float(_np_gain.max(_np_gain.abs(samples)))
        if crete > 0:
            gain = min(gain, 0.891 / crete)
        if gain <= 1.0:
            return samples
        return (samples * gain).astype(_np_gain.float32)
    except Exception:
        return samples  # jamais bloquer la transcription pour un probleme de gain
'''

# Le helper doit exister avant la classe qui l'utilise : on l'insere apres
# le bloc d'imports, repere par la definition de TAG.
if 'TAG = __name__' not in t:
    print('[patch_gain] ECHEC : ancre TAG introuvable', file=sys.stderr)
    sys.exit(1)
t = t.replace('TAG = __name__', 'TAG = __name__' + HELPER, 1)

p.write_text(t, encoding='utf-8')
print('[patch_gain] OK - normalisation du niveau installee dans read_wave')
