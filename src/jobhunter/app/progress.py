"""A collection's progress, read from the progress lines of `jobhunter collect`.

The collection prints, for each source, `»» source linkedin début` then
`»» source linkedin fin ok 693 412.0`, and after the merge `»» bilan 136 nouvelles`
(sources.source_yield.progres). The application shows them as a strip above its log —
which source runs, which finished with how many offers, which was refused or limited —
and, at the end, one concrete sentence instead of « terminé »: new offers, sources that
answered, sources that refused.

Pure: no widget here, so it is tested without a window.
"""

import re
from dataclasses import dataclass, field

from jobhunter.app.language import t as _t

PREFIXE = "»» "
_RX_SOURCE = re.compile(r"^»» source (\S+) (début|fin)(?: (.+?) (\d+) ([\d.]+))?\s*$")
_RX_BILAN = re.compile(r"^»» bilan (\d+) nouvelles\s*$")

# The verdicts of sources.source_yield, and how the strip shows them.
SIGNES = {"ok": "✓", "partiel": "◐", "limité": "⏸", "refusé": "⛔", "rien à prendre": "∅"}


@dataclass
class Progression:
    """The sources of the run in order, each with its state; the merge's new offers."""

    sources: dict[str, tuple[str, int]] = field(default_factory=dict)  # nom -> (état, offres)
    nouvelles: int | None = None

    def lire(self, ligne: str) -> bool:
        """Takes one output line. True if it was a progress line (then not shown as is)."""
        if not ligne.startswith(PREFIXE):
            return False
        if m := _RX_SOURCE.match(ligne.strip()):
            nom, phase, verdict, n, _duree = m.groups()
            self.sources[nom] = ("en cours", 0) if phase == "début" else (verdict, int(n))
            return True
        if m := _RX_BILAN.match(ligne.strip()):
            self.nouvelles = (self.nouvelles or 0) + int(m.group(1))
            return True
        return False

    def bande(self) -> str:
        """One line: each source and its state, the running one marked."""
        morceaux = []
        for nom, (etat, n) in self.sources.items():
            if etat == "en cours":
                morceaux.append(f"{nom} …")
            else:
                signe = SIGNES.get(etat, "·")
                morceaux.append(f"{nom} {signe} {n}" if n else f"{nom} {signe}")
        return "  ·  ".join(morceaux)

    def bilan(self) -> str:
        """The concrete outcome, once the run ended ("" if nothing was collected)."""
        if not self.sources:
            return ""
        refusees = [n for n, (e, _) in self.sources.items() if e == "refusé"]
        limitees = [n for n, (e, _) in self.sources.items() if e == "limité"]
        coupees = [n for n, (e, _) in self.sources.items() if e == "en cours"]
        ont_repondu = len(self.sources) - len(refusees) - len(coupees)
        phrase = _t(
            "Collecte : {a} nouvelle(s) offre(s), {b} source(s) sur {c} ont répondu"
        ).format(
            a="?" if self.nouvelles is None else self.nouvelles,
            b=ont_repondu,
            c=len(self.sources),
        )
        if refusees:
            phrase += " · " + _t("refusées : {a}").format(a=", ".join(refusees))
        if limitees:
            phrase += " · " + _t("limitées : {a}").format(a=", ".join(limitees))
        if coupees:
            phrase += " · " + _t("interrompues : {a}").format(a=", ".join(coupees))
        return phrase + "."
