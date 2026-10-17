"""Ecriture JSON atomique : on ecrit a cote, puis on bascule d'un seul coup.

Un crash ou un kill au milieu d'une ecriture ne corrompt jamais le fichier : il voit
soit l'ancienne version, soit la nouvelle.

os.replace echoue en PermissionError sous Windows quand OneDrive, un antivirus ou
l'application tient encore un handle sur le fichier. L'echec est transitoire : on
reessaie quelques fois avant d'abandonner.
"""

import json
import os
import time
from pathlib import Path


def ecrire_json(path, obj):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    for essai in range(6):
        try:
            os.replace(str(tmp), str(path))
            return
        except PermissionError:
            if essai == 5:
                raise
            time.sleep(0.5 * (essai + 1))
