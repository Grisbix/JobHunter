"""Stockage : les fichiers de donnees, et la seule facon sure de les ecrire.

    atomique   ecriture tmp + os.replace, reessais sous Windows
    verrou     exclusion entre processus, par fichier .lock
    file       apply_queue.json + descriptions.json   (ancien Scripts/queue_io.py)
    suivi      suivi.json, les candidatures            (ancien Scripts/suivi_io.py)

Dependances a sens unique : file et suivi s'appuient sur atomique et verrou, jamais
l'inverse. L'ancien cycle jutil <-> queue_io venait de ce que jutil.jwrite, garde-fou
de la file, appelait queue_io, qui importait jutil.
"""
