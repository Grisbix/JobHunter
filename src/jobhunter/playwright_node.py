"""The Node.js runtime of Playwright, downloaded the first time a browser starts.

WHY. Playwright drives the browser through a Node.js program: `node.exe` (88 MB) and
its scripts, shipped inside the Python package. In the compiled application it was
the heaviest file of the installer (67 MB compressed), and most launches never open
a browser: the collection goes through the sites' APIs, only applying and a few
sources need one. Since 3.62 the installer leaves `node.exe` out
(tools/installer/build.py) and attaches it to the release as
`playwright-node-win64.zip`; this module fetches it the first time Playwright starts.

HOW.
- The build writes `jobhunter_node.json` next to the compiled code: the zip's URL
  (the release of this very version), its SHA-256 and that of node.exe. The download
  is checked against both: a file that does not match is refused, never run.
- `node.exe` is extracted to `%LOCALAPPDATA%/JobHunter/node/<sha12>/`, outside the
  program's folder (replaced at each update): the next versions shipping the same
  Node reuse it without downloading again.
- `installer()` (jobhunter.frozen) wraps Playwright's `compute_driver_executable`
  when its transport module is imported, so that nothing is downloaded until a
  browser really starts, and importing Playwright costs nothing more.
- `JOBHUNTER_NODE_ZIP` gives a local zip instead of the download (the installer's
  CI tests the application without a release).

Outside the compiled application (Python installed), nothing changes: Playwright
uses the `node.exe` of its own package.
"""

import hashlib
import importlib.abc
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ZIP = "playwright-node-win64.zip"
MANIFESTE = "jobhunter_node.json"
MODULE = "playwright._impl._transport"


def _interne() -> Path:
    return Path(getattr(sys, "_MEIPASS", "."))


def manifeste() -> dict | None:
    """What the build wrote ({url, sha256, node}), or None when node.exe is shipped."""
    if (_interne() / "playwright" / "driver" / "node.exe").is_file():
        return None
    try:
        m = json.loads((_interne() / MANIFESTE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return m if isinstance(m, dict) and all(m.get(k) for k in ("url", "sha256", "node")) else None


def cible(sha: str) -> Path:
    """Where the node.exe of SHA-256 `sha` is kept, outside the program's folder."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "JobHunter" / "node" / sha[:12] / "node.exe"


def _telecharger(url: str) -> bytes:
    from jobhunter.programs.update import _get  # same download, same « Téléchargement : 40 % »

    print("Premier navigateur : téléchargement de Node.js (~30 Mo, une seule fois)", flush=True)
    return _get(url, 120)


def assurer(m: dict) -> Path:
    """The path of node.exe, downloaded and checked first if needed.

    Raises:
        RuntimeError: download impossible, or a file that does not match the build.
    """
    exe = cible(m["node"])
    if exe.is_file():
        return exe
    local = os.environ.get("JOBHUNTER_NODE_ZIP")
    try:
        donnees = Path(local).read_bytes() if local else _telecharger(m["url"])
    except Exception as e:  # noqa: BLE001  — offline, proxy, 404: one clear message
        raise RuntimeError(
            f"Node.js, nécessaire au navigateur, n'a pas pu être téléchargé ({e}). "
            f"Vérifier la connexion, puis réessayer. Adresse : {m['url']}"
        ) from e
    node = b""
    if hashlib.sha256(donnees).hexdigest() == m["sha256"]:
        with zipfile.ZipFile(io.BytesIO(donnees)) as z:
            node = z.read("node.exe")
    if hashlib.sha256(node).hexdigest() != m["node"]:
        raise RuntimeError(
            f"Node.js téléchargé refusé : empreinte différente de celle attendue ({m['url']})."
        )
    exe.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=exe.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(node)
        os.replace(tmp, exe)  # atomic: a half-written node.exe never has the final name
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return exe


def _envelopper(module, m: dict) -> None:
    origine = module.compute_driver_executable

    def compute_driver_executable():
        if "PLAYWRIGHT_NODEJS_PATH" not in os.environ:
            os.environ["PLAYWRIGHT_NODEJS_PATH"] = str(assurer(m))
        return origine()

    module.compute_driver_executable = compute_driver_executable


class _Crochet(importlib.abc.MetaPathFinder):
    """Wraps the transport module right after Playwright loads it."""

    def __init__(self, m: dict):
        self.m = m

    def find_spec(self, nom, chemin=None, cible=None):
        if nom != MODULE:
            return None
        sys.meta_path.remove(self)
        spec = None
        try:
            for f in sys.meta_path:  # the usual finders, in their order
                spec = getattr(f, "find_spec", lambda *a: None)(nom, chemin, cible)
                if spec is not None:
                    break
        finally:
            sys.meta_path.insert(0, self)
        if spec is None or spec.loader is None:
            return spec
        executer, m = spec.loader.exec_module, self.m

        def exec_module(module):
            executer(module)
            _envelopper(module, m)

        # One loader per module (PathFinder and PyInstaller alike): only this one changes.
        spec.loader.exec_module = exec_module
        return spec


def installer() -> bool:
    """In the compiled application without node.exe: fetch it when a browser starts.

    Returns:
        True when the hook is in place.
    """
    m = manifeste()
    if m is None or "PLAYWRIGHT_NODEJS_PATH" in os.environ:
        return False
    if MODULE in sys.modules:
        _envelopper(sys.modules[MODULE], m)
    else:
        sys.meta_path.insert(0, _Crochet(m))
    return True
