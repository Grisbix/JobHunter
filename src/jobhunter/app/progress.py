"""A collection's progress, read from the progress lines of `jobhunter collect`.

The collection prints, for each source, `»» source linkedin début` then
`»» source linkedin fin ok 693 412.0`, and after the merge `»» bilan 136 nouvelles`
(sources.source_yield.progres). The application shows them as a strip above its log —
which source runs, which finished with how many offers, which was refused or limited —
and, at the end, one concrete sentence instead of « terminé »: new offers, sources that
answered, sources that refused.

Before its first source, the collection announces its plan (`»» plan ats:35.2 linkedin`,
with each source's usual duration): the strip then opens with a percentage, the time
left and the offers found so far. The availability check prints `»» verif 120 900 7 1500`
(checked, total, closed, seconds left before its time limit) and, after the removal,
`»» verif retirees 7` (programs.availability_audit).

Pure: no widget here, so it is tested without a window.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from jobhunter.app.language import t as _t

PREFIXE = "»» "
_RX_SOURCE = re.compile(r"^»» source (\S+) (début|fin)(?: (.+?) (\d+) ([\d.]+))?\s*$")
_RX_BILAN = re.compile(r"^»» bilan (\d+) nouvelles\s*$")
_RX_PLAN = re.compile(r"^»» plan ?(.*?)\s*$")
_RX_VERIF = re.compile(r"^»» verif (\d+) (\d+) (\d+)(?: (\d+))?\s*$")
_RX_RETIREES = re.compile(r"^»» verif retirees (\d+)\s*$")

# The verdicts of sources.source_yield, and how the strip shows them.
SIGNES = {"ok": "✓", "partiel": "◐", "limité": "⏸", "refusé": "⛔", "rien à prendre": "∅"}


def duree_lisible(secondes: float) -> str:
    """ "45 s", "6 min", "1 h 05"."""
    s = max(0, round(secondes))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{round(s / 60)} min"
    return f"{s // 3600} h {s % 3600 // 60:02d}"


@dataclass
class Progression:
    """The sources of the run in order, each with its state; the merge's new offers.

    Also the availability check's counters, when that is what runs."""

    sources: dict[str, tuple[str, int]] = field(default_factory=dict)  # nom -> (état, offres)
    nouvelles: int | None = None
    # Planned sources -> usual duration in seconds (None: never measured).
    prevues: dict[str, float | None] = field(default_factory=dict)
    debuts: dict[str, float] = field(default_factory=dict)  # source -> start (horloge)
    # Availability check: (checked, total, closed, seconds left before its limit or None)
    verif: tuple[int, int, int, int | None] | None = None
    verif_debut: tuple[float, int] | None = None  # (instant, checked) of the first reading
    retirees: int | None = None
    horloge: Callable[[], float] = time.monotonic

    def lire(self, ligne: str) -> bool:
        """Takes one output line. True if it was a progress line (then not shown as is).

        The daily pipeline prefixes its steps' lines with the minutes elapsed
        ("  12.3' »» source …"): the progress line is found after it."""
        i = ligne.find(PREFIXE)
        if i < 0 or ligne[:i].strip(" \t0123456789.'"):
            return False
        ligne = ligne[i:].strip()
        if m := _RX_SOURCE.match(ligne):
            nom, phase, verdict, n, _duree = m.groups()
            if phase == "début":
                self.sources[nom] = ("en cours", 0)
                self.debuts[nom] = self.horloge()
            else:
                self.sources[nom] = (verdict, int(n))
            return True
        if m := _RX_BILAN.match(ligne):
            self.nouvelles = (self.nouvelles or 0) + int(m.group(1))
            return True
        if m := _RX_PLAN.match(ligne):
            # Several passes (the daily pipeline) each announce theirs: they add up.
            for morceau in m.group(1).split():
                nom, _, duree = morceau.partition(":")
                try:
                    self.prevues[nom] = float(duree) if duree else None
                except ValueError:
                    self.prevues[nom] = None
            return True
        if m := _RX_RETIREES.match(ligne):
            self.retirees = int(m.group(1))
            return True
        if m := _RX_VERIF.match(ligne):
            fait, total, fermees = (int(x) for x in m.groups()[:3])
            reste = int(m.group(4)) if m.group(4) is not None else None
            self.verif = (fait, total, fermees, reste)
            if self.verif_debut is None:
                self.verif_debut = (self.horloge(), fait)
            return True
        return False

    def _estime(self, nom: str) -> float:
        """Usual duration of a source; unmeasured: the mean of the measured ones (60 s if none)."""
        d = self.prevues.get(nom)
        if d is not None:
            return d
        connues = [x for x in self.prevues.values() if x is not None]
        return sum(connues) / len(connues) if connues else 60.0

    def entete(self) -> str:
        """The run at a glance: percentage, time left, offers found ("" without a plan)."""
        if self.verif is not None:
            return self._entete_verif()
        if not self.prevues:
            return ""
        noms = list(self.prevues) + [n for n in self.sources if n not in self.prevues]
        total = sum(self._estime(n) for n in noms) or 1.0
        fait = reste = 0.0
        maintenant = self.horloge()
        for nom in noms:
            estime = self._estime(nom)
            etat = self.sources.get(nom, ("", 0))[0]
            if etat == "en cours":
                ecoule = maintenant - self.debuts.get(nom, maintenant)
                # A source past its usual duration is counted as nearly done, not over.
                fait += min(ecoule, estime * 0.95)
                reste += max(estime - ecoule, estime * 0.05)
            elif etat:
                fait += estime
            else:
                reste += estime
        finies = sum(1 for n in noms if self.sources.get(n, ("", 0))[0] not in ("", "en cours"))
        trouvees = sum(n for _e, n in self.sources.values())
        morceaux = [
            _t("{a}/{b} sources").format(a=finies, b=len(noms)),
            f"{min(99, round(100 * fait / total))} %",
        ]
        if finies < len(noms):
            morceaux.append(_t("~{d} restantes").format(d=duree_lisible(reste)))
        morceaux.append(_t("{n} offres trouvées").format(n=trouvees))
        if self.nouvelles is not None:
            morceaux.append(_t("{n} nouvelles ajoutées").format(n=self.nouvelles))
        return " · ".join(morceaux)

    def _entete_verif(self) -> str:
        assert self.verif is not None
        fait, total, fermees, limite = self.verif
        morceaux = [
            _t("Vérification {a}/{b}").format(a=fait, b=total),
            f"{round(100 * fait / total) if total else 100} %",
        ]
        if fait < total and self.verif_debut is not None:
            t0, f0 = self.verif_debut
            if fait > f0:
                reste = (self.horloge() - t0) / (fait - f0) * (total - fait)
                if limite is not None:
                    reste = min(reste, limite)  # the check stops itself at its limit
                morceaux.append(_t("~{d} restantes").format(d=duree_lisible(reste)))
        morceaux.append(_t("{n} fermée(s)").format(n=fermees))
        if self.retirees is not None:
            morceaux.append(_t("{n} retirée(s) de la file").format(n=self.retirees))
        return " · ".join(morceaux)

    def bande(self) -> str:
        """The header line, then each source and its state, the running one marked."""
        morceaux = []
        for nom, (etat, n) in self.sources.items():
            if etat == "en cours":
                morceaux.append(f"{nom} …")
            else:
                signe = SIGNES.get(etat, "·")
                morceaux.append(f"{nom} {signe} {n}" if n else f"{nom} {signe}")
        sources = "  ·  ".join(morceaux)
        entete = self.entete()
        return f"{entete}\n{sources}" if entete and sources else entete or sources

    def bilan(self) -> str:
        """The concrete outcome, once the run ended ("" if nothing was collected)."""
        if self.verif is not None:
            return _t("Vérification des offres") + " : " + self._entete_verif() + "."
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
