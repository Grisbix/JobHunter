// JobHunter web interface: eight screens over the Python API (window.pywebview.api).
// Opened as a plain file it falls back to demo.json, so the page can be looked at in a
// browser. Offer titles come from the web: every text goes through textContent.
"use strict";

const ICONES = {
  maison: "M4 11.2 12 4l8 7.2V19a1.5 1.5 0 0 1-1.5 1.5H15v-5h-6v5H5.5A1.5 1.5 0 0 1 4 19z",
  valise: "M9 4h6a2 2 0 0 1 2 2v1h2.5A1.5 1.5 0 0 1 21 8.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5v-10A1.5 1.5 0 0 1 4.5 7H7V6a2 2 0 0 1 2-2zm0 3h6V6H9z",
  avion: "M3.4 11.2 19.6 4.3c.8-.3 1.5.4 1.2 1.2l-6.9 16.2c-.3.8-1.5.7-1.7-.1l-1.6-6-6-1.6c-.8-.2-.9-1.4-.1-1.7z",
  cloche: "M12 3a6 6 0 0 1 6 6v3.5l1.6 2.6c.4.7-.1 1.4-.9 1.4H5.3c-.8 0-1.3-.7-.9-1.4L6 12.5V9a6 6 0 0 1 6-6zm-2.5 15h5a2.5 2.5 0 0 1-5 0z",
  doc: "M7 3h7l5 5v11.5A1.5 1.5 0 0 1 17.5 21h-10A1.5 1.5 0 0 1 6 19.5v-15A1.5 1.5 0 0 1 7 3zm6.5 1.5V9H18z",
  profil: "M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm-8 8.2C4 16.8 7.6 14 12 14s8 2.8 8 6.2c0 .4-.4.8-.8.8H4.8c-.4 0-.8-.4-.8-.8z",
  sources: "M5 4h14a2 2 0 0 1 2 2v3H3V6a2 2 0 0 1 2-2zm-2 7h18v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
  cle: "M20.5 6.6 17 10.1l-3.1-3.1 3.5-3.5a5.5 5.5 0 0 0-7 7L3.6 17.3a1.9 1.9 0 0 0 2.7 2.7l6.8-6.8a5.5 5.5 0 0 0 7.4-6.6z",
  etoile: "m12 3 2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z",
  loupe: "M10.5 3a7.5 7.5 0 0 1 6 12l4.3 4.3-1.5 1.5-4.3-4.3A7.5 7.5 0 1 1 10.5 3zm0 2a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11z",
  sortie: "M14 3h7v7h-2V6.4l-8.3 8.3-1.4-1.4L17.6 5H14zM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z",
  copie: "M8 3h10a2 2 0 0 1 2 2v12h-2V5H8zM5 7h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z",
  eclair: "M13 2 4 14h6l-1 8 9-12h-6z",
  fleche: "M12 4a8 8 0 1 1-7.7 10h2.1A6 6 0 1 0 12 6V9L7.5 5 12 1z",
  reglage: "M3 6h9v2H3zm14 0h4v2h-4zM3 16h4v2H3zm8 0h10v2H11zM12 4h4v6h-4zM7 14h4v6H7z",
};

function svg(nom) {
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  const p = document.createElementNS(ns, "path");
  p.setAttribute("d", ICONES[nom] || "");
  s.appendChild(p);
  return s;
}

// h("div", {class: "x"}, "texte", enfant…) — builds an element; strings become text nodes.
function h(tag, attrs, ...enfants) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "style") e.style.cssText = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of enfants.flat(Infinity)) if (c != null && c !== false) e.append(c instanceof Node ? c : String(c));
  return e;
}

const $ = (id) => document.getElementById(id);
const nombre = (n) => Number(n || 0).toLocaleString("fr-FR");
const taille = (o) => (o < 1e6 ? `${Math.max(1, Math.round(o / 1024))} Ko` : `${(o / 1e6).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} Mo`);
const JOURS = ["di", "lu", "ma", "me", "je", "ve", "sa"];
const jourCourt = (iso) => {
  const d = new Date(iso + "T12:00:00");
  return isNaN(d) ? iso : `${JOURS[d.getDay()]} ${d.getDate()}`;
};
const dateFr = (iso) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "");
const classeScore = (f) => (f >= 8 ? "score" : f >= 5 ? "score moyen" : "score faible");

// --- Data access: Python when in the native window, demo.json otherwise ---------------

let DEMO = null;
async function appel(nom, ...args) {
  if (window.pywebview) return window.pywebview.api[nom](...args);
  if (!DEMO) DEMO = await (await fetch("demo.json")).json();
  return DEMO[nom] ?? null;
}

function ouvrir(url) {
  if (!url) return;
  if (window.pywebview) window.pywebview.api.ouvrir(url);
  else if (/^https?:\/\//.test(url)) window.open(url, "_blank", "noopener");
}
const ouvrirFichier = (chemin) => window.pywebview && window.pywebview.api.ouvrir_fichier(chemin);

// A button that is drawn but not yet wired to the engine: it says so.
const aBrancher = (texte, icone, classe = "") =>
  h("button", { class: `bouton ${classe}`, disabled: true, title: "À brancher sur le moteur" },
    icone ? svg(icone) : null, texte, h("span", { class: "bientot" }, "bientôt"));
const bouton = (texte, icone, onclick, classe = "") =>
  h("button", { class: `bouton ${classe}`, onclick }, icone ? svg(icone) : null, texte);

function segment(options, valeur, onchange) {
  return h("div", { class: "seg" }, options.map(([v, lib]) =>
    h("button", { class: v === valeur ? "on" : "", onclick: () => onchange(v) }, lib)));
}

function pagination(d, aller) {
  return h("div", { class: "pagination" },
    h("span", {}, `${nombre(d.total)} résultat${d.total > 1 ? "s" : ""} · page ${d.page + 1} sur ${d.pages}`),
    h("div", { class: "seg" },
      h("button", { disabled: d.page <= 0, onclick: () => aller(d.page - 1) }, "Précédente"),
      h("button", { disabled: d.page + 1 >= d.pages, onclick: () => aller(d.page + 1) }, "Suivante")));
}

// --- Drawer: one offer --------------------------------------------------------------

function fermerTiroir() {
  $("tiroir").classList.remove("ouvert");
  $("voile").classList.remove("ouvert");
}

async function ouvrirOffre(id) {
  const corps = $("tiroir-corps");
  corps.replaceChildren(h("div", { class: "vide" }, "Chargement…"));
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
  const o = await appel("offre", id);
  if (!o) return corps.replaceChildren(h("div", { class: "vide" }, "Offre introuvable dans la file."));
  corps.replaceChildren(...[
    h("div", { class: "fiche-tete" },
      h("span", { class: `${classeScore(o.fit)} grand-score` }, nombre(o.fit)),
      h("div", { style: "min-width:0" }, h("h2", {}, o.poste), h("div", { class: "sous" }, o.entreprise))),
    h("div", { class: "puces" },
      [o.lieu, o.contrat, o.zone, o.date && `publiée le ${dateFr(o.date)}`, o.suivi]
        .filter(Boolean).map((t, i) => h("span", { class: i === 4 ? "puce chaude" : "puce" }, t))),
    h("div", { class: "boutons" },
      bouton("Voir l'annonce", "sortie", () => ouvrir(o.url), "plein"),
      o.cv ? bouton("CV", "doc", () => ouvrirFichier(o.cv)) : null,
      o.lettre ? bouton("Lettre", "doc", () => ouvrirFichier(o.lettre)) : null,
      aBrancher("Préparer CV et lettre", "eclair"),
      aBrancher("Marquer postulée", "avion")),
    o.note ? h("div", { class: "carte description" }, h("h3", {}, "Note"), o.note) : null,
    h("div", { class: "carte description" },
      o.description || "Pas de description enregistrée pour cette offre."),
    h("dl", { class: "paires" },
      h("dt", {}, "Domaine"), h("dd", {}, o.domaine || "—"),
      h("dt", {}, "Source"), h("dd", { title: o.source }, o.source || "—"),
      h("dt", {}, "Statut"), h("dd", {}, o.statut || "—"),
      h("dt", {}, "Score fin"), h("dd", {}, o.fit_fin ? o.fit_fin.toFixed(2) : "—")),
  ].filter(Boolean));
}

// --- Screens ------------------------------------------------------------------------

const ECRANS = {};

ECRANS.accueil = {
  titre: "Accueil",
  actions: () => [aBrancher("Lancer la collecte", "eclair", "plein")],
  async dessiner(vue) {
    const d = await appel("tableau");
    const col = d.collecte;
    const dernier = col.length ? col[col.length - 1] : { n: 0 };
    const avant = col.slice(0, -1);
    const moyenne = avant.length ? avant.reduce((s, c) => s + c.n, 0) / avant.length : 0;
    const max = Math.max(1, ...col.map((c) => c.n));
    const pleins = [];
    const barres = h("div", { class: "barres" },
      [100, 75, 50, 25, 0].map((p) => h("div", { class: "axe", style: `top:${(1 - p / 100) * 168}px` },
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
          [["valise", "Offres en file", d.stats.file], ["etoile", "Notées 9 à traiter", d.stats.neuf],
           ["avion", "En attente de réponse", d.stats.postulees]].map(([ic, lab, val]) =>
            h("div", { class: "stat" }, h("span", { class: "rond" }, svg(ic)),
              h("div", {}, h("div", { class: "lab" }, lab), h("div", { class: "val" }, nombre(val)))))),
        h("div", { class: "verre kpi" },
          h("div", {},
            h("div", { class: "titre-ligne", style: "margin:0" }, h("h2", {}, "Collecte du matin"),
              h("span", { class: "etiq gris" }, "7 derniers scans")),
            h("div", { class: "grand" }, `+${nombre(dernier.n)}`),
            h("div", { class: "ecart" }, moyenne
              ? `${dernier.n >= moyenne ? "+" : "−"}${Math.abs(Math.round(100 * (dernier.n - moyenne) / moyenne))} % par rapport à la moyenne`
              : ""),
            barres),
          h("div", { class: "carte liste-meilleures" },
            h("div", { class: "titre-ligne", style: "margin:0" }, h("h3", {}, "Meilleures offres")),
            h("ol", {}, d.meilleures.map((o, i) =>
              h("li", { onclick: () => ouvrirOffre(`${o.entreprise}|${o.poste}`), title: o.poste },
                h("span", { class: classeScore(o.fit) }, nombre(o.fit), h("b", {}, i + 1)),
                h("div", { style: "min-width:0" }, h("div", { class: "t" }, o.poste), h("div", { class: "s" }, o.entreprise))))),
            h("button", { class: "bouton", style: "margin-top:18px;width:100%;justify-content:center", onclick: () => aller("offres") }, "Toutes les offres"))),
        h("div", { class: "verre panneau" },
          h("div", { class: "titre-ligne" }, h("h2", {}, "Candidatures récentes"),
            h("button", { class: "bouton", onclick: () => aller("candidatures") }, "Tout voir")),
          tableCandidatures(d.candidatures))),
      h("div", { class: "colonne" },
        h("div", { class: "sombre" }, h("h2", {}, "À faire"),
          h("ul", { class: "fil" }, d.relances.length
            ? d.relances.map((r) => h("li", { onclick: () => aller("relances") },
                h("div", { class: "t" }, `Relancer ${r.entreprise}`),
                h("div", { class: "s", title: r.poste }, `${r.jours} j · ${r.poste}`)))
            : h("li", { class: "vide" }, "Rien à relancer aujourd'hui"))),
        h("div", { class: "zones" }, h("h2", {}, "Par zone"), h("div", { class: "sous", style: "margin-bottom:16px" }, "offres notées 7 et plus"),
          d.zones.map((z) => h("div", { class: "zone" },
            h("div", {}, h("div", { class: "lab" }, z.zone), h("div", { class: "val" }, nombre(z.n))),
            h("div", { class: "tuile" }, h("i", { style: `width:${z.pct}%` }), h("span", {}, `${z.pct} %`))))))));
    requestAnimationFrame(() => requestAnimationFrame(() => pleins.forEach(([e, p]) => { e.style.height = `${p}%`; })));
  },
};

function tableCandidatures(lignes) {
  if (!lignes.length) return h("div", { class: "vide" }, "Aucune candidature pour l'instant.");
  return h("table", {},
    h("colgroup", {}, h("col", { style: "width:24%" }), h("col", { style: "width:38%" }), h("col", { style: "width:14%" }), h("col", { style: "width:11%" }), h("col", {})),
    h("thead", {}, h("tr", {}, ["Entreprise", "Poste", "Statut", "Le", "Score"].map((t) => h("th", {}, t)))),
    h("tbody", {}, lignes.map((c) =>
      h("tr", { onclick: () => ouvrirOffre(`${c.entreprise}|${c.poste}`) },
        h("td", {}, c.entreprise), h("td", { title: c.poste }, c.poste),
        h("td", {}, h("span", { class: `etiq ${c.statut}` }, c.statut)), h("td", {}, dateFr(c.date)),
        h("td", {}, c.fit == null ? "—" : h("div", { class: "prog", title: `${c.fit}/10` }, h("i", { style: `width:${c.fit * 10}%` })))))));
}

const filtresOffres = { texte: "", statut: "à traiter", zone: "", fit_min: 0, tri: "fit", page: 0 };
ECRANS.offres = {
  titre: "Offres",
  actions: () => [aBrancher("Préparer les documents", "eclair", "plein")],
  async dessiner(vue) {
    const f = filtresOffres;
    const relancer = () => ECRANS.offres.dessiner(vue);
    const changer = (cle, v) => { f[cle] = v; f.page = 0; relancer(); };
    const d = await appel("offres", { ...f });
    let minuteur;
    const champ = h("input", { type: "search", placeholder: "Poste, entreprise, ville…", value: f.texte,
      oninput: (e) => { clearTimeout(minuteur); minuteur = setTimeout(() => changer("texte", e.target.value), 250); } });
    const zone = h("select", { class: "choix", onchange: (e) => changer("zone", e.target.value) },
      h("option", { value: "" }, "Toutes les zones"),
      d.zones.map((z) => h("option", { value: z, selected: z === f.zone }, z)));
    const tri = h("select", { class: "choix", onchange: (e) => changer("tri", e.target.value) },
      [["fit", "Meilleur score"], ["date", "Plus récentes"], ["entreprise", "Entreprise A → Z"]].map(([v, l]) =>
        h("option", { value: v, selected: v === f.tri }, l)));

    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "barre-outils" },
        h("label", { class: "champ" }, svg("loupe"), champ),
        segment(d.statuts.map((s) => [s, s[0].toUpperCase() + s.slice(1)]), f.statut, (v) => changer("statut", v)),
        segment([[0, "Tous"], [7, "7+"], [8, "8+"], [9, "9+"]], f.fit_min, (v) => changer("fit_min", v)),
        zone, tri),
      h("div", { class: "verre panneau" },
        d.lignes.length ? h("table", {},
          h("colgroup", {}, h("col", { style: "width:40%" }), h("col", { style: "width:22%" }), h("col", { style: "width:13%" }), h("col", { style: "width:11%" }), h("col", {})),
          h("thead", {}, h("tr", {}, ["Offre", "Lieu", "Zone", "Date", "Suivi"].map((t) => h("th", {}, t)))),
          h("tbody", {}, d.lignes.map((o) => h("tr", { onclick: () => ouvrirOffre(o.id) },
            h("td", {}, h("div", { class: "cellule-offre" }, h("span", { class: classeScore(o.fit) }, nombre(o.fit)),
              h("div", {}, h("div", { class: "t", title: o.poste }, o.poste), h("div", { class: "s" }, o.entreprise)))),
            h("td", { title: o.lieu }, o.lieu || "—"),
            h("td", {}, o.zone ? h("span", { class: "etiq gris" }, o.zone) : "—"),
            h("td", {}, dateFr(o.date) || "—"),
            h("td", {}, o.suivi ? h("span", { class: `etiq ${o.suivi}` }, o.suivi) : "")))))
        : h("div", { class: "vide" }, "Aucune offre ne correspond à ces filtres."),
        pagination(d, (p) => { f.page = p; relancer(); vue.scrollTop = 0; }))));
    if (f.texte) { champ.focus(); champ.setSelectionRange(f.texte.length, f.texte.length); }
  },
};

ECRANS.candidatures = {
  titre: "Candidatures",
  actions: () => [aBrancher("Lire les réponses par mail", "cloche")],
  async dessiner(vue) {
    const d = await appel("candidatures");
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "tableau-kanban" }, d.colonnes.map((c) =>
        h("div", { class: "verre colonne-k" },
          h("div", { class: "entete" }, h("h3", {}, c.statut[0].toUpperCase() + c.statut.slice(1)),h("span", { class: "compte" }, c.entrees.length)),
          c.entrees.length ? c.entrees.map((e) => h("div", { class: "carte fiche-k", onclick: () => ouvrirOffre(e.id) },
            h("div", { class: "t", title: e.poste }, e.poste), h("div", { class: "s" }, e.entreprise),
            h("div", { class: "bas" }, h("span", {}, dateFr(e.date) || "—"),
              e.fit == null ? null : h("div", { class: "prog", title: `${e.fit}/10` }, h("i", { style: `width:${e.fit * 10}%` })))))
          : h("div", { class: "vide" }, "Vide")))),
      d.ecartees ? h("div", { class: "sous" }, `${d.ecartees} offres écartées (mauvaise, pas intéressé, expirée) ne sont pas montrées.`) : null));
  },
};

ECRANS.relances = {
  titre: "Relances",
  actions: () => [aBrancher("Écrire les brouillons du jour", "eclair", "plein")],
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
        apercu.replaceChildren(texte || h("div", { class: "vide" }, "Brouillon vide ou illisible."));
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

const filtresDocs = { texte: "", page: 0 };
ECRANS.documents = {
  titre: "Documents",
  actions: () => [aBrancher("Régénérer après un changement de modèle", "fleche")],
  async dessiner(vue) {
    const f = filtresDocs;
    const relancer = () => ECRANS.documents.dessiner(vue);
    const d = await appel("documents", { ...f });
    let minuteur;
    const champ = h("input", { type: "search", placeholder: "Entreprise, poste…", value: f.texte,
      oninput: (e) => { clearTimeout(minuteur); minuteur = setTimeout(() => { f.texte = e.target.value; f.page = 0; relancer(); }, 250); } });
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "barre-outils" }, h("label", { class: "champ", style: "max-width:460px" }, svg("loupe"), champ)),
      h("div", { class: "verre panneau" },
        d.fichiers.length ? h("table", {},
          h("colgroup", {}, h("col", { style: "width:11%" }), h("col", { style: "width:59%" }), h("col", { style: "width:10%" }), h("col", { style: "width:11%" }), h("col", {})),
          h("thead", {}, h("tr", {}, ["Type", "Document", "Format", "Le", "Taille"].map((t) => h("th", {}, t)))),
          h("tbody", {}, d.fichiers.map((x) => h("tr", { onclick: () => ouvrirFichier(x.chemin), title: "Ouvrir" },
            h("td", {}, h("span", { class: x.genre === "CV" ? "etiq" : "etiq gris" }, x.genre)),
            h("td", { title: x.nom }, x.nom), h("td", {}, x.format), h("td", {}, dateFr(x.date)), h("td", {}, `${nombre(x.ko)} Ko`)))))
        : h("div", { class: "vide" }, "Aucun document."),
        pagination(d, (p) => { f.page = p; relancer(); vue.scrollTop = 0; }))));
    if (f.texte) { champ.focus(); champ.setSelectionRange(f.texte.length, f.texte.length); }
  },
};

const carte = (titre, ...contenu) => h("div", { class: "verre panneau" }, h("div", { class: "titre-ligne" }, h("h2", {}, titre)), ...contenu);
const puces = (liste, classe = "puce") => liste.length
  ? h("div", { class: "puces" }, liste.map((t) => h("span", { class: classe }, t)))
  : h("div", { class: "sous" }, "—");

ECRANS.profil = {
  titre: "Profil",
  actions: () => [aBrancher("Modifier le profil", "profil", "plein")],
  async dessiner(vue) {
    const p = await appel("profil");
    const id = p.identite;
    vue.replaceChildren(h("div", { class: "grille" },
      h("div", { class: "verre panneau" },
        h("div", { class: "identite" }, h("span", { class: "avatar" }, (id.prenom || "?")[0]),
          h("div", { style: "min-width:0" }, h("div", { class: "nom" }, `${id.prenom} ${id.nom}`), h("div", { class: "sous" }, id.ville))),
        h("dl", { class: "paires", style: "margin-top:20px" },
          h("dt", {}, "Mail"), h("dd", {}, id.email || "—"),
          h("dt", {}, "LinkedIn"), h("dd", { title: id.linkedin }, id.linkedin || "—"),
          h("dt", {}, "Langues"), h("dd", {}, p.langues.join(" · ").toUpperCase()))),
      carte("Domaines visés", puces(p.domaines.map((d) => d.libelle), "puce chaude")),
      carte("Zones", h("div", { class: "sous", style: "margin:0 0 8px" }, "Prioritaires"), puces(p.prioritaires, "puce chaude"),
        h("div", { class: "sous", style: "margin:16px 0 8px" }, "Secondaires"), puces(p.secondaires)),
      h("div", { class: "verre panneau large" }, h("div", { class: "titre-ligne" }, h("h2", {}, "Compétences"), h("span", { class: "compte" }, p.competences.length)), puces(p.competences)),
      carte("Outils", puces(p.outils)),
      carte("Notation", h("dl", { class: "paires" }, Object.entries(p.scoring).map(([k, v]) =>
        [h("dt", {}, k.replaceAll("_", " ")), h("dd", {}, String(v))]))),
      carte("Intitulés", h("div", { class: "sous", style: "margin:0 0 8px" }, "Gardés"), puces(p.garder.slice(0, 30)),
        h("div", { class: "sous", style: "margin:16px 0 8px" }, "Écartés"), puces(p.ecarter.slice(0, 30)))));
  },
};

ECRANS.sources = {
  titre: "Sources",
  actions: () => [aBrancher("Collecter maintenant", "eclair", "plein")],
  async dessiner(vue) {
    const s = await appel("sources");
    const max = Math.max(1, ...s.rendement.map((r) => r.nouvelles));
    const ats = Object.values(s.ats).reduce((a, b) => a + b, 0);
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "verre stats" },
        [["loupe", "Mots-clés", s.mots_cles.length], ["sources", "Sources actives", s.rendement.length], ["valise", "Sites carrières suivis", ats]]
          .map(([ic, lab, val]) => h("div", { class: "stat" }, h("span", { class: "rond" }, svg(ic)),
            h("div", {}, h("div", { class: "lab" }, lab), h("div", { class: "val" }, nombre(val)))))),
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Rendement des sources"), h("span", { class: "etiq gris" }, "dernières collectes")),
        s.rendement.length ? h("table", {},
          h("colgroup", {}, h("col", { style: "width:20%" }), h("col", { style: "width:14%" }), h("col", { style: "width:14%" }), h("col", { style: "width:30%" }), h("col", {})),
          h("thead", {}, h("tr", {}, ["Source", "Ramenées", "Nouvelles", "", "Dernier passage"].map((t) => h("th", {}, t)))),
          h("tbody", {}, s.rendement.map((r) => h("tr", { style: "cursor:default" },
            h("td", { style: "text-transform:capitalize" }, r.source), h("td", {}, nombre(r.ramenees)), h("td", {}, nombre(r.nouvelles)),
            h("td", {}, h("div", { class: "prog" }, h("i", { style: `width:${100 * r.nouvelles / max}%` }))),
            h("td", {}, `${dateFr(r.dernier)} `, r.verdict ? h("span", { class: r.verdict === "ok" ? "etiq gris" : "etiq" }, r.verdict) : null)))))
        : h("div", { class: "vide" }, "Pas encore de journal de rendement.")),
      h("div", { class: "grille" },
        carte("Mots-clés de collecte", puces(s.mots_cles)),
        carte("Exclusions", h("div", { class: "sous", style: "margin:0 0 8px" }, "Contrats"), puces(s.contrats_exclus),
          h("div", { class: "sous", style: "margin:16px 0 8px" }, "Pays"), puces(s.pays_exclus)),
        carte("Sites carrières (ATS)", h("dl", { class: "paires" }, Object.entries(s.ats).map(([k, v]) =>
          [h("dt", { style: "text-transform:capitalize" }, k), h("dd", {}, `${v} entreprises`)]))))));
  },
};

ECRANS.maintenance = {
  titre: "Maintenance",
  actions: () => [],
  async dessiner(vue) {
    const m = await appel("maintenance");
    const c = m.collecte;
    vue.replaceChildren(h("div", { class: "grille" },
      h("div", { class: "sombre" }, h("h2", {}, "Moteur"), h("div", { class: "chiffre", style: "margin-top:14px" }, m.version),
        h("div", { class: "sous", style: "color:#8f8783" }, "version installée"),
        h("div", { class: "actions-col" }, aBrancher("Chercher une mise à jour", "fleche", "plein"))),
      carte("Dernière collecte",
        h("div", { class: c.etat === "ok" ? "etat ok" : "etat" }, c.etat === "ok" ? "Réussie" : (c.etat || "inconnue")),
        h("dl", { class: "paires", style: "margin-top:14px" },
          h("dt", {}, "Début"), h("dd", {}, c.debut || "—"), h("dt", {}, "Fin"), h("dd", {}, c.fin || "—"),
          h("dt", {}, "Erreurs"), h("dd", {}, String(c.erreurs)), h("dt", {}, "Dernier succès"), h("dd", {}, c.dernier_succes || "—")),
        h("div", { class: "actions-col" }, aBrancher("Relancer la collecte", "eclair"))),
      carte("Données",
        h("dl", { class: "paires" },
          h("dt", {}, "Offres"), h("dd", {}, nombre(m.offres)), h("dt", {}, "Candidatures"), h("dd", {}, nombre(m.candidatures)),
          m.tailles.map((t) => [h("dt", {}, t.nom), h("dd", {}, taille(t.octets))])),
        h("div", { class: "actions-col" }, aBrancher("Contrôler les offres fermées", "loupe"))),
      carte("Sauvegardes", h("div", { class: "sous", style: "margin:0 0 10px" }, "une par jour, sept jours glissants"), puces(m.sauvegardes))));
  },
};

// --- Navigation ---------------------------------------------------------------------

let courant = null;
// Display settings: --t drives every see-through surface of the native window (style.css).
function appliquerReglages(r) {
  if (!r) return;
  document.body.style.setProperty("--t", String(r.verre / 100));
  document.body.classList.toggle("sans-fond", r.fond === "aucun");
}

const FONDS = [["acrylique", "Acrylique"], ["net", "Net"], ["mica", "Mica"], ["aucun", "Aucun"]];

ECRANS.reglages = {
  titre: "Réglages",
  actions: () => [],
  async dessiner(vue) {
    let r = (await appel("reglages")) || { fond: "acrylique", verre: 50 };
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
    vue.replaceChildren(h("div", { class: "grille" },
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Apparence")),
        h("div", { class: "reglage" },
          h("div", {}, h("div", { class: "nom-reglage" }, "Fond de la fenêtre"),
            h("div", { class: "sous" }, "Acrylique : le bureau, flouté. Net : le bureau tel quel. Mica : une teinte douce. Aucun : opaque.")),
          place),
        h("div", { class: "reglage" },
          h("div", { class: "titre-ligne" }, h("div", { class: "nom-reglage" }, "Transparence"), valeur),
          h("div", { class: "ligne-curseur" }, h("span", {}, "Opaque"), curseur, h("span", {}, "Verre")),
          h("div", { class: "sous" }, "Combien le bureau transparaît. La force du flou acrylique est fixée par Windows."))),
      window.pywebview ? null : h("div", { class: "verre panneau" },
        h("div", { class: "sous" }, "Aperçu navigateur : ces réglages ne s'enregistrent que dans l'application."))));
  },
};

async function aller(nom) {
  if (!ECRANS[nom]) nom = "accueil";
  courant = nom;
  fermerTiroir();
  for (const a of document.querySelectorAll(".menu a")) a.classList.toggle("actif", a.dataset.ecran === nom);
  const e = ECRANS[nom];
  $("titre").textContent = e.titre;
  $("actions").replaceChildren(...e.actions());
  const vue = $("vue");
  vue.scrollTop = 0;
  try { localStorage.setItem("jh-ecran", nom); } catch (_) { /* no storage: fine */ }
  try {
    await e.dessiner(vue);
  } catch (err) {
    console.error(err);
    vue.replaceChildren(h("div", { class: "vide" }, "Impossible de charger cet écran."));
  }
}

function demarrer() {
  for (const a of document.querySelectorAll(".menu a[data-icone]")) {
    a.prepend(svg(a.dataset.icone));
    a.addEventListener("click", () => aller(a.dataset.ecran));
  }
  $("voile").addEventListener("click", fermerTiroir);
  $("fermer-tiroir").addEventListener("click", fermerTiroir);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermerTiroir(); });
  let debut = "accueil";
  try { debut = localStorage.getItem("jh-ecran") || debut; } catch (_) { /* no storage */ }
  aller(debut);
}

// Native window: no Windows frame, our own title bar over a see-through background.
function natif() {
  document.body.classList.add("natif");
  appel("reglages").then(appliquerReglages).catch(() => { /* defaults from style.css */ });
  for (const b of document.querySelectorAll(".feux button")) {
    b.addEventListener("click", () => window.pywebview.api.fenetre(b.dataset.action));
  }
  $("barre").addEventListener("dblclick", (e) => {
    if (!e.target.closest("button")) window.pywebview.api.fenetre("agrandir");
  });
  demarrer();
}

if (window.pywebview) natif();
else window.addEventListener("pywebviewready", natif);
// Outside pywebview the event never comes: start on the demo after a short wait.
setTimeout(() => { if (!window.pywebview && !courant) demarrer(); }, 300);
