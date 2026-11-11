// --- Screens ------------------------------------------------------------------------

const ECRANS = {};

ECRANS.accueil = {
  titre: "Accueil",
  actions: () => [],
  async dessiner(vue) {
    const d = await appel("tableau");
    const col = d.collecte;
    const dernier = col.length ? col[col.length - 1] : { n: 0 };
    const avant = col.slice(0, -1);
    const moyenne = avant.length ? avant.reduce((s, c) => s + c.n, 0) / avant.length : 0;
    // Four steps of a round size, 1, 2, 5 or 25 times a power of ten: five distinct
    // whole ticks (an empty week showed 1, 1, 1, 0, 0), and no 0, 712, 1 424, 2 136.
    const brut = Math.max(1, Math.max(0, ...col.map((c) => c.n)) / 4);
    const puissance = 10 ** Math.floor(Math.log10(brut));
    const pas = (puissance >= 10 ? [1, 2, 2.5, 5, 10] : [1, 2, 5, 10]).map((m) => m * puissance).find((x) => x >= brut);
    const max = pas * 4;
    const pleins = [];
    const barres = h("div", { class: "barres" },
      [100, 75, 50, 25, 0].map((p) => h("div", { class: "axe", style: `top:calc(${1 - p / 100} * (100% - 22px))` },
        h("span", {}, nombre(Math.round(max * p / 100))))),
      col.map((c) => {
        const plein = h("div", { class: "plein", style: "height:0" });
        pleins.push([plein, Math.max(6, 100 * c.n / max)]);
        return h("div", { class: "col", title: `${nombre(c.n)} offres le ${dateFr(c.jour)}` },
          h("div", { class: "tube" }, plein), h("div", { class: "jour" }, jourCourt(c.jour)));
      }));

    vue.replaceChildren(h("div", { class: "accueil" },
      h("div", { class: "colonne" },
        h("div", { class: "verre stats" },
          // The pace first (the user, 2026-11-05): the queue's size called for nothing.
          [["avion", "Envoyées en 7 jours", d.stats.semaine, `${nombre(d.stats.semaine_avant)} les 7 jours d'avant`],
           ["cible", `Notées ${d.seuil || 8}+ à traiter`, d.stats.neuf],
           ["horloge", "En attente de réponse", d.stats.postulees]].map(([ic, lab, val, note]) =>
            h("div", { class: "stat" }, h("span", { class: "rond" }, svg(ic)),
              h("div", { style: "min-width:0" }, h("div", { class: "lab" }, lab),
                h("div", { class: "val" }, nombre(val), note ? h("span", { class: "note" }, note) : null))))),
        h("div", { class: "verre kpi" },
          h("div", {},
            h("div", { class: "titre-ligne", style: "margin:0" }, h("h2", {}, "Collecte du matin"),
              h("span", { class: "etiq gris" }, "7 derniers scans")),
            h("div", { class: "grand" }, `+${nombre(dernier.n)}`),
            h("div", { class: "ecart" }, moyenne
              ? `${dernier.n >= moyenne ? "+" : "−"}${Math.abs(Math.round(100 * (dernier.n - moyenne) / moyenne))} % par rapport à la moyenne`
              : ""),
            // One or two bars draw no trend: say when the curve will come instead.
            col.length >= 3 ? barres : h("div", { class: "vide" }, "La courbe apparaîtra après trois collectes.")),
          h("div", { class: "carte liste-meilleures" },
            h("div", { class: "titre-ligne", style: "margin:0" }, h("h3", {}, "Meilleures offres")),
            h("ol", {}, d.meilleures.map((o) =>
              h("li", { onclick: () => ouvrirOffre(`${o.entreprise}|${o.poste}`), title: o.poste },
                h("span", { class: classeScore(o.fit) }, nombre(o.fit)),
                h("div", { style: "min-width:0" }, h("div", { class: "t" }, o.poste), h("div", { class: "s" }, o.entreprise))))),
            h("button", { class: "bouton", style: "margin-top:18px;width:100%;justify-content:center", onclick: () => aller("offres") }, "Toutes les offres"))),
        h("div", { class: "verre panneau" },
          h("div", { class: "titre-ligne" }, h("h2", {}, "Candidatures récentes"),
            h("button", { class: "bouton", onclick: () => aller("candidatures") }, "Tout voir")),
          tableCandidatures(d.candidatures))),
      h("div", { class: "colonne" },
        h("div", { class: "sombre" }, h("h2", {}, "À faire"),
          h("ul", { class: "fil" },
            d.a_trier ? h("li", { onclick: () => aller("tri") },
              h("div", { class: "t" }, "Trier les nouvelles offres"),
              h("div", { class: "s" }, `${nombre(d.a_trier)} offres notées ${d.seuil || 8}+ jamais ouvertes`)) : null,
            // Offers with their CV and letter ready, not applied to yet: what to do next.
            // The follow-ups left this list (the user, 2026-11-02: « pas très importantes »).
            (d.a_postuler || []).length
            ? d.a_postuler.map((o) => h("li", { onclick: () => ouvrirOffre(`${o.entreprise}|${o.poste}`) },
                h("div", { class: "t" }, `Postuler chez ${o.entreprise}`),
                h("div", { class: "s", title: o.poste }, `${nombre(o.fit)} · ${o.poste}`)))
            : d.a_trier || d.cle_conseillee ? null : h("li", { class: "vide" }, "Rien à faire pour l'instant"),
            // A free key missing: for a waiter or a nurse, most of the offers. Last, and
            // one day in three when there is something else to do (api.cle_du_jour).
            d.cle_conseillee ? h("li", { onclick: () => saisirCle(d.cle_conseillee.nom, () => aller("accueil")) },
              h("div", { class: "t" }, `Ajouter la clé ${d.cle_conseillee.libelle}`),
              h("div", { class: "s" }, "Gratuite, 5 minutes : beaucoup plus d'offres")) : null)),
        carteRetours(d.retours),
        carteDocumentsAccueil(d.documents))));
    requestAnimationFrame(() => requestAnimationFrame(() => pleins.forEach(([e, p]) => { e.style.height = `${p}%`; })));
    ajusterAccueil(vue);
  },
};

// The home screen fits the window it opens in (the user, 2026-10-28: « éviter de couper
// les widgets quand on ouvre l'app »): whole items are put away, the least useful first —
// best offers beyond three, recent applications beyond one; on the right, zones beyond
// one, tasks beyond two, then the Documents button (also in the menu) — never a panel cut
// by the window's edge. Each column for itself. In one column (narrow window) the page
// scrolls.
function ajusterAccueil(vue) {
  const accueil = vue.querySelector(".accueil");
  if (!accueil) return;
  accueil.querySelectorAll(".range").forEach((e) => e.classList.remove("range"));
  // The best offers, as many as the chart beside them is tall: more stretched the card
  // past the chart, fewer left a hole under them (the user, 2026-11-05: « des endroits vides »).
  const kpi = accueil.querySelector(".kpi");
  const liste = kpi && kpi.querySelector(".liste-meilleures");
  if (liste && getComputedStyle(kpi).gridTemplateColumns.split(" ").length > 1) {
    const contenu = (el) => {
      const r = el.getBoundingClientRect();
      return el.lastElementChild.getBoundingClientRect().bottom - r.top + parseFloat(getComputedStyle(el).paddingBottom);
    };
    for (const li of [...liste.querySelectorAll("li")].slice(3).reverse()) {
      if (contenu(liste) <= contenu(kpi.firstElementChild) + 1) break;
      li.classList.add("range");
    }
  }
  if (getComputedStyle(accueil).gridTemplateColumns.split(" ").length < 2) return;
  // The visible edge, padding included (3.67: a fixed 8 px let the left column run 7 px
  // past the bottom of a low window, whose padding is 16).
  const bas = vue.getBoundingClientRect().bottom - parseFloat(getComputedStyle(vue).paddingBottom) + vue.scrollTop;
  const apres = (col, sel, garder) => [...col.querySelectorAll(sel)].slice(garder).reverse();
  const [gauche, droite] = accueil.querySelectorAll(":scope > .colonne");
  const etapes = [
    [gauche, [...apres(gauche, ".liste-meilleures li:not(.range)", 3), ...apres(gauche, "tbody tr", 1)]],
    [droite, [...apres(droite, ".retours .zone", 2), ...apres(droite, ".fil > li", 2),
              ...droite.querySelectorAll(".documents-accueil .boutons > :last-child")]],
  ];
  for (const [col, elements] of etapes) {
    for (const e of elements) {
      const avant = col.getBoundingClientRect().bottom;
      if (avant <= bas + 1) break;
      e.classList.add("range");
      // Put away only what gives back height: a best offer beside a taller chart gave
      // none, and only left a hole.
      if (col.getBoundingClientRect().bottom >= avant - 0.5) e.classList.remove("range");
    }
  }
}
window.addEventListener("resize", () => { if (courant === "accueil") ajusterAccueil($("vue")); });

// What the applications sent brought back (the user, 2026-11-05: « il manque quelque
// chose »), in place of « Par zone »: answers, interviews, silence, each as a share of
// the applications sent (funnel.entonnoir, as the Statistics screen).
function carteRetours(r) {
  if (!r) return null;
  const titre = [h("h2", {}, "Retours")];
  if (!r.envoyees) return h("div", { class: "zones retours" }, ...titre, h("div", { class: "sous" }, "Aucune candidature envoyée pour l'instant."));
  const part = (n) => Math.round(100 * n / r.envoyees);
  const delai = r.delai_median == null ? "" : ` · réponse en ${nombre(Math.round(r.delai_median))} j (médiane)`;
  return h("div", { class: "zones retours" }, ...titre,
    h("div", { class: "sous", style: "margin-bottom:16px" }, `${nombre(r.envoyees)} candidature${r.envoyees > 1 ? "s" : ""} envoyée${r.envoyees > 1 ? "s" : ""}${delai}`),
    [["Réponses", r.reponses, "Entretien ou refus"], ["Entretiens", r.entretiens, "Les réponses qui ont mené à un entretien"],
     ["Sans réponse", r.silence, "Envoyées il y a 30 jours et plus, sans réponse"]].map(([lab, n, explication]) =>
      aide(h("div", { class: "zone" },
        h("div", {}, h("div", { class: "lab" }, lab), h("div", { class: "val" }, nombre(n))),
        h("div", { class: "tuile" }, h("i", { style: `width:${part(n)}%` }), h("span", {}, `${part(n)} %`))), explication)));
}

// Bottom right of the home screen (the user, 2026-10-27: « remplissons le bas droit »):
// how many well-scored offers have their CV and letter, and the button to prepare more.
function carteDocumentsAccueil(d) {
  if (!d) return null;
  const pct = d.bonnes ? Math.round(100 * d.prets / d.bonnes) : 0;
  return h("div", { class: "zones documents-accueil" }, h("h2", {}, "CV et lettres"),
    h("div", { class: "sous", style: "margin-bottom:16px" }, `offres notées ${d.seuil || 8} et plus · ${nombre(d.a_preparer)} à préparer`),
    h("div", { class: "zone" },
      h("div", {}, h("div", { class: "lab" }, "Prêtes"), h("div", { class: "val" }, nombre(d.prets))),
      h("div", { class: "tuile" }, h("i", { style: `width:${pct}%` }), h("span", {}, `${pct} %`))),
    h("div", { class: "boutons", style: "margin-top:14px" },
      d.a_preparer ? action("Préparer les 30 meilleures", "plume", "documents_top", "plein") : null,
      bouton("Documents", "doc", () => aller("documents"))));
}

function tableCandidatures(lignes) {
  if (!lignes.length) return h("div", { class: "vide" }, "Aucune candidature pour l'instant.");
  return h("table", {},
    h("colgroup", {}, h("col", { style: "width:22%" }), h("col", { style: "width:34%" }), h("col", { style: "width:14%" }), h("col", { style: "width:15%" }), h("col", {})),
    h("thead", {}, h("tr", {}, ["Entreprise", "Poste", "Statut", "Le", "Score"].map((t) => h("th", {}, t)))),
    h("tbody", {}, lignes.map((c) =>
      h("tr", { onclick: () => ouvrirOffre(`${c.entreprise}|${c.poste}`) },
        h("td", {}, c.entreprise), h("td", { title: c.poste }, c.poste),
        h("td", {}, h("span", { class: `etiq ${c.statut}` }, c.statut)), h("td", { style: "white-space:nowrap" }, dateFr(c.date)),
        h("td", {}, c.fit == null ? "—" : h("div", { class: "prog", title: `${c.fit}/10` }, h("i", { style: `width:${c.fit * 10}%` })))))));
}

const sansAccent = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
// A filter of several values (the user, 2026-10-27): a button that says what is chosen,
// and a list of boxes with Apply. The list hangs on <body>: inside the filter bar, its
// scrolling and fade (mask) would clip it. Past a dozen values, a field narrows it.
const enListe = (v) => (Array.isArray(v) ? v : v ? [v] : []);
// `noms`: the name shown for a value (a domain's key -> its trade's name, 3.74).
function listeMulti(choisis, tous, valeurs, appliquer, lien = null, noms = {}) {
  const garde = new Set(choisis);
  const nom = (v) => noms[v] || v;
  const libelle = !choisis.length ? tous
    : choisis.length <= 2 ? choisis.map(nom).join(", ") : `${nom(choisis[0])} + ${choisis.length - 1}`;
  const bouton_ = h("button", { class: `choix multi${choisis.length ? " pris" : ""}`, title: choisis.join(", ") || tous }, libelle);
  const menu = h("div", { class: "menu-cherchable menu-multi" });
  const cherche = valeurs.length > 12 ? h("input", { type: "search", class: "champ-texte", placeholder: "Chercher…", autocomplete: "off" }) : null;
  const cases = h("div", { class: "cases" });
  const remplir = () => {
    const q = cherche ? sansAccent(cherche.value.trim()) : "";
    const vus = valeurs.filter((v) => sansAccent(nom(v)).includes(q));
    cases.replaceChildren(...(vus.length ? vus.slice(0, 300).map((v) => h("label", {},
      h("input", { type: "checkbox", checked: garde.has(v), onchange: (e) => { e.target.checked ? garde.add(v) : garde.delete(v); } }),
      h("span", {}, nom(v)))) : [h("div", { class: "sous" }, "Aucun résultat")]));
  };
  const placer = (e) => {
    if (e && menu.contains(e.target)) return;
    const r = bouton_.getBoundingClientRect();
    Object.assign(menu.style, { left: `${Math.max(12, Math.min(r.left, innerWidth - menu.offsetWidth - 12))}px`, top: `${r.bottom + 6}px`, minWidth: `${Math.max(r.width, 220)}px` });
  };
  const dehors = (e) => { if (!menu.contains(e.target) && !bouton_.contains(e.target)) finir(true); };
  const clavier = (e) => {
    if (e.key === "Enter") { e.preventDefault(); finir(true); } else if (e.key === "Escape") { e.stopPropagation(); finir(false); }
  };
  const finir = (garder) => {
    menu.remove();
    document.removeEventListener("scroll", placer, true);
    document.removeEventListener("mousedown", dehors, true);
    document.removeEventListener("keydown", clavier, true);
    const choix = valeurs.filter((v) => garde.has(v));
    if (garder && (choix.length !== choisis.length || choix.some((v) => !choisis.includes(v)))) appliquer(choix);
    else { garde.clear(); choisis.forEach((v) => garde.add(v)); }
  };
  if (cherche) cherche.addEventListener("input", remplir);
  menu.append(...(cherche ? [cherche] : []), cases, ...(lien ? [h("button", { class: "lien-multi", onclick: () => { finir(false); lien[1](); } }, lien[0])] : []), h("div", { class: "pied-multi" },
    h("button", { class: "bouton", onclick: () => { garde.clear(); remplir(); } }, "Tout effacer"),
    h("button", { class: "bouton plein", onclick: () => finir(true) }, "Appliquer")));
  bouton_.addEventListener("click", () => {
    if (menu.isConnected) return finir(true);
    remplir();
    document.body.append(menu);
    placer();
    document.addEventListener("scroll", placer, true);
    document.addEventListener("mousedown", dehors, true);
    document.addEventListener("keydown", clavier, true);
    (cherche || bouton_).focus();
  });
  return bouton_;
}

const filtresOffres = { texte: "", statut: "à traiter", zone: [], domaine: [], contrat: [], pays: [], region: [], fit_min: 0, jours: 0, tri: "fit", page: 0, par_page: 40 };
// The offer's age (the user, 2026-11-04: « il n'y a pas de filtre sur la date de l'offre »):
// its publication, else the day it was seen. Days; 0 = any date.
const AGES_OFFRES = [[0, "Toutes les dates"], [1, "Dernières 24 h"], [3, "3 derniers jours"], [7, "7 derniers jours"],
  [14, "14 derniers jours"], [30, "30 derniers jours"]];
// The table's optional columns (the desktop's COLS); the offer itself is always shown.
const COLONNES_OFFRES = [
  ["lieu", "Lieu", (o) => h("span", { class: "cellule-lieu", title: o.lieu }, o.lieu || "—")],
  ["zone", "Zone", (o) => (o.zone ? h("span", { class: "etiq gris" }, o.zone) : "—")],
  ["date", "Date", (o) => dateFr(o.date) || "—"],
  ["suivi", "Suivi", (o) => (o.suivi ? h("span", { class: `etiq ${o.suivi}` }, o.suivi) : "")],
  ["domaine", "Domaine", (o) => (o.domaine ? lisible(o.domaine) : "—")],
  ["contrat", "Contrat", (o) => (o.contrat ? lisible(o.contrat) : "—")],
  ["pays", "Pays", (o) => o.pays || "—"],
  ["region", "Région", (o) => o.region || "—"],
];
const TRIS_OFFRES = [["fit", "Meilleur score"], ["entreprise", "Entreprise A → Z"]];
let vuesOffres = null;  // {vues: {name: filters}, colonnes: [...]}, read once

async function choisirColonnes() {
  const visibles = new Set(vuesOffres.colonnes);
  const cases = COLONNES_OFFRES.map(([cle, nom]) => h("label", { class: "case-colonne" },
    h("input", { type: "checkbox", checked: visibles.has(cle), onchange: (e) => { e.target.checked ? visibles.add(cle) : visibles.delete(cle); } }), nom));
  const ok = await dialogue("Colonnes", "Les colonnes montrées dans le tableau ; le choix est gardé pour la prochaine fois.",
    h("div", { class: "grille-cases" }, cases), [["Appliquer", "plein", () => (visibles.size ? true : undefined)]]);
  if (!ok) return;
  vuesOffres.colonnes = COLONNES_OFFRES.map(([c]) => c).filter((c) => visibles.has(c));
  if (window.pywebview) ecrire("memoriser_colonnes", vuesOffres.colonnes);
  redessiner();
}

async function enregistrerVue() {
  const champ = h("input", { class: "champ-texte", placeholder: "par exemple : ESG à Paris, 8+" });
  const nom = await dialogue("Enregistrer la vue", "Garde les filtres et le tri de l'écran sous un nom (même nom : remplacée).",
    champ, [["Enregistrer", "plein", () => champ.value.trim() || undefined]]);
  if (!nom) return;
  const { page, ...filtres } = filtresOffres;
  if (await ecrire("enregistrer_vue", nom, filtres)) {
    vuesOffres.vues[nom] = filtres;
    toast(`Vue « ${nom} » enregistrée.`);
    redessiner();
  }
}

function menuVues() {
  const noms = Object.keys(vuesOffres.vues).sort((a, b) => a.localeCompare(b, "fr"));
  return h("select", { class: "choix", onchange: async (e) => {
    const v = e.target.value;
    e.target.value = "";
    if (v === "+") return enregistrerVue();
    if (v.startsWith("-")) {
      const nom = v.slice(1);
      const ok = await dialogue(`Supprimer la vue « ${nom} » ?`, "Seule la vue est oubliée ; les offres ne bougent pas.", null, [["Supprimer", "chaud", () => true]]);
      if (ok && await ecrire("supprimer_vue", nom)) { delete vuesOffres.vues[nom]; redessiner(); }
      return;
    }
    if (v === "*") Object.assign(filtresOffres, { texte: "", statut: "à traiter", zone: [], domaine: [], contrat: [], pays: [], region: [], fit_min: 0, jours: 0, tri: "fit" });
    else Object.assign(filtresOffres, vuesOffres.vues[v]);
    filtresOffres.page = 0;
    redessiner();
  } },
  h("option", { value: "" }, "Vues…"),
  h("option", { value: "*" }, "Tout réinitialiser"),
  noms.map((n) => h("option", { value: n }, n)),
  h("option", { value: "+" }, "Enregistrer la vue…"),
  noms.length ? h("optgroup", { label: "Supprimer" }, noms.map((n) => h("option", { value: "-" + n }, n))) : null);
}
const coches = new Set();  // ticked offers, kept across pages (the desktop's ☐ column)
ECRANS.offres = {
  titre: "Offres",
  plein: true,
  actions: () => [
    bouton("Tri du jour", "entonnoir", () => aller("tri")),
    bouton("Ajouter une offre", "sortie", ajouterOffre),
    action("Vérifier les offres", "loupe", "disponibilite"),
    action("Lancer la collecte", "collecte", "collecte", "plein")],
  async dessiner(vue) {
    const f = filtresOffres;
    // No score filter any more (the user, 2026-10-27): sorted by score the 7+ / 8+ buttons
    // showed the same list. A saved view that still carries one is read without it. The
    // date filter is back (2026-11-04): the queue holds 17 000 offers, not only fresh ones.
    f.fit_min = 0;
    if (!AGES_OFFRES.some(([v]) => v === Number(f.jours))) f.jours = 0;
    if (!TRIS_OFFRES.some(([v]) => v === f.tri)) f.tri = "fit";
    const relancer = () => ECRANS.offres.dessiner(vue);
    const changer = (cle, v) => { f[cle] = v; f.page = 0; relancer(); };
    if (!vuesOffres) vuesOffres = (await appel("vues")) || { vues: {}, colonnes: ["lieu", "zone", "date", "suivi"] };
    const d = await appel("offres", { ...f });
    if (d && d.noms_domaines) NOMS_DOMAINES = d.noms_domaines;
    if (d.choisis) f.pays = d.choisis.pays;  // a country outside the chosen regions is dropped
    // A column empty on the whole page (no zone set, nothing applied to) is left out.
    const cols = COLONNES_OFFRES.filter(([c]) => vuesOffres.colonnes.includes(c)
      && (!d.lignes.length || d.lignes.some((o) => o[c])));
    let minuteur;
    const champ = h("input", { type: "search", placeholder: "Poste, entreprise, ville…", value: f.texte,
      oninput: (e) => { clearTimeout(minuteur); minuteur = setTimeout(() => changer("texte", e.target.value), 250); } });
    const liste = (cle, tous, valeurs, lien, noms) => listeMulti(enListe(f[cle]), tous, valeurs || [], (v) => changer(cle, v), lien, noms);
    // Which places are priority or secondary is the profile's search (the user could not
    // find it, 2026-10-27): the zone list leads there.
    const reglerZones = ["Régler les zones…", () => aller("profil").then(() => {
      const c = document.getElementById("zones-profil");
      if (c) c.scrollIntoView({ behavior: "smooth", block: "start" });
    })];
    const ids = () => [...coches];
    const barreSel = coches.size ? h("div", { class: "barre-selection verre" },
      h("strong", {}, `${coches.size} cochée${coches.size > 1 ? "s" : ""}`),
      bouton("Candidature guidée…", "avion", () => candidatureGuidee(ids()), "plein"),
      bouton("Pas intéressé", "", () => { marquer(ids(), "pas intéressé", false); coches.clear(); }),
      bouton("Écarter…", "", () => ecarter(ids())),
      h("select", { class: "choix", onchange: (e) => { if (e.target.value) { marquer(ids(), e.target.value === "—" ? "" : e.target.value, false); coches.clear(); } } },
        h("option", { value: "" }, "Statut…"), h("option", { value: "—" }, "Vider le statut"),
        STATUTS.map((s) => h("option", { value: s }, majuscule(s)))),
      bouton("Tout décocher", "", () => { coches.clear(); relancer(); })) : null;
    const cocher = (id, e) => { e.stopPropagation(); coches.has(id) ? coches.delete(id) : coches.add(id); relancer(); };
    const tous = d.lignes.length && d.lignes.every((o) => coches.has(o.id));
    const tri = h("select", { class: "choix", onchange: (e) => changer("tri", e.target.value) },
      TRIS_OFFRES.map(([v, l]) =>
        h("option", { value: v, selected: v === f.tri }, l)));

    vue.replaceChildren(h("div", { class: "colonne" },
      // Two aligned rows (audit 2026-10-27: ten controls wrapped into two ragged rows):
      // search and display on top, the five filters on a grid of equal columns.
      h("div", { class: "filtres-offres" },
        h("div", { class: "barre-outils" },
          h("label", { class: "champ" }, svg("loupe"), champ),
          segment(d.statuts.map((s) => [s, s[0].toUpperCase() + s.slice(1)]), f.statut, (v) => changer("statut", v)),
          tri, menuVues(), bouton("Colonnes…", "", choisirColonnes)),
        h("div", { class: "grille-filtres" },
          liste("zone", "Toutes les zones", d.zones, reglerZones), liste("domaine", "Tous les domaines", d.domaines, null, d.noms_domaines || {}), liste("contrat", "Tous les contrats", d.contrats, null, Object.fromEntries((d.contrats || []).map((c) => [c, lisible(c)]))),
          liste("region", "Toutes les régions", d.regions), liste("pays", "Tous les pays", d.pays),
          h("select", { class: `choix${f.jours ? " pris" : ""}`, "aria-label": "Date de l'offre", onchange: (e) => changer("jours", Number(e.target.value)) },
            AGES_OFFRES.map(([v, l]) => h("option", { value: v, selected: v === Number(f.jours) }, l))))),
      barreSel,
      h("div", { class: "verre panneau remplit" },
        d.lignes.length ? h("div", { class: "defile" }, h("table", {},
          h("colgroup", {}, h("col", { style: "width:36px" }), h("col", { style: "width:64px" }), h("col", { style: `width:${cols.length > 4 ? 30 : 40}%` }), cols.map(() => h("col", {}))),
          h("thead", {}, h("tr", {}, h("th", {}, h("input", { type: "checkbox", class: "coche", checked: tous, title: "Cocher la page",
            onclick: () => { d.lignes.forEach((o) => (tous ? coches.delete(o.id) : coches.add(o.id))); relancer(); } })),
            ["Score", "Offre", ...cols.map(([, nom]) => nom)].map((t) => h("th", {}, t)))),
          h("tbody", {}, d.lignes.map((o) => h("tr", { onclick: () => ouvrirOffre(o.id), class: coches.has(o.id) ? "cochee" : "" },
            h("td", { onclick: (e) => cocher(o.id, e) }, h("input", { type: "checkbox", class: "coche", checked: coches.has(o.id), "aria-label": `Cocher : ${o.poste}` })),
            h("td", {}, h("span", { class: classeScore(o.fit), title: `Score ${nombre(o.fit)} sur 10` }, nombre(o.fit))),
            h("td", {}, h("div", { class: "cellule-offre" },
              h("div", {}, h("div", { class: "t", title: o.poste }, o.alerte ? h("span", { class: "alerte", title: o.signal }, o.alerte + " ") : null, o.poste),
                h("div", { class: "s avec-logo" }, logoSource(o.source), h("span", { class: "coupe" }, o.entreprise))))),
            cols.map(([, , cellule]) => h("td", {}, cellule(o))))))))
        : h("div", { class: "vide" }, "Aucune offre ne correspond à ces filtres."),
        pagination(d, (p) => { f.page = p; relancer(); vue.scrollTop = 0; },
          h("select", { class: "choix", onchange: (e) => { changer("par_page", Number(e.target.value)); garderReglage({ par_page: f.par_page }); } },
            [20, 40, 100, 200].map((n) => h("option", { value: n, selected: n === (d.par_page || f.par_page) }, `${n} par page`)))))));
    if (f.texte) { champ.focus(); champ.setSelectionRange(f.texte.length, f.texte.length); }
  },
};

// A column shows the cards that fit in the window; the rest unfold on demand, so that no
// column has to be scrolled to find an offer (the user, 2026-10-27) and the board is not
// cut at the bottom when the screen opens (2026-10-28). Unfolded columns stay so while
// the app is open, and scroll inside themselves.
const deroulees = new Set();
function ajusterKanban(vue) {
  for (const col of vue.querySelectorAll(".colonne-k")) {
    const bouton = col.querySelector(".deplier-k");
    if (!bouton || deroulees.has(col.dataset.statut)) continue;
    const cartes = [...col.querySelectorAll(".fiche-k")];
    cartes.forEach((c) => { c.hidden = false; });
    bouton.hidden = true;
    let n = cartes.length;
    while (n > 1 && col.scrollHeight > col.clientHeight + 1) {
      cartes[--n].hidden = true;
      bouton.hidden = false;
      bouton.textContent = `Voir les ${cartes.length - n} autres`;
    }
  }
}
window.addEventListener("resize", () => { if (courant === "candidatures") ajusterKanban($("vue")); });
ECRANS.candidatures = {
  titre: "Candidatures",
  plein: true,
  actions: () => [bouton("Relances", "cloche", () => aller("relances")),
    bouton("Lire les réponses par mail", "cloche", ouvrirCourriels)],
  async dessiner(vue) {
    const d = await appel("candidatures");
    // A card dragged to another column takes its status (the user, 2026-10-27), as the
    // drawer's status list would: same undo, same date of change.
    let tiree = null;
    const cible = (c) => STATUTS.includes(c.statut) ? {
      ondragover: (ev) => { if (tiree && tiree.statut !== c.statut) { ev.preventDefault(); ev.currentTarget.classList.add("survol"); } },
      ondragleave: (ev) => { if (!ev.currentTarget.contains(ev.relatedTarget)) ev.currentTarget.classList.remove("survol"); },
      ondrop: (ev) => {
        ev.preventDefault();
        ev.currentTarget.classList.remove("survol");
        if (tiree && tiree.statut !== c.statut) marquer(tiree.id, c.statut, false);
        tiree = null;
      },
    } : {};
    // No application yet: a word on how one gets here, and the columns over the whole
    // window rather than five small boxes in a corner of an empty page (the user,
    // 2026-11-05: « aussi dans candidatures quand il n'y en a pas encore »).
    const aucune = d.colonnes.every((c) => !c.entrees.length);
    vue.replaceChildren(h("div", { class: "colonne" },
      aucune ? h("div", { class: "verre panneau debut-k" },
        h("div", {}, h("h2", {}, "Pas encore de candidature"),
          h("div", { class: "sous" }, "Une offre arrive ici quand tu changes son statut dans Offres : « à postuler » pour la garder, « postulé » une fois envoyée. Glisse ensuite sa fiche d'une colonne à l'autre.")),
        h("div", { class: "boutons" }, bouton("Voir les offres", "valise", () => aller("offres"), "plein"),
          bouton("Tri du jour", "entonnoir", () => aller("tri")))) : null,
      h("div", { class: aucune ? "tableau-kanban debut" : "tableau-kanban" }, d.colonnes.map((c) =>
        h("div", { class: c.entrees.length || aucune ? "verre colonne-k" : "verre colonne-k vide-k", "data-statut": c.statut, ...cible(c) },
          h("div", { class: "entete" }, h("h3", {}, c.statut[0].toUpperCase() + c.statut.slice(1)),h("span", { class: "compte" }, c.entrees.length)),
          c.entrees.length ? [...c.entrees.map((e) => h("div", { class: "carte fiche-k", draggable: "true", onclick: () => ouvrirOffre(e.id),
            ondragstart: (ev) => { tiree = e; ev.dataTransfer.effectAllowed = "move"; ev.dataTransfer.setData("text/plain", e.id); ev.currentTarget.classList.add("tiree"); },
            ondragend: (ev) => { ev.currentTarget.classList.remove("tiree"); } },
            h("div", { class: "t", title: e.poste }, e.poste), h("div", { class: "s" }, e.entreprise),
            h("div", { class: "bas" }, h("span", { title: dateFr(e.date) }, e.jours != null ? `J+${e.jours}` : (dateFr(e.date) || "—")),
              e.relance_due ? h("span", { class: e.brouillon ? "etiq gris" : "etiq" }, e.brouillon ? "Brouillon prêt" : "Relance due") : null,
              e.fit == null ? null : h("div", { class: "prog", title: `${e.fit}/10` }, h("i", { style: `width:${e.fit * 10}%` }))))),
            c.entrees.length > 1 ? h("button", { class: "bouton deplier-k", onclick: () => {
              deroulees.has(c.statut) ? deroulees.delete(c.statut) : deroulees.add(c.statut);
              ECRANS.candidatures.dessiner(vue);
            } }, "Replier") : null]
          : h("div", { class: "vide" }, "Vide")))),
      d.ecartees ? h("div", { class: "sous" }, `${d.ecartees} offres écartées (mauvaise, pas intéressé, expirée) ne sont pas montrées.`) : null));
    ajusterKanban(vue);
  },
};

// The daily triage (3.80): the good offers never opened, one at a time, best first.
// Opening one marks it seen (api.offre), so the next draw shows the next one.
let triGeste = null;
// The whole description, unfolded, kept from one offer to the next (the user, 2026-11-04:
// « pouvoir voir la description en entier »; it was held in a box 40 % of the window high).
let triEntier = false;
try { triEntier = localStorage.getItem("jh-tri-entier") === "1"; } catch (_) { /* no storage */ }
ECRANS.tri = {
  titre: "Tri du jour",
  actions: () => [bouton("Toutes les offres", "", () => aller("offres"))],
  async dessiner(vue) {
    triGeste = null;
    const d = await appel("a_trier");
    const id = d && d.ids[0];
    const o = id ? await appel("offre", id) : null;
    if (courant !== "tri") return;
    if (!o) {
      vue.replaceChildren(h("div", { class: "tri" }, h("div", { class: "verre panneau tri-fin" },
        h("h2", {}, "Tri terminé"),
        h("p", { class: "sous" }, "Plus de nouvelle offre bien notée à regarder. La prochaine collecte en apportera d'autres."),
        h("div", { class: "boutons" }, bouton("Voir les offres", "", () => aller("offres"), "plein")))));
      return;
    }
    const garder = () => redessiner();
    const rejeter = () => marquer(id, "pas intéressé", false);
    const passer = async () => { await appel("passer", id); redessiner(); };
    triGeste = { garder, rejeter, passer };
    vue.replaceChildren(h("div", { class: "tri" },
      h("div", { class: "sous" }, `${nombre(d.total)} à trier · → ou Entrée : garder · P : passer · X : pas intéressé`),
      h("div", { class: "verre panneau tri-carte" },
        h("div", { class: "fiche-tete" },
          h("span", { class: `${classeScore(o.fit)} grand-score` }, nombre(o.fit)),
          h("div", { style: "min-width:0" }, h("h2", {}, o.poste), h("div", { class: "sous" }, o.entreprise))),
        h("div", { class: "puces" },
          [o.lieu, o.contrat !== "non precise" && lisible(o.contrat), o.zone, o.date && `publiée le ${dateFr(o.date)}`]
            .filter(Boolean).map((t) => h("span", { class: "puce" }, t))),
        o.pourquoi ? h("div", { class: "carte description" }, h("h3", {}, "Pourquoi ce score"),
          h("div", { translate: "no" }, traduireFit(o.pourquoi))) : null,
        o.description ? texteTri(o.description) : h("div", { class: "carte description tri-texte" }, "Pas de description enregistrée pour cette offre."),
        h("div", { class: "boutons" },
          aide(bouton("Garder", "fleche", garder, "plein"), "Elle reste dans tes offres à traiter ; offre suivante."),
          aide(bouton("Passer", "", passer), "Pas de décision : elle revient à la fin du tri."),
          aide(bouton("Pas intéressé", "", rejeter), "Classée « pas intéressé », toujours visible dans Offres. Rien n'est supprimé."),
          bouton(o.cv ? "Refaire CV et lettre" : "Préparer CV et lettre", "plume", async () => { await lancer("documents", id); garder(); }),
          bouton("Voir l'annonce", "sortie", () => ouvrir(o.url)),
          plus([
            ["Retirer de la file, avec un motif…", "", () => ecarter([id])],
            ["Tout le détail", "doc", () => ouvrirOffre(id)],
          ])))));
  },
};
function texteTri(description) {
  const boite = h("div", { class: `carte description tri-texte ${triEntier ? "entier" : ""}` }, h("div", { translate: "no" }, description));
  const lien = h("button", { class: "lien-plier", "aria-expanded": String(triEntier) });
  const poser = () => {
    boite.classList.toggle("entier", triEntier);
    lien.setAttribute("aria-expanded", String(triEntier));
    lien.textContent = triEntier ? "Réduire la description" : "Lire la description en entier";
    // Short enough to fit: nothing to unfold.
    lien.hidden = !triEntier && boite.scrollHeight <= boite.clientHeight + 4;
  };
  lien.onclick = () => {
    triEntier = !triEntier;
    try { localStorage.setItem("jh-tri-entier", triEntier ? "1" : ""); } catch (_) { /* no storage */ }
    poser();
    if (!triEntier) boite.scrollIntoView({ block: "nearest" });
  };
  requestAnimationFrame(poser);  // its height is known once in the page
  return h("div", { class: "tri-description" }, boite, lien);
}

document.addEventListener("keydown", (e) => {
  if (courant !== "tri" || !triGeste || e.ctrlKey || e.altKey || e.metaKey) return;
  if (e.target && e.target.closest && e.target.closest("input, textarea, select, [contenteditable], button, summary")) return;
  if ($("tiroir").classList.contains("ouvert") || document.querySelector(".dialogue")) return;
  const geste = e.key === "ArrowRight" || e.key === "Enter" ? triGeste.garder
    : e.key === "x" || e.key === "X" ? triGeste.rejeter
    : e.key === "p" || e.key === "P" ? triGeste.passer : null;
  if (!geste) return;
  e.preventDefault();
  triGeste = null;  // one key, one offer: a held key does not run through the list
  geste();
});

ECRANS.relances = {
  titre: "Relances",
  // Held in the window: the lists and the draft scroll inside their panels (2026-10-28).
  plein: true,
  actions: () => [action("Écrire les brouillons du jour", "plume", "brouillons", "plein")],
  async dessiner(vue) {
    const d = await appel("relances");
    const apercu = h("div", { class: "carte apercu" }, h("div", { class: "vide" }, "Choisis un brouillon pour le lire."));
    const copier = h("button", { class: "bouton", disabled: true }, svg("copie"), "Copier le texte");
    let texte = "";
    copier.onclick = async () => {
      try { await navigator.clipboard.writeText(texte); copier.lastChild.textContent = "Copié"; } catch (e) { console.error(e); }
    };
    const lignes = d.brouillons.map((b) => {
      const l = h("div", { class: "ligne-brouillon", title: b.nom },
        h("div", { style: "min-width:0" }, h("div", { class: "t" }, b.titre.replace(/^Relance J(\d+) /, "")), h("div", { class: "s" }, `J+${(b.nom.match(/^Relance_J(\d+)/) || [])[1] || "?"} · ${dateFr(b.date)}`)));
      l.onclick = async () => {
        lignes.forEach((x) => x.classList.remove("on"));
        l.classList.add("on");
        texte = (await appel("brouillon", b.nom)) || "";
        apercu.replaceChildren(texte ? h("div", { translate: "no" }, texte) : h("div", { class: "vide" }, "Brouillon vide ou illisible."));
        copier.disabled = !texte;
        copier.lastChild.textContent = "Copier le texte";
      };
      return l;
    });
    vue.replaceChildren(h("div", { class: "relances" },
      h("div", { class: "colonne" },
        h("div", { class: "sombre" }, h("h2", {}, "À relancer"), h("div", { class: "sous", style: "color:#8f8783" }, "postulées depuis 7 jours et plus"),
          h("ul", { class: "fil" }, d.dues.length
            ? d.dues.map((r) => h("li", { onclick: () => ouvrirOffre(`${r.entreprise}|${r.poste}`) },
                h("div", { class: "t" }, r.entreprise), h("div", { class: "s", title: r.poste }, `${r.jours} j · ${r.poste}`)))
            : h("li", { class: "vide" }, "Rien à relancer")))),
      h("div", { class: "relances-droite" },
        h("div", { class: "verre panneau" },
          h("div", { class: "titre-ligne" }, h("h2", {}, "Brouillons"), h("span", { class: "compte" }, d.brouillons.length)),
          h("div", { class: "liste-brouillons" }, lignes.length ? lignes : h("div", { class: "vide" }, "Aucun brouillon."))),
        h("div", { class: "colonne" },
          apercu,
          h("div", { class: "boutons" }, copier),
          h("div", { class: "sous" }, "L'envoi reste ton geste : copie, relis, envoie depuis ta messagerie.")))));
  },
};

const filtresDocs = { texte: "", genre: "", en_cours: false, page: 0 };
ECRANS.documents = {
  titre: "Documents",
  plein: true,
  // After a change of template, the documents already made are made again (the user,
  // 2026-10-27: the letters need the same tool as the CVs).
  // Shown only when there is something to redo (the user, 2026-10-28: the buttons
  // were there, and did nothing, before the first document).
  actions: () => [],
  async dessiner(vue) {
    const f = filtresDocs;
    const relancer = () => ECRANS.documents.dessiner(vue);
    const d = await appel("documents", { ...f });
    const ex = d.existants || {};
    if (courant === "documents") $("actions").replaceChildren(
      ex.CV ? action("Refaire les CV", "fleche", "regenerer_cv") : "",
      ex.Lettre ? action("Refaire les lettres", "fleche", "regenerer_lettres") : "");
    let minuteur;
    const champ = h("input", { type: "search", placeholder: "Entreprise, poste…", value: f.texte,
      oninput: (e) => { clearTimeout(minuteur); minuteur = setTimeout(() => { f.texte = e.target.value; f.page = 0; relancer(); }, 250); } });
    // A click shows the document and lets its text be changed, as from an offer; the PDF
    // is made again from the .docx, which stays the file to edit (the user, 2026-10-27).
    const voir = (x) => (x.modifiable ? voirDocument(null, x.chemin, `${x.genre} · ${x.nom}`) : ouvrirFichier(x.chemin));
    const dossiers = (d.dossiers || []).map((x) => bouton(x.genre === "CV" ? "Dossier des CV" : "Dossier des lettres", "sortie",
      () => ecrire("ouvrir_dossier_documents", x.genre)));
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "barre-outils" }, h("label", { class: "champ", style: "max-width:460px" }, svg("loupe"), champ),
        segment([["", "Tous"], ["CV", "CV"], ["Lettre", "Lettres"]], f.genre, (v) => { f.genre = v; f.page = 0; relancer(); }),
        segment([["", "Toutes les offres"], ["oui", "Candidatures envoyées"]], f.en_cours ? "oui" : "", (v) => { f.en_cours = !!v; f.page = 0; relancer(); }),
        ...dossiers,
        h("span", { class: "sous", title: (d.dossiers || []).map((x) => x.chemin).join(" · ") }, `${nombre(d.total)} documents`)),
      h("div", { class: "verre panneau remplit" },
        d.fichiers.length ? h("div", { class: "defile" }, h("table", {},
          h("colgroup", {}, h("col", { style: "width:12%" }), h("col", {}), h("col", { style: "width:16%" }), h("col", { style: "width:14%" })),
          h("thead", {}, h("tr", {}, ["Type", "Document", "Offre", "Le"].map((t) => h("th", {}, t)))),
          h("tbody", {}, d.fichiers.map((x) => h("tr", { onclick: () => voir(x), title: x.modifiable ? "Voir et modifier" : "Ouvrir" },
            h("td", {}, h("span", { class: x.genre === "CV" ? "etiq" : "etiq gris" }, x.genre)),
            h("td", { title: x.nom }, x.nom),
            // The offer it was made for, with its status: a click opens it.
            h("td", {}, x.offre ? h("button", { class: "lien", title: "Ouvrir l'offre",
              onclick: (e) => { e.stopPropagation(); ouvrirOffre(x.offre); } },
              x.statut ? majuscule(x.statut) : "Ouvrir") : "—"),
            h("td", {}, dateFr(x.date)))))))
        : (ex.CV || ex.Lettre) ? h("div", { class: "vide" }, f.en_cours ? "Aucun document d'une candidature envoyée." : "Aucun document pour cette recherche.")
        : premiersDocuments(),
        d.fichiers.length ? pagination(d, (p) => { f.page = p; relancer(); vue.scrollTop = 0; }) : null)));
    if (f.texte) { champ.focus(); champ.setSelectionRange(f.texte.length, f.texte.length); }
  },
};

// No document yet: what makes them, and the two buttons to get there (the user,
// 2026-10-28: « si aucun document créé, explique ce qu'il faut faire »).
function premiersDocuments() {
  return h("div", { class: "premiers-docs" },
    h("h2", {}, "Pas encore de CV ni de lettre"),
    h("p", { class: "sous" }, "JobHunter écrit un CV et une lettre sur mesure pour chaque offre bien notée (8 et plus), à partir de ton CV de base et de ton profil."),
    h("ol", {},
      h("li", {}, "Trouve des offres : « Lancer la collecte » (quelques minutes)."),
      h("li", {}, "Prépare les documents : « Préparer des CV et lettres… », ou depuis une offre."),
      h("li", {}, "Relis-les ici : un clic ouvre le document pour le lire ou modifier son texte.")),
    h("div", { class: "boutons" },
      action("Lancer la collecte", "collecte", "collecte", "plein"),
      bouton("Préparer des CV et lettres…", "doc", () => ACTIONS_OUTILS.documents())));
}

const carte = (titre, ...contenu) => h("div", { class: "verre panneau" }, h("div", { class: "titre-ligne" }, h("h2", {}, titre)), ...contenu);
const puces = (liste, classe = "puce") => liste.length
  ? h("div", { class: "puces" }, liste.map((t) => h("span", { class: classe }, t)))
  : h("div", { class: "sous" }, "—");
