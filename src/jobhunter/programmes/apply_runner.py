"""
apply_runner.py — semi-auto job-application runner.

Loops over offers in apply_queue.json, opens each apply page in YOUR Chrome
(persistent profile = your LinkedIn/ATS logins stay), best-effort autofills the
form (name / email / phone / uploads CV + cover letter), then STOPS.
You verify and click "Envoyer" yourself. Status logged to apply_runner_done.json, resumable.

NO form is ever auto-submitted. Submit = you.

Usage (run in a real terminal, NOT inside an IDE output pane):
    cd Scripts
    py apply_runner.py --canal auto           # offres directes (defaut)
    py apply_runner.py --canal linkedin       # Easy Apply semi-auto
    py apply_runner.py --selection sel.json   # offres cochees dans l'app
    py apply_runner.py --canal auto --start 5 # reprendre a la 5e

First run: a fresh Chrome window opens. Log into LinkedIn / WTJ / the ATS once;
the profile dir remembers you for next runs.

Per offer, console asks:
    [s] = marqué ENVOYÉ   [k] = SAUTÉ   [r] = re-remplir (après navigation manuelle)
    [o] = ré-ouvrir l'URL  [enter] = re-remplir   [q] = quitter (sauvegarde)

`--pilote` : the same loop driven by the desktop app instead of the keyboard. Events go
to stdout as `@JH {json}` lines (offre, pret, bloque, attente, resultat, fin); commands
come on stdin, one per line (envoye, saute, reremplir, rouvrir, quitter). It adds no
click: the submit button is still the user's.

After "envoyé" (both modes) the page is OBSERVED, never clicked: suivi.json gets
"postulé" with `envoi` = confirmé | incertain and a `preuve` (excerpt, address,
screenshot in Scripts/_preuves/). See docs/adr/0009-preuve-distincte-de-la-declaration.md

Decision : docs/adr/0005-aucune-soumission-automatique.md
"""

import argparse
import importlib
import os
import sys
import time
from pathlib import Path

from jobhunter import racine as _racine

# Console Windows = cp1252 → les print d'emoji/accents (describe_page, fill…) levaient
# UnicodeEncodeError et cassaient le remplissage. Force UTF-8 (remplace si impossible).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
except Exception:
    pass


def _unquote_path(u):
    """file:///…/Soci%C3%A9tal.pdf -> chemin disque décodé (accents). '' si vide."""
    from jobhunter.programmes.jutil import chemin_de

    p = chemin_de(u)
    return str(p) if p else ""


ROOT = _racine.racine()
# Profil de formulaire : profil/profil.json (identite + section « formulaire »),
# sans aucun mot de passe. Voir profil.formulaire().
PROFILE = importlib.import_module("jobhunter.profil").formulaire()
# persistent login store — MUST be off OneDrive (sync breaks Chrome's profile lock -> exit 21)
PW_USER_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "apply_runner_chrome"

# ---- field heuristics: regex (on name+id+placeholder+aria-label+label text) -> profile key ----
import re

# _norm() vivait ici : table d'accents manuelle et incomplete (ni ë, ni ï, ni ù,
# ni ü), et surtout appelee NULLE PART. Supprimee. Si un besoin revient :
# jutil.sans_accent(), qui passe par NFD et n'oublie aucune lettre.

# ordre = priorité (spécifique avant générique). Chaque clé existe dans apply_profile.json.
FIELD_MAP = [
    (
        r"(e-?mail|courriel|identifiant|username|login)",
        "email",
    ),  # TalentSoft/ASP.NET: "Identifiant"
    (r"(first.?name|pr[eé]nom|given.?name|vorname)", "prenom"),
    (r"(last.?name|surname|family.?name|nom de famille|nachname)", "nom"),
    (r"(date.?de.?naissance|birth|naissance|geburt|d\.?o\.?b)", "date_naissance"),
    (r"(nationalit|nationality)", "nationalite"),
    (r"(linked ?in)", "linkedin"),
    (r"(github)", "github"),
    (r"(portfolio|site ?web|website|url perso|personal (site|web))", "site_web"),
    (r"(phone|t[eé]l[eé]?(phone)?|portable|mobile|num[eé]ro|handy)", "tel"),
    (r"(city|ville|localit|commune|stadt)", "ville"),
    (r"(zip|postal|code postal|\bcp\b|plz)", "cp"),
    (r"(country|pays|land)", "pays"),
    (r"(address|adresse|rue|street|stra[sß]e)", "adresse"),
    (
        r"(disponibilit|availability|date de d[eé]but|start date|preavis|pr[eé]avis)",
        "disponibilite",
    ),
    (r"(salaire|salary|r[eé]mun[eé]ration|pr[eé]tention|expected|gehalt)", "salaire_souhaite"),
    (r"(mobilit|mobility|relocation|d[eé]m[eé]nag)", "mobilite"),
    (r"(permis|driver|driving licen|f[üu]hrerschein)", "permis"),
    (
        r"(niveau.?(d')?[eé]tude|degree|dipl[oô]me|education level|study level|abschluss)",
        "niveau_etudes",
    ),
    (
        r"(poste actuel|dernier poste|current (position|job|role)|current employer|employeur actuel)",
        "dernier_poste",
    ),
    (r"(langue|language|sprach)", "langues"),
    (r"(comp[eé]tence|skills|comp[eé]tences cl[eé])", "competences"),
    (
        r"(full.?name|nom complet|votre nom|\bname\b|vollst[aä]ndiger name)",
        "full",
    ),  # générique en dernier
]
COVER_RE = r"(message|motivation|lettre|cover|pourquoi|presentation|about you|commentaire|tell us|parlez|why|motiv)"

AUTOFILL_JS = r"""
() => {
  const out = [];
  const norm = s => (s||'').toLowerCase()
     .normalize('NFD').replace(/[̀-ͯ]/g,'');
  const labelText = el => {
    let t = '';
    if (el.id){ const l=document.querySelector(`label[for="${el.id}"]`); if(l) t+=' '+l.textContent; }
    const p = el.closest('label'); if(p) t+=' '+p.textContent;
    return t;
  };
  const fields = [...document.querySelectorAll('input,textarea,select')];
  for (const el of fields){
    const type=(el.type||'').toLowerCase();
    if(['hidden','submit','button','checkbox','radio','file','password'].includes(type)) continue;
    if(el.value && el.value.trim()) continue;            // don't overwrite
    const key = norm([el.name,el.id,el.placeholder,el.getAttribute('aria-label'),labelText(el)].join(' '));
    out.push({tag:el.tagName, type, key,
      ref: el.name||el.id||el.placeholder||'' , idx: fields.indexOf(el)});
  }
  // expose for python via data-pw-idx
  fields.forEach((el,i)=>el.setAttribute('data-pw-idx', i));
  return out;
}
"""


def autofill(page):
    metas = page.evaluate(AUTOFILL_JS)
    filled = 0
    for m in metas:
        key = m["key"]
        val = None
        if m["tag"] == "TEXTAREA" and re.search(COVER_RE, key):
            val = PROFILE.get("message")
        else:
            if re.search(COVER_RE, key) and m["tag"] != "TEXTAREA":
                continue
            for rx, pk in FIELD_MAP:
                if re.search(rx, key):
                    val = PROFILE.get(pk)
                    break
        if not val:
            continue
        try:
            loc = page.locator(f'[data-pw-idx="{m["idx"]}"]')
            if m["tag"] == "SELECT":
                # dropdown : choisit l'option dont le libellé/valeur contient la valeur profil
                if not _select_match(loc, str(val)):
                    continue
            else:
                loc.fill(val, timeout=2000)
            filled += 1
        except Exception:
            pass
    filled += fill_selects_radios(page)  # civilité, pays, niveau via <select>/radio
    # Aucun champ mot de passe n'est rempli : regle du projet (ADR 0005).
    return filled


def _select_match(loc, val):
    """Sélectionne dans un <select> l'option qui matche `val` (par label puis value)."""
    v = val.strip().lower()
    try:
        opts = loc.locator("option")
        n = opts.count()
        for i in range(n):
            o = opts.nth(i)
            txt = (o.inner_text(timeout=800) or "").strip().lower()
            ov = (o.get_attribute("value") or "").strip().lower()
            if v and (v in txt or txt in v or v == ov):
                loc.select_option(index=i, timeout=2000)
                return True
    except Exception:
        pass
    return False


def fill_selects_radios(page):
    """Remplit civilité (M./Monsieur) via <select> ou radio, et pays=France si <select> vide.
    Léger, best-effort. Retour nb rempli."""
    n = 0
    # civilité : radio ou select contenant "monsieur/m." (profil = homme)
    js = r"""
    () => {
      const norm=s=>(s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
      let done=0;
      // radios civilité
      for(const r of document.querySelectorAll('input[type=radio]')){
        const k=norm([r.name,r.id,r.value,(document.querySelector(`label[for="${r.id}"]`)||{}).textContent].join(' '));
        if(/civilit|monsieur|\bm\.?\b|\bmr\b|male|masculin|herr/.test(k) && !/madame|mme|female|frau/.test(k)){
          if(!r.checked){ r.click(); done++; break; }
        }
      }
      // selects pays / civilité vides
      for(const s of document.querySelectorAll('select')){
        if(s.value && s.value.trim()) continue;
        const k=norm([s.name,s.id,s.getAttribute('aria-label'),(document.querySelector(`label[for="${s.id}"]`)||{}).textContent].join(' '));
        if(/civilit|title|anrede/.test(k)){
          for(const o of s.options){ if(/monsieur|^m\.?$|^mr$|male|herr/.test(norm(o.text))){ s.value=o.value; s.dispatchEvent(new Event('change',{bubbles:true})); done++; break; } }
        } else if(/pays|country|land/.test(k)){
          for(const o of s.options){ if(/france|français/.test(norm(o.text))){ s.value=o.value; s.dispatchEvent(new Event('change',{bubbles:true})); done++; break; } }
        }
      }
      return done;
    }"""
    try:
        n += int(page.evaluate(js) or 0)
    except Exception:
        pass
    return n


def upload_files(page, cv, letter):
    done = []
    inputs = page.locator('input[type="file"]')
    n = inputs.count()
    files = [f for f in (cv, letter) if f and Path(f).exists()]
    for i in range(min(n, len(files))):
        try:
            inputs.nth(i).set_input_files(files[i], timeout=3000)
            done.append(Path(files[i]).name)
        except Exception:
            pass
    if n == 1 and cv and Path(cv).exists():  # single input -> at least CV
        pass
    return done


# words that OPEN an application form (safe to click) vs SUBMIT (never click)
OPEN_RX = r"(postuler|candidater|je postule|déposer ma candidature|apply now|apply|i'?m interested|postule)"
SUBMIT_RX = r"(envoyer|soumettre|submit|valider|confirmer|envoyer ma candidature|send application|créer le compte|create account|s'inscrire maintenant)"
# controls that OPEN a signup form (safe to click) — not the final create-account submit
REGISTER_RX = r"(créer un compte|creer un compte|s'inscrire|sign ?up|register|créer mon espace|nouveau compte|create an account|inscription)"


def try_click_register(page):
    """Click a 'create account / register' control to open the signup form. Never the final submit."""
    js = r"""
    ([regRx, submitRx]) => {
      const g = new RegExp(regRx, 'i'), s = new RegExp(submitRx, 'i');
      const els = [...document.querySelectorAll('a,button,[role=button],input[type=button]')];
      for (const el of els) {
        const t = (el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
        if (!t || s.test(t)) continue;
        if (g.test(t)) {
          const r = el.getBoundingClientRect();
          if (r.width>0 && r.height>0) { el.setAttribute('data-pw-reg','1'); return t; }
        }
      }
      return '';
    }"""
    try:
        label = page.evaluate(js, [REGISTER_RX, SUBMIT_RX])
        if label:
            page.locator('[data-pw-reg="1"]').first.click(timeout=4000)
            page.wait_for_timeout(2000)
            return label
    except Exception:
        pass
    return ""


def try_open_form(page):
    """Click an 'apply/postuler' control to reach the form. Never clicks a submit button."""
    js = r"""
    ([openRx, submitRx]) => {
      const o = new RegExp(openRx, 'i'), s = new RegExp(submitRx, 'i');
      const els = [...document.querySelectorAll('a,button,[role=button],input[type=button]')];
      for (const el of els) {
        const t = (el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
        if (!t) continue;
        if (s.test(t)) continue;          // skip submit buttons
        if (o.test(t)) {
          const r = el.getBoundingClientRect();
          if (r.width>0 && r.height>0) { el.setAttribute('data-pw-apply','1'); return t; }
        }
      }
      return '';
    }"""
    try:
        label = page.evaluate(js, [OPEN_RX, SUBMIT_RX])
        if label:
            page.locator('[data-pw-apply="1"]').first.click(timeout=4000)
            page.wait_for_timeout(2500)
            return label
    except Exception:
        pass
    return ""


def highlight_submit(page):
    """Outline the submit button red + scroll to it. Does NOT click."""
    js = r"""
    (submitRx) => {
      const s = new RegExp(submitRx, 'i');
      const NEVER = /(annuler|cancel|retour|back|effacer|reset|pr[eé]c[eé]dent|fermer|close)/i;
      const vis = el => { const r=el.getBoundingClientRect(); return r.width>4 && r.height>4; };
      const mark = el => { el.style.outline='4px solid red'; el.style.outlineOffset='2px';
                           el.setAttribute('data-pw-apply','submit'); el.scrollIntoView({block:'center'}); };
      const els = [...document.querySelectorAll('button,input[type=submit],a,[role=button]')].filter(vis);
      // 1) match par texte (postuler/envoyer/soumettre…)
      for (const el of els) {
        const t = (el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
        if (t && s.test(t) && !NEVER.test(t)) { mark(el); return t; }
      }
      // 2) fallback SPA : bouton submit d'un form à >=2 champs, même sans texte reconnu
      const subs = [...document.querySelectorAll('button[type=submit],input[type=submit],button:not([type])')]
        .filter(el => vis(el) && !NEVER.test((el.innerText||el.value||'').trim()));
      for (const el of subs) {
        const f = el.closest('form');
        if (f && f.querySelectorAll('input,textarea,select').length >= 2) {
          mark(el); return (el.innerText||el.value||'submit').trim() || 'submit';
        }
      }
      // 3) dernier recours : dernier bouton submit visible
      if (subs.length) { const el = subs[subs.length-1]; mark(el); return (el.innerText||el.value||'submit').trim() || 'submit'; }
      return '';
    }"""
    try:
        return page.evaluate(js, SUBMIT_RX)
    except Exception:
        return ""


def accept_consent(page):
    """Coche les cases de consentement OBLIGATOIRES (CGU, conditions, politique de confidentialité,
    traitement des données) nécessaires pour créer un compte / postuler. Ne coche PAS les opt-ins
    marketing (newsletter, offres commerciales)."""
    js = r"""
    () => {
      const REQ = /(accepte|conditions|cgu|c\.g\.u|politique|traitement.*donn|j'?ai lu|termes|terms|privacy|consent|rgpd|mentions l)/i;
      const MKT = /(newsletter|marketing|commercial|actualit|offres|partenaires|promo)/i;
      let n = 0;
      const boxes = [...document.querySelectorAll('input[type=checkbox]')];
      for (const b of boxes) {
        if (b.checked || b.disabled) continue;
        // texte associé : label[for], parent, aria-label, texte voisin
        let t = '';
        if (b.id) { const l = document.querySelector(`label[for="${b.id}"]`); if (l) t += ' ' + l.innerText; }
        t += ' ' + (b.getAttribute('aria-label')||'');
        let p = b.closest('label') || b.parentElement;
        if (p) t += ' ' + (p.innerText||'');
        if (REQ.test(t) && !MKT.test(t)) {
          try { b.click(); n++; } catch(e){}
        }
      }
      return n;
    }"""
    try:
        return page.evaluate(js)
    except Exception:
        return 0


# ── Qui repond a « envoye ? » : le clavier (terminal) ou l'application (pilote) ──
class _Terminal:
    """Comportement historique : invites et touches dans une console."""

    pilote = False

    def evenement(self, type_, **champs):
        pass  # les print du programme suffisent en console

    def commande(self, invite):
        return input(invite).strip().lower()

    def fin(self):
        try:
            input(
                "\n✅ Chrome reste OUVERT. Vérifie et clique ENVOYER sur chaque onglet.\n"
                "   Quand tu as fini → [Entrée] pour fermer Chrome > "
            )
        except Exception:
            time.sleep(120)  # pas de clavier (stdin fermé) → garde ouvert 2 min


# Commandes de l'application → touches historiques de la boucle.
_COMMANDES = {"envoye": "s", "saute": "k", "reremplir": "r", "rouvrir": "o", "quitter": "q"}


class _Pilote:
    """L'application pilote : evenements `@JH {json}` sur stdout, commandes sur stdin."""

    pilote = True

    def evenement(self, type_, **champs):
        import json as _j

        print("@JH " + _j.dumps({"type": type_, **champs}, ensure_ascii=False), flush=True)

    def commande(self, invite):
        self.evenement("attente")
        ligne = sys.stdin.readline()
        if not ligne:  # l'application a ferme le tuyau : on s'arrete proprement
            return "q"
        return _COMMANDES.get(ligne.strip().lower(), "")

    def fin(self):
        self.evenement("fin")
        sys.stdin.readline()  # Chrome reste ouvert jusqu'a « quitter » (ou fermeture)


def _chemin_preuve(d):
    import datetime as _dt

    nom = re.sub(r"[^A-Za-z0-9]+", "_", f"{d['comp']}_{d['role']}").strip("_")[:80]
    return _racine.scripts() / "_preuves" / f"{_dt.date.today().isoformat()}_{nom}.png"


def declarer_envoi(page, d):
    """L'utilisateur dit avoir clique Envoyer : la page est OBSERVEE (rien n'est clique),
    la preuve gardee, le suivi ecrit en une fois. Rend l'etat et la preuve.

    Decision : docs/adr/0009-preuve-distincte-de-la-declaration.md"""
    import datetime as _dt

    from jobhunter.navigation.confirmation import capturer_preuve, observer_confirmation
    from jobhunter.stockage import suivi as suivi_io

    obs = observer_confirmation(page)
    preuve = {
        "texte": str(obs.get("texte") or "")[:300],
        "url": str(obs.get("url") or ""),
        "capture": capturer_preuve(page, _chemin_preuve(d)) or "",
        "le": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    oid = f"{(d['comp'] or '').strip()}|{(d['role'] or '').strip()}"
    suivi_io.declarer_envoi(oid, obs["etat"], preuve)
    return {"etat": obs["etat"], **preuve}


def _decision_pilote(ui, page, d, marquer):
    """Attend la decision de l'application pour une offre deja prete (LinkedIn Easy
    Apply). Rend la touche finale : s (envoye), k (saute) ou q (quitter)."""
    while True:
        cmd = ui.commande("")
        if cmd == "s":
            marquer("ENVOYÉ")
            try:
                ui.evenement("resultat", **declarer_envoi(page, d))
            except Exception as e:
                ui.evenement("resultat", etat="erreur", texte=type(e).__name__)
            return cmd
        if cmd == "k":
            marquer("SAUTÉ")
            ui.evenement("resultat", etat="sauté")
            return cmd
        if cmd == "q":
            return cmd
        if cmd == "o":
            try:
                page.goto(d["url"], timeout=45000)
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--canal",
        default=None,
        choices=["auto", "manuel", "linkedin", "all"],
        help="auto=portails directs (défaut), manuel=linkedin/indeed, linkedin=Easy Apply semi-auto (session réutilisée, stop Envoyer), all=tout.",
    )
    ap.add_argument("--start", type=int, default=1, help="skip to Nth offer")
    ap.add_argument(
        "--selection",
        default=None,
        help="chemin JSON [{entreprise,poste},...] : ne postule QUE ces offres (coche depuis l'app). Prioritaire sur --canal.",
    )
    ap.add_argument(
        "--no-turbo",
        action="store_true",
        help="désactive le blocage images/polices/pubs (TURBO actif par défaut).",
    )
    ap.add_argument(
        "--images",
        action="store_true",
        help="TURBO mais garde les images (utile si un site casse sans images).",
    )
    ap.add_argument(
        "--auto",
        action="store_true",
        help="enchaîne : ouvre le form, autofill, surligne Envoyer, stop. Tu cliques Envoyer + Entrée.",
    )
    ap.add_argument(
        "--chrome",
        action="store_true",
        help="Réutilise le profil dédié partagé avec acces.py, sans recopier ni effacer les sessions.",
    )
    ap.add_argument(
        "--no-input", action="store_true", help="Pas de prompt après autofill — observe Chrome 30s"
    )
    ap.add_argument(
        "--fast",
        action="store_true",
        help="Batch ÉCLAIR : pauses réduites + prompt 1-touche (Entrée=envoyé+suivant). Toi = juste Entrée par offre.",
    )
    ap.add_argument(
        "--auth",
        default="auto",
        choices=["auto", "register", "login"],
        help="Sur écran login : auto=tente inscription puis login, register=force inscription, login=force connexion (compte existant).",
    )
    ap.add_argument(
        "--wizard",
        action="store_true",
        help="Formulaires MULTI-ÉCRANS (Workday/iCIMS) : remplit+Suivant en boucle jusqu'au submit final (que tu cliques).",
    )
    ap.add_argument(
        "--agent",
        action="store_true",
        help="Agent LLM (Ollama) en dernier recours si bloqué : lit la page, décide l'action. Nécessite un modèle Ollama.",
    )
    ap.add_argument(
        "--pilote",
        action="store_true",
        help="piloté par l'application (événements sur stdout, commandes sur stdin) — aucun clic d'envoi",
    )
    args = ap.parse_args()
    ui = _Pilote() if args.pilote else _Terminal()
    if args.pilote:
        args.auto = True  # surligne Envoyer ; « envoye » vient de l'application

    # L'application passe --chrome après une connexion via acces.py. Ce profil
    # existe déjà : le cloner à nouveau effacerait les sessions enregistrées.
    if args.chrome:
        print("--chrome : réutilisation du profil dédié partagé avec acces.py")

    # --- source : apply_queue.json UNIQUEMENT (Excel supprimé du pipeline) ---
    if not (args.selection or args.canal):
        args.canal = "auto"  # défaut : offres directes (l'Excel n'existe plus)
        print("(pas de --canal/--selection → défaut : --canal auto)")
    queues = []
    QUEUE_DONE = _racine.scripts() / "apply_runner_done.json"
    queue_done = {}
    import json as _json

    # La file passe par son contrat d'acces (ADR 0002), jamais par json.load direct.
    from jobhunter.stockage import file as queue_io

    q = queue_io.charger(descriptions=False)
    if QUEUE_DONE.exists():
        queue_done = _json.load(open(QUEUE_DONE, encoding="utf-8"))
    # --selection : liste explicite d'offres cochées (prioritaire, ignore canal/prio)
    sel_keys = None
    if args.selection:
        try:
            _sel = _json.load(open(args.selection, encoding="utf-8"))
            sel_keys = {f"{s.get('entreprise', '')}|{s.get('poste', '')}" for s in _sel}
            print(f"Sélection : {len(sel_keys)} offre(s) cochée(s) depuis l'app.")
        except Exception as e:
            print(f"! lecture --selection KO: {e}")
            return
    rows = []
    li_mode = args.canal == "linkedin"
    for x in q:
        key = f"{x['entreprise']}|{x['poste']}"
        if sel_keys is not None:
            if key not in sel_keys:
                continue
        else:
            if not li_mode and x.get("priorite") != "prio":
                continue
            if li_mode:
                # canal linkedin : sélection par HOST (le champ canal reste "manuel")
                if "linkedin.com" not in (x.get("url") or ""):
                    continue
            elif args.canal != "all" and x.get("canal") != args.canal:
                continue
        rows.append(
            dict(
                r=None,
                comp=x["entreprise"],
                role=x["poste"],
                url=x.get("url") or "",
                cv=_unquote_path(x.get("cv")),
                lt=_unquote_path(x.get("lettre")),
                status=queue_done.get(key, ""),
            )
        )
    rows.sort(
        key=lambda d: (
            -next(
                (
                    y.get("skills_match", 0)
                    for y in q
                    if y["entreprise"] == d["comp"] and y["poste"] == d["role"]
                ),
                0,
            )
        )
    )
    queues.append((f"queue:{args.selection and 'selection' or args.canal}", None, rows, None))

    def mark(ws, d, ix, val):
        """Écrit le statut dans apply_runner_done.json (ws/ix conservés pour compat).

        ÉCRITURE ATOMIQUE. `open(..., "w")` tronque le fichier AVANT d'écrire :
        une coupure au milieu — et ce programme tourne dans une console ouverte
        pendant des heures, à côté d'un Chrome qu'on ferme parfois d'un coup —
        laissait un fichier vide ou à moitié écrit. Ce fichier dit à quoi
        l'utilisateur a déjà postulé ; le perdre fait repostuler. jutil écrit à côté
        puis bascule d'un seul coup.
        """
        queue_done[f"{d['comp']}|{d['role']}"] = val
        importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE_DONE, queue_done)

    total = sum(len(r) for _, _, r, _ in queues)
    print(f"Offres chargées: {total}  (feuilles: {', '.join(s for s, _, _, _ in queues)})")
    print("Profil:", PROFILE["full"], "|", PROFILE["email"])
    print("AUCUN envoi auto. Tu vérifies + cliques Envoyer toi-même.\n")

    # Profil Chrome DEDIE a JobHunter, jamais le profil Chrome personnel : celui-ci
    # porte les sessions et mots de passe enregistres de l'utilisateur.
    launch_args = ["--start-maximized"]
    udir = str(PW_USER_DIR)
    print(f"Profil persistant dédié: {udir} (connecte-toi 1 fois, à la main, ça reste)")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=udir,
                channel="chrome",
                headless=False,
                args=launch_args,
                no_viewport=True,
            )
            # TURBO (défaut) : bloque images/polices/media/pubs → pages 2-5× plus vite.
            # --images pour tout recharger si un site casse. --no-turbo pour désactiver.
            if not getattr(args, "no_turbo", False):
                try:
                    from jobhunter.navigation import block_resources

                    block_resources(ctx, images=getattr(args, "images", False))
                    print(
                        "🚀 TURBO : images/polices/pubs bloquées (plus rapide). --no-turbo pour désactiver."
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"\n! Échec lancement Chrome: {type(e).__name__}: {e}")
            return
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        seen = 0
        for sheet, ws, rows, ix in queues:
            for d in rows:
                if str(d["status"]).strip().upper() in ("ENVOYÉ", "ENVOYE", "SAUTÉ", "SAUTE"):
                    continue
                # garde : pas d'URL http -> rien à ouvrir, on saute (recherche manuelle requise)
                if not str(d.get("url") or "").startswith("http"):
                    continue
                seen += 1
                if seen < args.start:
                    continue
                try:
                    print("=" * 70)
                    print(f"[{seen}/{total}] {d['comp']} — {d['role']}")
                    fa = {}  # remplissage de CETTE offre (vide si echec)
                    ui.evenement(
                        "offre",
                        i=seen,
                        total=total,
                        entreprise=d["comp"],
                        poste=d["role"],
                        url=d["url"],
                    )
                    print("  URL :", d["url"])
                    print(
                        "  CV  :",
                        Path(d["cv"]).name if d["cv"] else "—",
                        "| Lettre:",
                        Path(d["lt"]).name if d["lt"] else "—",
                    )
                    try:
                        from jobhunter.navigation import homepage_fallback, robust_goto

                        g = robust_goto(page, d["url"], tries=3)
                        if not g["ok"]:
                            print("  ! navigation:", g["note"])
                            # PIPELINE DE BASE : URL morte → site officiel → carrières → offre
                            hf = homepage_fallback(page, d["comp"], d.get("role", ""))
                            try:
                                from jobhunter.programmes.queue_tools import writeback

                                if hf.get("ok"):
                                    writeback(d["url"], hf.get("homepage"), "HOMEPAGE_FALLBACK")
                                else:
                                    writeback(d["url"], link_status="MORT")
                            except Exception:
                                pass
                            if hf.get("ok"):
                                print(
                                    f"  🏠 fallback: {hf['homepage']} → carrières={hf.get('careers')} → {hf.get('kind', '?')}"
                                )
                            else:
                                print(f"  ✗ fallback homepage: {hf.get('note', '?')}")
                    except Exception as e:
                        try:
                            page.goto(d["url"], timeout=45000, wait_until="domcontentloaded")
                        except Exception:
                            print("  ! navigation:", type(e).__name__)
                    _fast = getattr(args, "fast", False)
                    time.sleep(0.5 if _fast else 1.5)
                    # ── LinkedIn Easy Apply SEMI-AUTO : session réutilisée, remplit, STOP avant Envoyer ──
                    if "linkedin.com" in (d.get("url") or ""):
                        try:
                            from jobhunter.navigation import dismiss_cookies, linkedin_easy_apply

                            dismiss_cookies(page)
                            la = linkedin_easy_apply(
                                page, PROFILE, cv=d["cv"], letter=d["lt"], fast=_fast
                            )
                            print(
                                f"  🔗 LinkedIn: {la.get('kind')} — {la.get('note', '')}"
                                + (f" ({la.get('screens')} écran(s))" if la.get("screens") else "")
                            )
                            if la.get("kind") == "need_login":
                                print(
                                    "     ⚠️  connecte-toi à LinkedIn dans la fenêtre, puis relance sur cette offre (--start)."
                                )
                                mark(ws, d, ix, "LOGIN LinkedIn")
                                ui.evenement("bloque", raison="connexion LinkedIn")
                                continue
                            if la.get("kind") == "ready_to_submit":
                                print(
                                    f"     ⬛ ENVOYER surligné rouge: «{la.get('submit_label', '')}» — clique TOI-MÊME."
                                )
                                mark(ws, d, ix, "À VÉRIFIER LinkedIn")
                                if ui.pilote:
                                    # l'application attend la decision de l'utilisateur
                                    ui.evenement(
                                        "pret",
                                        couverture=None,
                                        documents="",
                                        bouton=la.get("submit_label", ""),
                                    )
                                    if (
                                        _decision_pilote(ui, page, d, lambda v: mark(ws, d, ix, v))
                                        == "q"
                                    ):
                                        ctx.close()
                                        return
                                    continue
                                time.sleep(0.5 if _fast else 3)
                                continue
                            if la.get("kind") == "external":
                                # candidature externe : laisse le pipeline générique gérer (ATS derrière)
                                pass
                            else:
                                mark(ws, d, ix, "LinkedIn " + str(la.get("kind")))
                                continue
                        except Exception as e:
                            print("  ! linkedin:", type(e).__name__)
                    # navigation intelligente + LOOP auto-résolution (self-healing)
                    try:
                        from jobhunter.navigation import (
                            describe_page,
                            dismiss_cookies,
                            find_offer,
                            goto_careers,
                            login_flow,
                            retry,
                            smart_step,
                            switch_to_register,
                        )

                        ck = dismiss_cookies(page)
                        time.sleep(0.3 if _fast else 1)
                        if ck.get("done") not in ("none", "err"):
                            print(f"  🍪 cookies: {ck.get('done')}")
                        # reconnaissance COMPLÈTE de la page (sautée en --fast pour la vitesse)
                        if not _fast:
                            try:
                                print("  🗺️ " + describe_page(page).replace("\n", "\n  "))
                            except Exception:
                                pass
                        # tâche visée selon l'intention : postuler (ouvre form), gère register si détecté
                        r = smart_step(page, task="apply", max_tries=5)
                        # page morte (404 ATS / offre pourvue) → PIPELINE DE BASE homepage→carrières
                        if r["status"] == "stuck" and r.get("kind") == "dead":
                            from jobhunter.navigation import homepage_fallback

                            hf = homepage_fallback(page, d["comp"], d.get("role", ""))
                            if hf.get("ok"):
                                print(
                                    f"  🏠 offre morte → fallback: {hf['homepage']} → {hf.get('kind', '?')}"
                                )
                                try:
                                    from jobhunter.programmes.queue_tools import writeback

                                    writeback(d["url"], hf.get("homepage"), "HOMEPAGE_FALLBACK")
                                except Exception:
                                    pass
                                r = smart_step(page, task="apply", max_tries=4)
                        # homepage corporate -> section Carrières/Nous rejoindre avant offre/login
                        if r["status"] == "stuck" and r["kind"] in ("other", "offer_list"):
                            gc = retry(
                                page, lambda: goto_careers(page), lambda x: x.get("clicked"), 3
                            )
                            if gc.get("clicked"):
                                print(
                                    f"  🧭 carrières: '{gc.get('label', '')}' → {gc.get('kind', '?')} (essai {gc.get('tries', 1)})"
                                )
                                dismiss_cookies(page)
                                r = smart_step(page, task="apply", max_tries=4)
                        # recherche d'offre UNIFIÉE : ATS + recherche mot-clé + drill (pattern ATS)
                        if r["status"] == "stuck" and r["kind"] in (
                            "offer_list",
                            "apply_cta",
                            "other",
                        ):
                            fo = find_offer(page, d.get("role", ""))
                            print(
                                f"  🔎 find_offer [{fo.get('ats', '?')}] via {fo.get('via', '?')} → {fo.get('kind', '?')}"
                            )
                            if fo.get("reached"):
                                r = smart_step(page, task="apply", max_tries=3)
                        # dernier recours : agent LLM (lit la page, décide) — si --agent + Ollama
                        if getattr(args, "agent", False) and r["status"] == "stuck":
                            from jobhunter.navigation import llm_agent

                            ag = llm_agent(
                                page,
                                "atteindre le formulaire de candidature et le remplir",
                                max_steps=6,
                                profile=PROFILE,
                            )
                            print(
                                f"  🤖 agent LLM: {ag.get('note', '?')} ({ag.get('steps', 0)} étapes)"
                            )
                            if ag.get("ok"):
                                r = smart_step(page, task="apply", max_tries=2)
                        if r["status"] == "blocked":
                            print(
                                f"  ⚠️  {r['kind'].upper()} détecté — À TOI (je ne contourne pas). Résous puis [r]."
                            )
                            ui.evenement("bloque", raison=str(r["kind"]))
                        elif r["status"] == "ok":
                            print(f"  ✅ nav: {r['kind']} ({r['note']})")
                            if r["kind"] == "login":
                                # #auth : postuler = souvent PAS de compte -> tente bascule création
                                auth = getattr(args, "auth", "auto")
                                switched = False
                                if (
                                    False
                                ):  # creation de compte : jamais automatique (regle du projet)
                                    sw = retry(
                                        page,
                                        lambda: switch_to_register(page),
                                        lambda x: x.get("switched"),
                                        3,
                                    )
                                    if sw.get("switched") and sw.get("kind") == "register":
                                        print(
                                            f"     ➡️  bascule INSCRIPTION : '{sw.get('label', '')}' → email+mdp+confirm+CGU auto, captcha=toi"
                                        )
                                        switched = True
                                if not switched and auth != "register":
                                    # Connexion : l'email seulement, le mot de passe reste a l'utilisateur.
                                    lg = login_flow(page, PROFILE.get("email", ""), "")
                                    print(f"     🔑 login 2-étapes : {len(lg['steps'])} étape(s)")
                                elif not switched:
                                    print("     ⚠️  pas de bouton inscription trouvé — à la main")
                            elif r["kind"] == "register":
                                print("     inscription : email+mdp+confirm+CGU auto, captcha=toi")
                        else:
                            print(f"  🔁 nav: {r['note']} (kind={r['kind']})")
                    except Exception as e:
                        print("  ! web_nav:", type(e).__name__)
                    # #6 attendre les inputs rendus tard (React/Vue : Wizbii, Meeschaert)
                    try:
                        from jobhunter.navigation import wait_for_form

                        ni = wait_for_form(page, min_inputs=1, timeout_ms=7000)
                        if ni == 0:
                            print(
                                "  ⏳ aucun champ visible (form dynamique non rendu) — vérifie à la main"
                            )
                    except Exception:
                        pass
                    # REMPLISSAGE UNIVERSEL : tous les champs + selects + radios + CGU + tous les docs
                    try:
                        from jobhunter.navigation import fill_application

                        fa = fill_application(page, PROFILE, cv=d["cv"], letter=d["lt"])
                        f, up, cons = fa["filled"], fa["docs"], fa["consent"]
                        print(
                            f"  📝 couverture {fa['cover_pct']}% ({f}/{fa['total']} champs) | 📎 {up or 'aucun fichier'}"
                            + (f" | ☑️ CGU {cons}" if cons else "")
                            + (f" | ⚠️ non-mappés: {fa['unmatched']}" if fa.get("unmatched") else "")
                        )
                    except Exception as e:
                        print("  ! fill:", type(e).__name__)
                        try:
                            f = autofill(page)
                            up = upload_files(page, d["cv"], d["lt"])
                            cons = accept_consent(page)
                        except Exception as e2:
                            print(f"  ! autofill: {type(e2).__name__} — skip offre")
                            mark(ws, d, ix, "SKIP AUTOFILL")
                            continue
                    # --wizard : formulaire multi-écrans (Workday/iCIMS) -> remplit+Suivant en boucle
                    if getattr(args, "wizard", False):
                        try:
                            from jobhunter.navigation import fill_application as _fa
                            from jobhunter.navigation import run_wizard

                            wz = run_wizard(
                                page,
                                fill_fn=lambda pg: _fa(pg, PROFILE, cv=d["cv"], letter=d["lt"])[
                                    "filled"
                                ],
                                max_screens=6,
                            )
                            print(
                                f"  🧩 wizard: {wz.get('screens', 0)} écran(s), stop={wz.get('stopped', '?')}"
                            )
                        except Exception as e:
                            print("  ! wizard:", type(e).__name__)
                    sub = ""
                    if args.auto:
                        sub = highlight_submit(page)
                        print(
                            f"  ⬛ bouton à cliquer surligné rouge: «{sub or 'non trouvé — clique manuellement'}»"
                        )
                    ui.evenement(
                        "pret",
                        couverture=fa.get("cover_pct"),
                        documents=str(fa.get("docs") or ""),
                        bouton=sub,
                    )
                    if getattr(args, "no_input", False):
                        print("  ⏳ Chrome reste ouvert 30s — vérifie et clique Envoyer")
                        time.sleep(30)
                        mark(ws, d, ix, "À VÉRIFIER")
                        continue
                    # Page de code recu par mail (OTP) : c'est a l'utilisateur de le lire et de le
                    # saisir. Aucun programme ne lit sa boite mail (regle du projet).
                    try:
                        from jobhunter.navigation import otp_present as _otp_present

                        if _otp_present(page):
                            print(
                                "  📨 page de code email (OTP) détectée — saisis le code reçu par mail, puis continue"
                            )
                            ui.evenement("bloque", raison="code reçu par courriel")
                    except Exception:
                        pass
                    while True:
                        if getattr(args, "fast", False):
                            prompt = f"  ⚡[{seen}/{total}] {d['comp'][:24]} → clique ENVOYER puis [Entrée]=✅suivant  [k]saut [q]quit > "
                        elif args.auto:
                            prompt = "  → vérifie, clique ENVOYER sur le site, puis [Entrée]=envoyé  [k]sauté  [r]re-remplir  [q]quitter > "
                        else:
                            prompt = (
                                "  [s]envoyé [k]sauté [r]re-remplir [o]ouvrir-url [q]quitter > "
                            )
                        cmd = ui.commande(prompt)
                        if args.auto and cmd == "" and not ui.pilote:
                            cmd = "s"
                        if cmd == "s":
                            mark(ws, d, ix, "ENVOYÉ")
                            try:
                                res = declarer_envoi(page, d)
                                print(f"  📮 envoi {res['etat']} — {res['texte'][:90]}")
                                ui.evenement("resultat", **res)
                            except Exception as e:
                                print(
                                    f"  ! suivi non écrit ({type(e).__name__}) — confirme dans l'app"
                                )
                                ui.evenement("resultat", etat="erreur", texte=type(e).__name__)
                            break
                        if cmd == "k":
                            mark(ws, d, ix, "SAUTÉ")
                            ui.evenement("resultat", etat="sauté")
                            break
                        elif cmd == "r" or (cmd == "" and not ui.pilote):
                            f = autofill(page)
                            try:
                                from jobhunter.navigation import smart_upload as _su

                                up = _su(page, d["cv"], d["lt"])
                            except Exception:
                                up = upload_files(page, d["cv"], d["lt"])
                            print(f"  re-fill: {f} champs | upload: {up}")
                        elif cmd == "o":
                            page.goto(d["url"], timeout=45000)
                            time.sleep(1.5)
                        elif cmd == "q":
                            print("Sauvegardé. Reprends avec --start", seen)
                            ctx.close()
                            return
                except Exception as _e:
                    print(f"  ! ERREUR offre: {type(_e).__name__}: {str(_e)[:80]} — skip")
                    try:
                        mark(ws, d, ix, "ERREUR SKIP")
                    except Exception:
                        pass
                    continue
        print("\nFini. Toutes les offres parcourues.")
        # NE PAS fermer Chrome tant que tu n'as pas validé/cliqué Envoyer.
        ui.fin()
        ctx.close()


if __name__ == "__main__":
    main()
