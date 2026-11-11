// --- Activity: what runs now, in a light panel that folds -----------------------------
// The user, 2026-11-02: « un panneau dédié ou une notification repliable », not a black
// console, and no toast every nine descriptions. One panel shows the task started by a
// button and the background work, each with its progress; the details fold away.
let etatTache = null;  // api.tache()
let etatFond = null;  // api.fond_etat()
let tacheMasquee = false;  // « Fermer » on a finished task: hidden until the next one
let activiteDepliee = false;
try { activiteDepliee = localStorage.getItem("jh-activite") === "1"; } catch (_) { /* no storage */ }

// The percentage a program's output says: « [12/40] », « ── 12/40 » or « 45 % ».
function avancement(lignes) {
  for (let i = lignes.length - 1; i >= Math.max(0, lignes.length - 30); i--) {
    const l = lignes[i];
    let m = l.match(/\[(\d+)\/(\d+)\]/) || l.match(/── (\d+)\/(\d+)/);
    if (m && +m[2] > 0) return Math.min(100, Math.round((100 * m[1]) / m[2]));
    m = l.match(/(\d+(?:[.,]\d+)?) ?%/);
    if (m) return Math.min(100, Math.round(parseFloat(m[1].replace(",", "."))));
  }
  return null;
}

function jauge(pct) {
  return h("div", { class: `jauge ${pct === null ? "indet" : ""}`, role: "progressbar",
    "aria-valuemin": "0", "aria-valuemax": "100", ...(pct === null ? {} : { "aria-valuenow": String(pct) }) },
  h("i", { style: pct === null ? "" : `width:${pct}%` }));
}

function dessinerActivite() {
  const p = $("tache");
  const e = etatTache && !tacheMasquee ? etatTache : null;
  const f = etatFond && etatFond.activite;
  if (!e && !f) { p.hidden = true; return; }
  p.hidden = false;
  p.classList.toggle("fini", !!(e && e.fini) && !f);
  p.classList.toggle("echec", !!(e && e.fini && e.code !== 0));
  const lignes = [];
  if (e) {
    const pct = e.fini ? null : avancement(e.lignes);
    const etat = !e.fini ? `en cours · ${duree(e.duree)}${pct === null ? "" : ` · ${pct} %`}`
      : e.code === 0 ? `terminé en ${duree(e.duree)}`
      : e.code === 3 ? "Un autre programme écrit les offres : réessaie dans un instant"
      : "arrêté avant la fin";
    lignes.push(h("div", { class: "activite-ligne" },
      h("span", { class: "point" }),
      h("div", { class: "activite-texte" }, h("div", { class: "t" }, e.libelle), h("div", { class: "s" }, etat),
        e.fini ? null : jauge(pct)),
      e.fini
        ? h("button", { class: "bouton", onclick: () => { tacheMasquee = true; dessinerActivite(); } }, "Fermer")
        : h("button", { class: "bouton", onclick: async () => { await window.pywebview.api.arreter(); suivreTache(); } }, "Arrêter")));
  }
  if (f) {
    const pct = f.total ? Math.round((100 * f.fait) / f.total) : null;
    lignes.push(h("div", { class: "activite-ligne fond-ligne" },
      h("span", { class: "point" }),
      h("div", { class: "activite-texte" }, h("div", { class: "t" }, f.libelle),
        h("div", { class: "s" }, f.total ? `en arrière-plan · ${f.fait} sur ${f.total}` : "en arrière-plan"), jauge(pct))));
  }
  const detail = e ? e.lignes.slice(-12) : (etatFond.messages || []).map((m) => `${m.heure}  ${m.texte}`);
  const plier = h("button", { class: "lien-plier", "aria-expanded": String(activiteDepliee), onclick: () => {
    activiteDepliee = !activiteDepliee;
    try { localStorage.setItem("jh-activite", activiteDepliee ? "1" : ""); } catch (_) { /* no storage */ }
    dessinerActivite();
  } }, activiteDepliee ? (e ? "Masquer ce qu'écrit le programme" : "Masquer l'historique")
    // « Voir le détail » said nothing of what unfolds (the user, 2026-11-04: « pas clair »).
    : e ? `Voir ce qu'écrit le programme (${detail.length} dernières lignes)` : `Voir l'historique (${detail.length} messages)`);
  p.replaceChildren(...lignes,
    ...(detail.length ? [plier] : []),
    ...(detail.length && activiteDepliee ? [h("div", { class: "activite-detail" }, detail.map((l) => h("div", {}, l)))] : []));
}

async function suivreTache() {
  clearTimeout(minuteurTache);
  if (!window.pywebview) return;
  const e = await window.pywebview.api.tache();
  suivreMaj(e);
  etatTache = e;
  dessinerActivite();
  if (!e) return;
  if (!e.fini) {
    tacheEnCours = true;
    minuteurTache = setTimeout(suivreTache, 1000);
  } else if (tacheEnCours) {
    tacheEnCours = false;
    redessiner();  // the data may have changed: show it
  }
}

// The update, followed on the title bar's button and in the Moteur card: its time or
// its percentage, the last line as a tooltip, then done or failed (the user,
// 2026-10-28: « avoir un temps ou un pourcentage quand on passe la souris dessus »).
// Before, the button said « Mise à jour en cours… » for good, even after a failure.
function suivreMaj(e) {
  if (!e || e.cle !== "maj") return;
  const derniere = e.lignes[e.lignes.length - 1] || "";
  const pct = (derniere.match(/(\d+) %/) || [])[1];
  const texte = !e.fini ? (pct ? `Mise à jour… ${pct} %` : `Mise à jour… ${duree(e.duree)}`)
    : e.code === 0 ? "Mise à jour faite : relance JobHunter"
    : e.code === 3 ? "Mise à jour reportée : file occupée"
    : "Mise à jour échouée";
  const info = (e.fini ? `terminée en ${duree(e.duree)}` : `en cours · ${duree(e.duree)}`) + (derniere ? ` · ${derniere}` : "");
  const b = $("maj");
  if (b) {
    b.hidden = false;
    b.onclick = clicMaj;
    b.textContent = texte;
    b.title = info;
    b.disabled = !e.fini;
    b.classList.toggle("echec", e.fini && e.code !== 0);
    b.dataset.fait = e.fini && e.code === 0 ? "1" : "";
  }
  const m = document.querySelector(".etat-maj");
  if (m) { m.textContent = `${texte} · ${info}`; m.title = info; }
  document.querySelectorAll(".bouton-maj").forEach((x) => { x.disabled = !e.fini; });
}

// --- Guided application (the desktop's Candidatures panel, web.guided) ---------------
// The program opens each ticked offer in Chrome, fills it in and stops before sending:
// the user clicks Send in Chrome, then « J'ai envoyé » here. Nothing is sent from here.
let minuteurGuidee = null;
let envoisGuidee = 0;

async function candidatureGuidee(ids) {
  if (!window.pywebview) { toast("Disponible dans l'application seulement.", true); return; }
  const n = ids.length;
  const ok = await dialogue("Candidature guidée",
    `${n} offre${n > 1 ? "s" : ""}. Chrome ouvre chaque offre, remplit le formulaire, joint CV et lettre, puis s'arrête avant l'envoi. ` +
    "Tu vérifies et cliques « Envoyer » toi-même dans Chrome, puis « J'ai envoyé » ici. JobHunter n'envoie rien.",
    null, [["Commencer", "plein", () => true]]);
  if (!ok) return;
  const r = await window.pywebview.api.candidature_guidee(ids);
  if (!r || !r.ok) { toast((r && r.erreur) || "Lancement impossible.", true); return; }
  coches.clear();
  envoisGuidee = 0;
  redessiner();
  suivreGuidee();
}

async function commandeGuidee(cmd) {
  const r = await window.pywebview.api.candidature_commande(cmd);
  if (r && !r.ok && r.erreur) toast(r.erreur, true);
  suivreGuidee();
}

async function suivreGuidee() {
  clearTimeout(minuteurGuidee);
  if (!window.pywebview) return;
  const e = await window.pywebview.api.candidature_etat();
  const p = $("guidee");
  if (!e) { p.hidden = true; return; }
  const actif = e.attente && !e.fini;
  p.hidden = false;
  p.classList.toggle("fini", e.fini);
  p.classList.toggle("a-toi", actif);
  const zone = (z) => (e.zones[z].texte ? h("div", { class: `zone-${z} ton-${e.zones[z].ton}` }, e.zones[z].texte) : null);
  const commande = (texte, cmd, classe = "") =>
    h("button", { class: `bouton ${classe}`, disabled: !actif, onclick: () => commandeGuidee(cmd) }, texte);
  p.replaceChildren(...[  // replaceChildren writes null as text: filtered below
    h("div", { class: "tache-tete" },
      h("span", { class: "point" }),
      h("div", { style: "min-width:0;flex:1" },
        h("div", { class: "t" }, `Candidature guidée · ${e.n} offre${e.n > 1 ? "s" : ""}`),
        h("div", { class: "s" }, e.fini ? "terminée" : actif ? "à toi : vérifie dans Chrome" : "le programme travaille…")),
      e.fini
        ? h("button", { class: "bouton", onclick: () => { p.hidden = true; } }, "Fermer")
        : h("button", { class: "bouton", onclick: async () => { await window.pywebview.api.candidature_arreter(); suivreGuidee(); } }, "Arrêter")),
    zone("offre"), zone("dossier"), zone("etat"), zone("resultat"),
    e.fini ? null : h("div", { class: "boutons" },
      commande("J'ai envoyé", "envoye", "plein"), commande("Sauter", "saute"),
      commande("Re-remplir", "reremplir"), commande("Rouvrir l'offre", "rouvrir")),
    e.journal.length ? h("pre", {}, e.journal.join("\n")) : null].filter(Boolean));
  if (e.envois !== envoisGuidee) { envoisGuidee = e.envois; redessinerDonnees(); }  // the tracking was written
  if (!e.fini) minuteurGuidee = setTimeout(suivreGuidee, 800);
}

// Ctrl+Enter = « J'ai envoyé », as on the desktop panel.
document.addEventListener("keydown", (e) => {
  const p = $("guidee");
  if (e.ctrlKey && e.key === "Enter" && p && !p.hidden && p.classList.contains("a-toi")) {
    e.preventDefault();
    commandeGuidee("envoye");
  }
  // Ctrl+Z = undo the last status change, outside a text field (where it undoes typing).
  const saisie = e.target && e.target.closest && e.target.closest("input, textarea, [contenteditable]");
  if (e.ctrlKey && !e.shiftKey && (e.key === "z" || e.key === "Z") && !saisie) {
    e.preventDefault();
    annulerGeste();
  }
});

// Redraws the current screen without leaving it (the drawer stays open).
function redessiner() {
  if (courant && ECRANS[courant]) ECRANS[courant].dessiner($("vue")).catch(console.error);
}

// Redraws after a change made in the background: only the screens that show data, so
// a form being typed in (profile, sources, settings) never loses what was typed.
// The lists keep where they were scrolled to: a batch of descriptions landing must not
// send the offers list back to its top while it is being read.
async function redessinerDonnees() {
  if (!["accueil", "offres", "candidatures", "relances", "documents", "stats"].includes(courant)) return;
  const vue = $("vue");
  const defilants = () => [vue, ...vue.querySelectorAll(".defile")];
  const avant = defilants().map((e) => e.scrollTop);
  await ECRANS[courant].dessiner(vue).catch(console.error);
  defilants().forEach((e, i) => { if (avant[i]) e.scrollTop = avant[i]; });
}

// --- Application status ---------------------------------------------------------------

const STATUTS = ["à postuler", "à vérifier", "postulé", "relancé", "entretien", "refus", "mauvaise", "pas intéressé", "expiré"];
const majuscule = (s) => s[0].toUpperCase() + s.slice(1);

// A call that writes: outside the application it only says so; an error becomes a toast.
// A Python exception (corrupt file, full disk) rejects the call: a toast too, never a
// silent half-done gesture (audit 2026-10-29).
async function ecrire(nom, ...args) {
  if (!window.pywebview) { toast(HORS_APPLI, true); return null; }
  let r;
  try { r = await window.pywebview.api[nom](...args); }
  catch (e) { toast(`Échec : ${(e && e.message) || e}`, true); return null; }
  if (r && r.ok === false) { toast(r.erreur || (r.erreurs || []).join(" · "), true); return null; }
  return r;
}

async function marquer(id, statut, rouvrir = true) {
  const r = await ecrire("marquer", id, statut);
  if (!r) return;
  const n = Array.isArray(id) ? id.length : 1;
  // The promised « Annuler » is a real button now, and Ctrl+Z does the same: the toast
  // used to promise it with nothing wired to annulerGeste (audit 2026-11-03).
  toast(`${n > 1 ? `${n} offres · ` : ""}${statut ? `Statut : ${statut}` : "Statut vidé"}`, false,
    ["Annuler", annulerGeste]);
  if (rouvrir && !Array.isArray(id)) ouvrirOffre(id);
  redessiner();
}

async function annulerGeste() {
  const r = await ecrire("annuler");
  if (!r) return;
  toast(`Annulé (${r.n} offre${r.n > 1 ? "s" : ""}).`);
  redessiner();
}

// A small modal window; resolves with what a button returns, null when closed.
function dialogue(titre, sous, contenu, boutons) {
  return new Promise((fin) => {
    const fond = h("div", { class: "dialogue-fond" });
    const avant = document.activeElement;
    const fermer = (v) => {
      fond.remove();
      if (avant && document.contains(avant)) avant.focus({ preventScroll: true });
      fin(v);
    };
    fond.addEventListener("click", (e) => { if (e.target === fond) fermer(null); });
    const id = `dialogue-${Date.now()}`;
    fond.append(h("div", { class: "dialogue verre", role: "dialog", "aria-modal": "true", "aria-labelledby": id },
      h("h2", { id }, titre), sous ? h("p", { class: "sous" }, sous) : null,
      contenu,
      h("div", { class: "boutons" }, bouton("Annuler", "", () => fermer(null)),
        boutons.map(([texte, classe, valeur]) => bouton(texte, "", () => {
          const v = valeur();
          if (v !== undefined) fermer(v);
        }, classe)))));
    document.body.append(fond);
    const champ = fond.querySelector("input, textarea") || fond.querySelector(".boutons button:last-child");
    if (champ) champ.focus();
    fond.addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(null); });
  });
}

async function demanderMotif(n) {
  const motifs = (await appel("motifs")) || [];
  let choix = "";
  const libre = h("input", { class: "champ-texte", placeholder: "ou une autre raison…", oninput: () => {
    choix = libre.value.trim(); liste.querySelectorAll("button").forEach((b) => b.classList.remove("on")); } });
  const liste = h("div", { class: "motifs" }, motifs.map((m) => h("button", { class: "motif", onclick: (e) => {
    choix = m; libre.value = "";
    liste.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === e.currentTarget)); } }, m)));
  return dialogue(`Écarter ${n} offre${n > 1 ? "s" : ""}`,
    "Retirées de la file, elles ne reviennent pas à la collecte suivante. Le motif aide à comprendre ce qui ne va pas et corrige le score.",
    h("div", {}, liste, libre),
    [["Écarter", "chaud", () => (choix ? choix : (toast("Choisis un motif.", true), undefined))]]);
}

async function ecarter(ids) {
  const motif = await demanderMotif(ids.length);
  if (!motif) return;
  const r = await ecrire("ecarter", ids, motif);
  if (!r) return;
  toast(`${r.retirees} offre(s) écartée(s) — « ${motif} ». ${r.exclusions} nouvelle(s) exclusion(s).${gardees(r)}`);
  coches.clear();
  fermerTiroir();
  redessiner();
}

// Offers with an application stay in the queue with their posting (the server keeps them).
const gardees = (r) => (r.gardees ? ` ${r.gardees} gardée(s) : elles ont une candidature.` : "");

async function ajouterOffre() {
  const champ = h("input", { class: "champ-texte", placeholder: "https://…" });
  const url = await dialogue("Ajouter une offre", "Colle le lien de l'annonce : titre, entreprise et description sont lus, puis l'offre entre dans la file.",
    champ, [["Ajouter", "plein", () => champ.value.trim() || undefined]]);
  if (!url) return;
  if (await ecrire("ajouter_offre", url)) suivreTache();
}

async function declarerEnvoi(id) {
  const ok = await dialogue("Confirmer l'envoi", "As-tu envoyé cette candidature ? Rien n'est envoyé ici : c'est noté dans le suivi.",
    null, [["Oui, je l'ai envoyée", "plein", () => true]]);
  if (!ok) return;
  if (await ecrire("declarer_envoi", id)) { toast("Candidature notée comme envoyée."); ouvrirOffre(id); redessiner(); }
}

const bouton = (texte, icone, onclick, classe = "") =>
  h("button", { class: `bouton ${classe}`, onclick }, icone ? svg(icone) : null, texte);

// What a button does, in a bubble after a moment on it (the user, 2026-11-05: « quand on
// passe la souris dessus une explication s'affiche au bout de quelques secondes »):
// `data-aide` on the element. Not in the page under the buttons: it took room for what
// one reads once.
const AIDE_DELAI = 1200;
let aideMinuteur = 0;
let aideCible = null;
function cacherAide() {
  clearTimeout(aideMinuteur);
  aideCible = null;
  const b = $("bulle-aide");
  if (b) b.hidden = true;
}
document.addEventListener("mouseover", (e) => {
  const cible = e.target.closest && e.target.closest("[data-aide]");
  if (cible === aideCible) return;
  cacherAide();
  if (!cible) return;
  aideCible = cible;
  aideMinuteur = setTimeout(() => {
    if (!cible.isConnected) return;
    let b = $("bulle-aide");
    if (!b) { b = h("div", { id: "bulle-aide", class: "bulle-aide", role: "tooltip" }); document.body.append(b); }
    b.textContent = cible.dataset.aide;
    b.hidden = false;
    const r = cible.getBoundingClientRect();
    const l = b.offsetWidth, ht = b.offsetHeight;
    const x = Math.min(Math.max(8, r.left + r.width / 2 - l / 2), innerWidth - l - 8);
    const y = r.top - ht - 8 >= 8 ? r.top - ht - 8 : r.bottom + 8;
    b.style.left = `${x}px`;
    b.style.top = `${y}px`;
  }, AIDE_DELAI);
});
for (const ev of ["mousedown", "keydown", "scroll"]) document.addEventListener(ev, cacherAide, true);
const aide = (el, texte) => { el.dataset.aide = texte; return el; };

// « Plus… »: a list of [text, icon, action] behind one button; closes on a choice or
// on a click elsewhere. It opens in the flow, on its own line: a floating menu was cut
// by the drawer's edge in a narrow window (2026-11-03).
function plus(entrees) {
  const d = h("details", { class: "plus" }, h("summary", { class: "bouton" }, "Plus…"),
    h("div", { class: "menu-plus" }, entrees.map(([t, ic, f]) => bouton(t, ic, () => { d.open = false; f(); }))));
  const dehors = (e) => { if (!d.contains(e.target)) d.open = false; };
  d.addEventListener("toggle", () => {
    if (d.open) document.addEventListener("mousedown", dehors);
    else document.removeEventListener("mousedown", dehors);
  });
  return d;
}

function segment(options, valeur, onchange) {
  return h("div", { class: "seg" }, options.map(([v, lib]) =>
    h("button", { class: v === valeur ? "on" : "", onclick: () => onchange(v) }, lib)));
}

function pagination(d, aller, taille = null) {
  return h("div", { class: "pagination" },
    h("span", {}, `${nombre(d.total)} résultat${d.total > 1 ? "s" : ""} · page ${d.page + 1} sur ${d.pages}`),
    taille,
    h("div", { class: "seg" },
      h("button", { disabled: d.page <= 0, onclick: () => aller(d.page - 1) }, "Précédente"),
      h("button", { disabled: d.page + 1 >= d.pages, onclick: () => aller(d.page + 1) }, "Suivante")));
}
