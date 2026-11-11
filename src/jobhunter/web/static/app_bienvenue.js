// --- The welcome (3.78): a folder without a profile, before the application ---------
// jobhunter.web.onboarding answers. A previous folder's data to take back, or the CV
// (chosen, or dropped: pywebview gives the dropped file's path to Python, which calls
// cvDepose), then the form prefilled from it; once the profile is written the window
// restarts on it. Until 3.77 these were customtkinter windows before this one.
let enBienvenue = false;

async function bienvenue(b) {
  enBienvenue = true;
  document.body.classList.add("sans-profil");
  await appel("textes").then(chargerCatalogue).catch(() => { /* French */ });
  if (b.message) toast(b.message.replace(/^!/, ""), b.message.startsWith("!"));
  if (b.cv) formulaireProfil(b.cv);
  else if (b.reprise && b.reprise.length) ecranReprise(b);
  else ecranCv();
  affiche();
}

function carteBienvenue(...enfants) {
  $("vue").replaceChildren(h("div", { class: "bienvenue" }, h("div", { class: "verre panneau" }, ...enfants)));
}

const plusTard = () => appel("plus_tard");

function ecranReprise(b) {
  const msg = h("p", { class: "erreur-texte", role: "alert" });
  const reprendre = async (dossier) => {
    msg.textContent = "Copie en cours…";
    const r = await appel("reprendre", dossier);
    if (r && r.ok === false) msg.textContent = r.erreur;
  };
  carteBienvenue(
    h("h1", { class: "grand-titre" }, "Bon retour"),
    h("p", { class: "sous" }, "Ce dossier est vide, mais un autre JobHunter a déjà ton profil. Reprends ses données (profil, CV, offres, candidatures) : elles sont copiées ici, l'ancien dossier ne change pas."),
    h("div", { class: "reprises" }, b.reprise.map((r) => h("div", { class: "reprise" },
      h("div", { class: "coupe" }, h("div", { translate: "no" }, r.dossier), h("div", { class: "sous" }, `profil du ${r.date}`)),
      bouton("Reprendre", "", () => reprendre(r.dossier), "plein")))),
    msg,
    h("div", { class: "boutons" },
      bouton("Autre dossier…", "", async () => {
        const c = await appel("choisir_ancien_dossier");
        if (c && c.erreur) msg.textContent = c.erreur;
        else if (c && c.dossier) reprendre(c.dossier);
      }),
      bouton("Nouveau profil", "", () => ecranCv())));
}

function ecranCv(erreur = "") {
  const msg = h("p", { class: "erreur-texte", role: "alert" }, erreur);
  const choisir = async () => {
    const c = await appel("choisir_cv");
    if (c && c.erreur) msg.textContent = c.erreur;
    else if (c && c.cv) formulaireProfil(c.cv);
  };
  const zone = h("div", { class: "depot-cv", tabindex: 0, role: "button", onclick: choisir,
    onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choisir(); } } },
  h("strong", {}, "Dépose ton CV ici"), h("span", {}, "PDF ou Word"));
  for (const t of ["dragenter", "dragover"]) zone.addEventListener(t, (e) => { e.preventDefault(); zone.classList.add("survol"); });
  for (const t of ["dragleave", "drop"]) zone.addEventListener(t, () => zone.classList.remove("survol"));
  carteBienvenue(
    h("h1", { class: "grand-titre" }, "Bienvenue"),
    h("p", { class: "sous" }, "Aucun profil pour l'instant. Donne ton CV, en PDF (ou en Word) : JobHunter le lit puis te pose quelques questions."),
    zone, msg,
    h("div", { class: "boutons" }, bouton("Choisir mon CV…", "", choisir, "plein"), bouton("Plus tard", "", plusTard)));
}

// Called by Python (web/__main__.py) with the path of a file dropped on the window.
function cvDepose(chemin) {
  if (!enBienvenue) return;
  if (/\.(pdf|docx)$/i.test(chemin || "")) formulaireProfil(chemin);
  else ecranCv("Ce n'est pas un CV PDF ou Word : dépose-en un autre.");
}

async function formulaireProfil(cv) {
  carteBienvenue(h("h1", { class: "grand-titre" }, "Lecture du CV…"));
  const l = await appel("lire_cv", cv);
  if (!l || !l.ok) return ecranCv((l && l.erreur) || "");
  const p = l.propositions;
  const rep = { ...p, villes: "", secondaires: [], etranger: false, pays_etrangers: "" };
  const msg = h("p", { class: "erreur-texte", role: "alert" });
  const champ = (cle, lib, type = "text") => h("label", { class: "champ-form" }, h("span", {}, lib),
    h("input", { type, value: rep[cle] ?? "", oninput: (e) => { rep[cle] = e.target.value; } }));
  const coches = (cle) => h("div", { class: "secteurs" }, l.secteurs.map(([code, lib]) =>
    h("label", { class: "case-colonne" }, h("input", { type: "checkbox", checked: rep[cle].includes(code),
      onchange: (e) => { rep[cle] = e.target.checked ? [...rep[cle], code] : rep[cle].filter((x) => x !== code); } }), lib)));
  const coche = (cle, lib) => h("label", { class: "case-colonne" },
    h("input", { type: "checkbox", checked: !!rep[cle], onchange: (e) => { rep[cle] = e.target.checked; } }), lib);
  const pays = h("label", { class: "champ-form", hidden: true }, h("span", {}, "Pays ou régions"),
    h("input", { placeholder: "ex. : Suisse, Belgique, Europe, monde", oninput: (e) => { rep.pays_etrangers = e.target.value; } }));
  const ou = h("div", { class: "ou" });
  const dessinerOu = () => ou.replaceChildren(segment([[false, `Seulement en ${l.pays}`], [true, "Aussi à l'étranger"]], rep.etranger,
    (v) => { rep.etranger = v; pays.hidden = !v; dessinerOu(); }));
  dessinerOu();
  const genre = h("div", {});
  const dessinerGenre = () => genre.replaceChildren(segment([["m", "« diplômé »"], ["f", "« diplômée »"]], rep.genre,
    (v) => { rep.genre = v; dessinerGenre(); }));
  dessinerGenre();
  const parcours = h("textarea", { class: "champ-texte", rows: 5, oninput: (e) => { rep.parcours = e.target.value; } });
  parcours.value = rep.parcours || "";
  const source = h("span", { class: "sous" }, "Tiré de ton CV. Tu as déjà une lettre que tu aimes ? Reprends-en le paragraphe.");
  const word = l.pdf ? [
    h("div", { class: "boutons" }, coche("word", "Adapter mon CV à chaque offre"),
      bouton("Voir la version Word", "", async () => {
        const r = await appel("apercu_word", cv);
        if (r && r.ok === false) msg.textContent = r.erreur;
      })),
    h("p", { class: "sous" }, "Un PDF ne se modifie pas : il partirait identique pour chaque offre. JobHunter en refait une version Word, plus sobre, où les compétences demandées passent en premier. Ton PDF reste à côté ; décoche pour l'envoyer tel quel."),
  ] : [];
  const boutons = h("div", { class: "boutons" },
    bouton("Créer mon profil", "", async () => {
      msg.textContent = "";
      boutons.querySelectorAll("button").forEach((b) => { b.disabled = true; });
      const attente = h("p", { class: "sous" }, "Création du profil…");
      boutons.after(attente);
      const r = await appel("creer_mon_profil", cv, rep);
      if (!r || r.ok === false) {
        attente.remove();
        boutons.querySelectorAll("button").forEach((b) => { b.disabled = false; });
        msg.textContent = (r && r.erreur) || "Le profil n'a pas été créé.";
      }
    }, "plein"),
    bouton("Choisir un autre CV…", "", () => ecranCv()),
    bouton("Plus tard", "", plusTard));
  carteBienvenue(
    h("h1", { class: "grand-titre" }, "Ton profil"),
    h("p", { class: "sous", translate: "no" }, l.nom),
    l.peu ? h("p", { class: "erreur-texte" }, l.peu) : null,
    h("p", { class: "sous" }, "Vérifie et complète : rien n'est écrit tant que tu n'as pas validé."),
    h("div", { class: "formulaire" },
      champ("prenom", "Prénom"), champ("nom", "Nom"), champ("email", "Email"), champ("telephone", "Téléphone"),
      champ("ville", "Ville"), champ("metiers", "Métiers visés"), champ("annees", "Années d'expérience", "number"),
      h("div", { class: "champ-form" }, h("span", {}, "Accords"), genre)),
    h("p", { class: "sous" }, "Métiers séparés par des virgules ; années d'expérience stages compris ; les accords sont ceux de tes lettres."),
    sousTitre("Secteurs prioritaires"), coches("prioritaires"),
    sousTitre("Secteurs secondaires (facultatif)"), coches("secondaires"),
    h("label", { class: "champ-form" }, h("span", {}, "Autres villes"),
      h("input", { placeholder: "facultatif, séparées par des virgules", oninput: (e) => { rep.villes = e.target.value; } })),
    sousTitre("Où chercher"), ou, pays,
    coche("entreprises", "Suivre les ~90 entreprises de finance / ESG proposées"),
    sousTitre("Ton CV et tes lettres"), ...word,
    h("p", { class: "sous" }, "Le paragraphe de parcours de tes lettres"), parcours,
    h("div", { class: "boutons" }, bouton("Reprendre celui de ma lettre…", "", async () => {
      const r = await appel("parcours_de_ma_lettre");
      if (!r || r.annule) return;
      if (r.erreur) { source.textContent = r.erreur; return; }
      parcours.value = r.parcours; rep.parcours = r.parcours;
      source.textContent = `Repris de ${r.source}. Relis-le.`;
    }), source),
    msg, boutons);
}

// Native window: no Windows frame, our own title bar over a see-through background.
function natif() {
  document.body.classList.add("natif");
  appel("reglages").then(appliquerReglages).catch(() => { /* defaults from style.css */ });
  // Remote Desktop: no blur, no motion (style.css, body.leger).
  appel("session").then((s) => {
    document.body.classList.toggle("leger", !!(s && s.distance));
    // `jobhunter sandbox` (3.85): always say that this window is not the real one.
    if (s && s.bac_a_sable) $("barre").prepend(h("span", { class: "bac-a-sable", title: "Données fictives, web coupé : rien de réel n'est lu ni modifié." }, "Bac à sable"));
  }).catch(() => {});
  suivreTache();  // a task started before a reload keeps being followed
  for (const b of document.querySelectorAll(".feux button")) {
    b.addEventListener("click", () => window.pywebview.api.fenetre(b.dataset.action).then(iconePlein));
  }
  $("barre").addEventListener("dblclick", (e) => {
    if (!e.target.closest("button")) window.pywebview.api.fenetre("agrandir").then(iconePlein);
  });
  window.pywebview.api.fenetre("etat").then(iconePlein);
  window.pywebview.api.bienvenue().then((b) => {
    if (b && !b.profil) return bienvenue(b);  // no profile yet: the welcome (3.78)
    if (b && b.message) toast(b.message.replace(/^!/, ""), b.message.startsWith("!"));
    demarrer();
    annonceMaj();
  }).catch(() => { demarrer(); annonceMaj(); });  // never a blank window
  window.pywebview.api.demarrage().then((m) => { if (m) toast(m, m.startsWith("!")); });
  suivreFond();
}

// Full screen: the button shows two windows (« back to a window »), as Windows does;
// in a window, one square (the user, 2026-11-02).
function iconePlein(plein) {
  const b = document.querySelector('.feux [data-action="agrandir"]');
  if (!b || typeof plein !== "boolean") return;
  b.innerHTML = plein
    ? '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="4" width="6" height="6" rx="1.2"/><path d="M4 4V3.2C4 2.5 4.5 2 5.2 2H8.8C9.5 2 10 2.5 10 3.2V6.8C10 7.5 9.5 8 8.8 8H8"/></svg>'
    : '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.5" y="2.5" width="7" height="7" rx="1.5"/></svg>';
  b.title = plein ? "Revenir à une fenêtre" : "Plein écran";
  b.setAttribute("aria-label", b.title);
}

// The background work (web.background): its news as toasts, the screen redrawn when
// it changed the data (descriptions, synced documents, new offers).
let versionFond = null;  // null until the first poll: no redraw at start
let vuFond = null;  // the last message seen; null until the first poll (no old news)
async function suivreFond() {
  const e = await window.pywebview.api.fond_etat().catch(() => null);
  if (e) {
    const m = e.messages[e.messages.length - 1];
    const cle = m ? m.heure + m.texte : "";
    // Only a failure is worth a toast: the progress is in the activity panel.
    if (vuFond !== null && cle && cle !== vuFond && m.texte.startsWith("!")) toast(m.texte, true);
    vuFond = cle;
    if (versionFond !== null && e.version !== versionFond) redessinerDonnees();
    versionFond = e.version;
    etatFond = e;
    dessinerActivite();
  }
  // Every 2 s while something runs in the background (its progress bar), else 20 s.
  setTimeout(suivreFond, e && e.activite ? 2000 : 20000);
}

if (window.pywebview) natif();
else window.addEventListener("pywebviewready", natif);
// Outside pywebview the event never comes: start on the demo after a short wait.
setTimeout(() => { if (!window.pywebview && !courant) demarrer(); }, 300);
