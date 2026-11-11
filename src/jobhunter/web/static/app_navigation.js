// --- Navigation ---------------------------------------------------------------------

let courant = null;
// Display settings: --t drives every see-through surface of the native window (style.css).
let reglagesCourants = null;
function appliquerReglages(r) {
  if (!r) return;
  reglagesCourants = r;
  document.body.classList.toggle("menu-replie", r.menu === "etroit");
  if (r.par_page) filtresOffres.par_page = r.par_page;
  document.body.style.setProperty("--t", String(r.verre / 100));
  document.body.classList.toggle("sans-fond", r.fond === "aucun");
  document.body.dataset.teinte = r.teinte || "terre";
  modeAffiche = r.mode || "auto";
  appliquerMode();
  document.body.style.setProperty("--police", (POLICES.find(([v]) => v === r.police) || POLICES[0])[2]);
}

// One display setting changed outside the settings screen (menu, page size): the whole
// set goes back, since a missing key would be reset to its default.
async function garderReglage(maj) {
  if (!reglagesCourants || !window.pywebview) return;
  reglagesCourants = { ...reglagesCourants, ...maj };
  reglagesCourants = (await window.pywebview.api.regler(reglagesCourants)) || reglagesCourants;
}

// The side menu folded to its icons, for more room (the user, 2026-10-27).
function basculerMenu() {
  const replie = document.body.classList.toggle("menu-replie");
  garderReglage({ menu: replie ? "etroit" : "large" });
}

// Light or dark: "auto" follows Windows (WebView2 passes its setting to the page).
let modeAffiche = "auto";
const systemeSombre = window.matchMedia("(prefers-color-scheme: dark)");
function appliquerMode() {
  const sombre = modeAffiche === "sombre" || (modeAffiche === "auto" && systemeSombre.matches);
  document.documentElement.classList.toggle("mode-sombre", sombre);  // not "sombre": the dark card
}
systemeSombre.addEventListener("change", appliquerMode);
appliquerMode();
const MODES = [["auto", "Comme Windows"], ["clair", "Clair"], ["sombre", "Sombre"]];

// [value, label, CSS stack]: fonts every Windows 11 has, nothing to download.
const POLICES = [
  ["segoe", "Segoe", '"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif'],
  ["bahnschrift", "Bahnschrift", 'Bahnschrift, "Segoe UI", sans-serif'],
  ["corbel", "Corbel", 'Corbel, "Segoe UI", sans-serif'],
  ["sitka", "Sitka", '"Sitka Text", Sitka, Georgia, serif'],
  ["georgia", "Georgia", 'Georgia, "Times New Roman", serif'],
];
// [value, label, the three colours of its swatch]
const TEINTES = [
  ["terre", "Terre", ["#eaa476", "#c98366", "#a8766b"]],
  ["vert", "Vert", ["#a9d4b4", "#6fa98a", "#4e7f6a"]],
  ["bleu", "Bleu", ["#9fc4ec", "#6b97cf", "#4b6fa8"]],
  ["noir", "Noir et blanc", ["#d4d4d4", "#5e5e5e", "#161616"]],
];

const FONDS = [["acrylique", "Acrylique"], ["net", "Net"], ["mica", "Mica"], ["aucun", "Aucun"]];

ECRANS.reglages = {
  titre: "Réglages",
  actions: () => [],
  async dessiner(vue) {
    let r = (await appel("reglages")) || { fond: "acrylique", verre: 50, teinte: "terre", police: "segoe", mode: "auto" };
    const enregistrer = async (maj) => {
      r = { ...r, ...maj };
      appliquerReglages(r);
      if (window.pywebview) r = await window.pywebview.api.regler(r);
    };
    const valeur = h("span", { class: "compte" }, `${r.verre} %`);
    const curseur = h("input", {
      type: "range", min: 0, max: 100, step: 5, value: r.verre, class: "curseur",
      style: `--p:${r.verre}%`, disabled: r.fond === "aucun",
      oninput: (e) => {
        const v = Number(e.target.value);
        valeur.textContent = `${v} %`;
        e.target.style.setProperty("--p", `${v}%`);
        appliquerReglages({ ...r, verre: v });
      },
      onchange: (e) => enregistrer({ verre: Number(e.target.value) }),
    });
    const place = h("div");
    const dessinerFond = () => place.replaceChildren(segment(FONDS, r.fond, async (v) => {
      await enregistrer({ fond: v });
      curseur.disabled = v === "aucun";
      dessinerFond();
    }));
    dessinerFond();
    const teintes = h("div", { class: "nuancier" });
    const dessinerTeintes = () => teintes.replaceChildren(...TEINTES.map(([v, lib, c]) =>
      h("button", { class: `nuance ${v === r.teinte ? "on" : ""}`, title: lib, onclick: async () => { await enregistrer({ teinte: v }); dessinerTeintes(); } },
        h("span", { class: "pastille", style: `background:linear-gradient(135deg, ${c[0]}, ${c[1]} 55%, ${c[2]})` }), lib)));
    dessinerTeintes();
    const placeMode = h("div");
    const dessinerMode = () => placeMode.replaceChildren(segment(MODES, r.mode || "auto", async (v) => { await enregistrer({ mode: v }); dessinerMode(); }));
    dessinerMode();
    const polices = h("div", { class: "polices" });
    const dessinerPolices = () => polices.replaceChildren(...POLICES.map(([v, lib, pile]) =>
      h("button", { class: `police ${v === r.police ? "on" : ""}`, onclick: async () => { await enregistrer({ police: v }); dessinerPolices(); } },
        h("span", { class: "exemple", style: `font-family:${pile}` }, "Aa"), lib)));
    dessinerPolices();
    const placePc = h("div");
    const dessinerPc = () => placePc.replaceChildren(segment([["non", "Masqués"], ["oui", "Affichés"]], r.pourcentages ? "oui" : "non",
      async (v) => { await enregistrer({ pourcentages: v === "oui" }); dessinerPc(); }));
    dessinerPc();
    // Columns of cards at their own height (style.css .mosaique): in the grid, each card
    // stretched to the tallest of its row (Langue, three lines, as tall as Couleurs) and
    // Données sat alone on the last row (the user, 2026-11-05: « tous les espaces vides,
    // dans et en dehors des widgets »). Outils, full width, comes after.
    const cartes = [
      // The tallest first: the browser balances the columns in this order.
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Couleurs et police")),
        h("div", { class: "reglage" }, h("div", { class: "nom-reglage" }, "Mode"), placeMode),
        h("div", { class: "reglage" }, h("div", { class: "nom-reglage" }, "Couleur"), teintes),
        h("div", { class: "reglage" }, h("div", { class: "nom-reglage" }, "Police"), polices),
        h("div", { class: "reglage" },
          h("div", {}, h("div", { class: "nom-reglage" }, "Pourcentages dans Statistiques"),
            h("div", { class: "sous" }, "La part de chaque ligne et les taux de réponse.")),
          placePc)),
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Apparence")),
        h("div", { class: "reglage" },
          h("div", {}, h("div", { class: "nom-reglage" }, "Fond de la fenêtre"),
            h("div", { class: "sous" }, "Acrylique : le bureau, flouté. Net : le bureau tel quel. Mica : une teinte douce. Aucun : opaque.")),
          place),
        h("div", { class: "reglage" },
          h("div", { class: "titre-ligne" }, h("div", { class: "nom-reglage" }, "Transparence"), valeur),
          h("div", { class: "ligne-curseur" }, h("span", {}, "Opaque"), curseur, h("span", {}, "Verre")),
          h("div", { class: "sous" }, "Combien le bureau transparaît derrière le fond de la fenêtre ; les cartes et les textes restent nets. La force du flou acrylique est fixée par Windows."))),
      ...((await cartesParametres()) || []),
      ...(await cartesMaintenance()),
    ].flatMap((c) => c.classList.contains("pile") ? [...c.children] : [c]);  // the grid's piles: one card each here
    const larges = cartes.filter((c) => c.classList.contains("large"));
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "mosaique" }, cartes.filter((c) => !larges.includes(c))),
      larges,
      window.pywebview ? null : h("div", { class: "verre panneau" },
        h("div", { class: "sous" }, "Aperçu navigateur : ces réglages ne s'enregistrent que dans l'application."))));
  },
};

// The desktop's Paramètres page: language, update, daily collection, profiles.
async function verifierMaj(ev) {
  if (!window.pywebview) return toast(HORS_APPLI, true);
  const b = ev && ev.currentTarget;
  if (b) b.disabled = true;
  let v = {};
  try { v = (await window.pywebview.api.mise_a_jour()) || {}; }
  catch (e) { v = {}; }
  finally { if (b) b.disabled = false; }
  if (!v.derniere) return toast("Impossible de joindre le serveur des mises à jour : réessaie plus tard.", true);
  if (v.store) {
    // Installed from here, no Store window (3.74): JobHunter closes and opens again.
    // The Store's answer, not GitHub's: a release reaches it once Microsoft certified it.
    if (v.erreur) return toast(`Le Microsoft Store ne répond pas (${v.erreur}) : réessaie plus tard.`, true);
    const certif = v.attente ? ` La ${v.attente} arrive dans le Microsoft Store après sa vérification par Microsoft (quelques heures à quelques jours).` : "";
    if (!v.nouvelle) return toast(`À jour : ${v.installee}.${certif}`);
    const ok = await dialogue(`Version ${v.derniere} disponible`, `Installée : ${v.installee}. JobHunter se ferme pendant l'installation puis se rouvre de lui-même.`,
      null, [["Installer", "plein", () => true]]);
    if (ok) await lancer("maj");
    return;
  }
  // v.attente: the latest, published but not signed yet (its author signs within the hour)
  const suite = v.attente ? ` La ${v.attente} sera proposée dès que son auteur l'aura signée.` : "";
  if (!v.nouvelle) return toast(`À jour : ${v.installee}.${suite}`);
  if (v.silencieux) {
    // The installer's copy: installed without its window, then JobHunter opens again.
    const oui = await dialogue(`Version ${v.derniere} disponible`, `Installée : ${v.installee}. Elle est vérifiée (signature), installée sans fenêtre, puis JobHunter se rouvre.${suite}`,
      null, [["Installer", "plein", () => true]]);
    if (oui) await installerMaj();
    return;
  }
  const ok = await dialogue(`Version ${v.derniere} disponible`, `Installée : ${v.installee}. Elle est vérifiée (signature) avant d'être installée ; relance JobHunter ensuite.${suite}`,
    null, [["Installer", "plein", () => true]]);
  if (!ok) return;
  await lancer("maj");  // suivreTache → suivreMaj: the button and the Moteur card follow it
}

// The downloaded installer runs once the window has closed (setup_update).
async function installerMaj() {
  toast("Vérification de la mise à jour…");
  const r = await appel("installer_maj").catch(() => null);
  if (!r || !r.ok) toast((r && r.message) || "Mise à jour impossible : réessaie plus tard.", true);
}

// At start-up: a newer signed version shows as a button in the title bar.
// Again every 6 hours while the window stays open: a window left open for days saw no
// release at all (audit of 2026-11-06; Chrome checks every 5 h at most, MSIX every 8).
// annonce_maj downloads a version once: asked again, a ready one is only confirmed.
const MAJ_TOUTES_LES = 6 * 3600 * 1000;
let majMinuteur = null;
async function annonceMaj() {
  if (!majMinuteur) majMinuteur = setInterval(annonceMaj, MAJ_TOUTES_LES);
  const v = await appel("annonce_maj").catch(() => null);
  if (!v) return;
  const b = $("maj");
  // v.pret: downloaded (and checked) in the background; closing the window installs it too.
  // The Store's: its click installs through the Store task (verifierMaj), JobHunter reopens.
  b.textContent = v.pret ? `Redémarrer pour mettre à jour (${v.derniere})` : `Mettre à jour (${v.derniere})`;
  b.title = v.pret ? `Version installée : ${v.installee}. Prête : elle s'installe aussi à la fermeture de JobHunter.` : `Version installée : ${v.installee}`;
  b.hidden = false;
  b.onclick = v.pret && !v.store ? (() => installerMaj()) : clicMaj;
}
function clicMaj(ev) {
  if (ev.currentTarget.dataset.fait) return toast("Ferme JobHunter puis rouvre-le : la nouvelle version démarre.");
  return verifierMaj(ev);
}

async function cartesParametres() {
  const p = await appel("parametres");
  if (!p) return null;
  const relire = () => redessiner();
  const langue = h("select", { class: "choix", onchange: async (e) => {
    if (await ecrire("choisir_langue", e.target.value)) location.reload();  // the page redraws in it
  } }, Object.entries(p.langues).map(([c, n]) => h("option", { value: c, selected: c === p.langue }, n)));
  const heure = h("input", { class: "champ-texte", type: "time", value: "08:00", style: "width:120px" });
  const planif = !p.planif.disponible
    ? h("div", { class: "sous" }, "Planification disponible sous Windows (ailleurs : schedule.sh).")
    : p.planif.planifiee
      ? h("div", { class: "ligne-actions" }, h("span", { class: "etat ok" }, "Planifiée"),
          bouton("Retirer la collecte automatique", "", async () => {
            const ok = await dialogue("Retirer la collecte automatique ?", "Les offres ne seront plus collectées chaque jour.", null, [["Retirer", "chaud", () => true]]);
            if (ok && await ecrire("planifier", "")) { toast("Collecte automatique retirée."); relire(); }
          }))
      : h("div", { class: "ligne-actions" }, h("span", { class: "etat" }, "Pas planifiée"), heure,
          bouton("Collecter chaque jour à cette heure", "horloge", async () => {
            const r = await ecrire("planifier", heure.value);
            if (r) { toast(r.message || "Collecte planifiée."); relire(); }
          }, "plein"));
  return [
    h("div", { class: "pile" },
      carte("Langue",
        h("div", { class: "sous", style: "margin-bottom:10px" }, "Langue de l'interface, dans les deux fenêtres. Les lettres et les messages gardent la leur."), langue)),
    carte("Collecte automatique",
      h("div", { class: "sous", style: "margin-bottom:10px" }, "Chaque jour à l'heure choisie, l'ordinateur collecte les offres de tous tes profils, même si JobHunter est fermé."),
      planif),
  ];
}

// The Profiles panel (the user, 2026-10-27: « gérer les profils doit mener au panneau
// profils pour en changer un ou en rajouter un »): open one, add one, rename, archive.
async function gererProfils() {
  const corps = $("tiroir-corps");
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
  const p = await appel("parametres");
  if (!p) return corps.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  const liste = p.profils.length ? p.profils : [{ slug: "", nom: "Principal" }];
  const nomDe = (x) => (!x.slug && p.titulaire) || x.nom;
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Profils"),
      h("div", { class: "sous" }, "Un profil = une recherche à part : un autre métier, une autre ville, ou une autre personne. Chacun a ses offres, ses CV et ses lettres ; les clés des sites restent communes. Changer de profil relance la fenêtre."))),
    h("div", { class: "liste-profils" }, liste.map((x) =>
      h("div", { class: `ligne-profil ${x.slug === p.actif ? "on" : ""}` },
        h("span", { class: "t", translate: "no" }, nomDe(x)),
        x.slug === p.actif ? h("span", { class: "etiq gris" }, "ouvert")
          : bouton("Ouvrir", "sortie", () => ecrire("changer_profil", x.slug))))),
    h("div", { class: "boutons" },
      bouton("Nouveau profil depuis un CV…", "profil", () => { fermerTiroir(); nouveauProfil(); }, "plein"),
      p.actif ? bouton("Renommer", "", async () => {
        const champ = h("input", { class: "champ-texte", value: (p.profils.find((x) => x.slug === p.actif) || {}).nom || "" });
        const nom = await dialogue("Renommer le profil", "Seul le nom affiché change ; son dossier reste le même.", champ, [["Renommer", "plein", () => champ.value.trim() || undefined]]);
        if (nom && await ecrire("renommer_profil", nom)) gererProfils();
      }) : null,
      p.actif ? bouton("Archiver ce profil", "", async () => {
        const ok = await dialogue("Archiver ce profil ?", "Il est déplacé dans profiles/_archives (rien n'est supprimé), puis le profil principal s'ouvre.", null, [["Archiver", "chaud", () => true]]);
        if (ok) ecrire("archiver_profil");
      }) : null));
}

async function nouveauProfil() {
  const champ = h("input", { class: "champ-texte", placeholder: "par exemple : Chargée RSE à Lyon" });
  const nom = await dialogue("Nouveau profil", "1. Donne-lui un nom. 2. Choisis le CV de cette recherche (.docx ou .pdf). 3. La fenêtre s'ouvre sur ce nouveau profil, avec un formulaire rempli d'après le CV : vérifie, complète, valide. Ton profil actuel ne change pas.",
    champ, [["Choisir le CV…", "plein", () => champ.value.trim() || undefined]]);
  if (!nom) return;
  await ecrire("nouveau_profil", nom);  // the window restarts in the new profile's folder
}

async function aller(nom) {
  if (nom === "maintenance") nom = "reglages";  // merged into Réglages (3.82): a saved screen
  if (!ECRANS[nom]) nom = "accueil";
  courant = nom;
  fermerTiroir();
  // Relances: a page of Candidatures; the daily triage, one of Offres.
  const lien = { relances: "candidatures", tri: "offres" }[nom] || nom;
  for (const a of document.querySelectorAll(".menu a")) {
    a.classList.toggle("actif", a.dataset.ecran === lien);
    if (a.dataset.ecran === lien) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  const e = ECRANS[nom];
  $("titre").textContent = e.titre;
  $("actions").replaceChildren(...e.actions());
  const vue = $("vue");
  vue.scrollTop = 0;
  // A list screen keeps its filters in place: its list scrolls inside its panel, not the
  // page (the user, 2026-10-27). style.css: .vue.plein.
  vue.classList.toggle("plein", typeof e.plein === "function" ? e.plein() : !!e.plein);
  vue.dataset.ecran = nom;  // style.css: .vue[data-ecran=…]
  try { localStorage.setItem("jh-ecran", nom); } catch (_) { /* no storage: fine */ }
  // A screen reading the whole queue takes a second: the old one stayed in place under
  // the new title, as if the click had done nothing (2026-11-03). Past 150 ms, say so.
  const attente = setTimeout(() => {
    if (courant === nom) vue.replaceChildren(h("div", { class: "vide chargement" }, "Chargement…"));
  }, 150);
  try {
    await e.dessiner(vue);
  } catch (err) {
    console.error(err);
    vue.replaceChildren(h("div", { class: "vide" }, "Impossible de charger cet écran."));
  } finally {
    clearTimeout(attente);
  }
}

// Top left: the open profile, a round badge and its name; a click lists the others.
// The main profile shows its holder's name ("Principal" says little).
async function marqueProfil() {
  let p;
  try { p = await appel("parametres"); } catch (_) { return; }  // preview: "JobHunter" stays
  if (!p) return;
  const liste = p.profils.length ? p.profils : [{ slug: "", nom: "Principal" }];
  const ouvert = liste.find((x) => x.slug === p.actif) || liste[0];
  const nom = (!ouvert.slug && p.titulaire) || ouvert.nom;
  const initiales = (n) => n.split(/[\s\-_]+/).filter(Boolean).slice(0, 2).map((m) => m[0].toUpperCase()).join("");
  const rond = (n) => h("span", { class: "rond-profil", translate: "no" }, initiales(n));
  const menu = h("div", { class: "menu-profils" });
  // A press inside the badge or the list keeps it open: closing on it removed the list
  // before its click, and « Gérer les profils… » did nothing (the user, 2026-10-27).
  const fermer = (e) => {
    if (e && (marque.contains(e.target) || menu.contains(e.target))) return;
    menu.remove();
    document.removeEventListener("mousedown", fermer);
  };
  const marque = h("button", { class: "marque", title: "Changer de profil", onclick: () => {
    if (menu.isConnected) return fermer();
    menu.replaceChildren(
      h("div", { class: "titre-profils" }, "Profils"),
      ...liste.map((x) => {
        const n = (!x.slug && p.titulaire) || x.nom;
        return h("button", { class: x.slug === p.actif ? "on" : "", onclick: () => {
          fermer();
          if (x.slug !== p.actif) ecrire("changer_profil", x.slug);
        } }, rond(n), h("span", { translate: "no" }, n), x.slug === p.actif ? h("span", { class: "etiq gris" }, "ouvert") : null);
      }),
      h("button", { class: "gerer", onclick: () => { fermer(); gererProfils(); } }, "Gérer les profils…"));
    marque.after(menu);
    document.addEventListener("mousedown", fermer);
  } }, rond(nom), h("span", { class: "nom-profil", translate: "no" }, nom));
  document.querySelector(".menu .marque").replaceWith(marque);
}

async function demarrer() {
  // The language first: the first screen is drawn already translated.
  await appel("textes").then(chargerCatalogue).catch(() => { /* French */ });
  for (const a of document.querySelectorAll(".menu a[data-icone]")) {
    a.prepend(svg(a.dataset.icone));
    a.href = `#${a.dataset.ecran}`;  // a link with an address: reached by Tab, opened by Enter
    a.addEventListener("click", (e) => { e.preventDefault(); aller(a.dataset.ecran); });
  }
  suivreTiroir();
  marqueProfil();
  $("menu").append(h("button", { class: "replier", title: "Replier ou déplier le menu", onclick: basculerMenu },
    svg("panneau"), h("span", {}, "Replier le menu")));
  $("voile").addEventListener("click", fermerTiroir);
  $("fermer-tiroir").addEventListener("click", fermerTiroir);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermerTiroir(); });
  let debut = "accueil";
  try { debut = localStorage.getItem("jh-ecran") || debut; } catch (_) { /* no storage */ }
  await aller(debut);
  affiche();
}

// The first screen is drawn: after a profile switch, the previous window, above this
// one, closes and shows it ready (Api.affiche). Two painted frames, not the DOM built:
// one switch in three showed the bare menu for 150 ms (filmed 2026-11-05). A timer as
// a net: a covered window might get no frame at all.
function affiche() {
  let dit = false;
  const dire = () => {
    if (dit || !window.pywebview) return;
    dit = true;
    window.pywebview.api.affiche().catch(() => {});
  };
  requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(dire, 30)));
  setTimeout(dire, 400);
}
