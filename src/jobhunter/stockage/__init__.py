"""Storage: the data files, and the only safe way to write them.

    atomique   tmp write + os.replace, retries under Windows
    verrou     exclusion between processes, through a .lock file
    file       apply_queue.json + descriptions.json   (formerly Scripts/queue_io.py)
    suivi      suivi.json, the applications            (formerly Scripts/suivi_io.py)

One-way dependencies: file and suivi rely on atomique and verrou, never
the reverse. The old jutil <-> queue_io cycle came from jutil.jwrite, the queue's
safeguard, calling queue_io, which imported jutil.
"""
