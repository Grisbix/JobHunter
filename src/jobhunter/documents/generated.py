"""Never overwrite a document the user retouched by hand.

A CV or a letter of `By_offer` is generated, then often retouched: in Word, or in the
application (Mes CV → Enregistrer). Regenerating it (`jobhunter regenerate`, a new
template, `documents --url`) used to overwrite that work without a word.

Each folder keeps the fingerprint of the text it last GENERATED for each file
(`.jobhunter_generes.json`). Before writing again:

- the file's text is still the generated one → replaced, as before;
- it changed since → the user's version stays, the new one goes to `_a_comparer/` next to
  it, and the log says how many paragraphs differ;
- no fingerprint (a document from before 3.7) → replaced, as before, and fingerprinted.

Programs that edit documents in place on purpose (`refresh_letters`: date, order,
recipient) call `noter()` afterwards: their change is not a retouch.
"""

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from jobhunter import log as _journal

_log = _journal.journal(__name__)

REGISTRE = ".jobhunter_generes.json"
A_COMPARER = "_a_comparer"


def _texte(path: Path) -> list[str]:
    from docx import Document

    return [p.text for p in Document(str(path)).paragraphs]


def _empreinte(paragraphes: list[str]) -> str:
    return hashlib.sha256("\n".join(paragraphes).encode("utf-8")).hexdigest()


def _lire(dossier: Path) -> dict[str, str]:
    try:
        d = json.loads((dossier / REGISTRE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def noter(path: Path) -> None:
    """Records `path`'s current text as generated (not a retouch)."""
    try:
        empreinte = _empreinte(_texte(path))
    except Exception:  # an unreadable document: nothing to protect it against
        return
    reg = _lire(path.parent)
    reg[path.name] = empreinte
    tmp = path.parent / (REGISTRE + ".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=0), encoding="utf-8")
    tmp.replace(path.parent / REGISTRE)


def retouche(path: Path) -> bool:
    """True if `path` was generated, then changed by someone else since."""
    if not path.exists():
        return False
    connue = _lire(path.parent).get(path.name)
    if connue is None:
        return False
    try:
        return _empreinte(_texte(path)) != connue
    except Exception:  # unreadable (open in Word, damaged): do not overwrite it either
        return True


def ecart(a: Path, b: Path) -> int:
    """Number of paragraphs added, removed or changed from `a` to `b`."""
    sm = difflib.SequenceMatcher(a=_texte(a), b=_texte(b), autojunk=False)
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")


def enregistrer(doc: Any, out: Path) -> Path:
    """Saves `doc` to `out`, unless the user retouched `out`. Returns `out` either way.

    The returned path is the document the offer keeps pointing to: the user's, when
    kept. The new version, then, is `out.parent/_a_comparer/out.name`.
    """
    if retouche(out):
        nouveau = out.parent / A_COMPARER / out.name
        nouveau.parent.mkdir(exist_ok=True)
        doc.save(str(nouveau))
        try:
            n = ecart(out, nouveau)
        except Exception:
            n = -1
        _log.warning(
            f"  ✋ {out.name} retouché à la main : ta version est gardée. La nouvelle est dans "
            f"{A_COMPARER}/ ({n if n >= 0 else '?'} paragraphe(s) différent(s)) — compare, "
            f"puis supprime ta version pour prendre la nouvelle."
        )
        return out
    doc.save(str(out))
    noter(out)
    return out
