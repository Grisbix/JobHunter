// --- Workshop: fit weights, base CV, recipes, documents to compare, CV/letters in bulk --

// The desktop's Profil → Fit tab: each slider recomputes the queue at once, nothing written.
async function cartePoids() {
  const d = await appel("poids");
  if (!d) return null;
  const valeurs = Object.fromEntries(d.curseurs.map((c) => [c.cle, c.v]));
  const resume = h("div", { class: "sous", style: "margin:10px 0" }, "Lecture de la file…");
  const histo = h("div", { class: "histo" });
  let minuteur, essais = 0;
  const recalculer = async () => {
    const b = await appel("bilan_poids", valeurs);
    if (!b) return;
    if (!b.pret) {
      resume.textContent = b.erreur ? `Lecture de la file impossible (${b.erreur}).` : "Lecture de la file… (une trentaine de secondes la première fois)";
      if (!b.erreur && essais++ < 200) minuteur = setTimeout(recalculer, 1500);
      return;
    }
    const e = b.essai, s = b.enregistre;
    resume.textContent = `${nombre(e.n)} offres · score moyen ${e.moyenne.toFixed(2)} (enregistré ${s.moyenne.toFixed(2)}) · à 8 et plus : ${nombre(e.haut)} (enregistré ${nombre(s.haut)})`;
    const max = Math.max(1, ...e.repartition, ...s.repartition);
    histo.replaceChildren(...e.repartition.map((n, i) => h("div", { class: "histo-col", title: `score ${i + 1} : ${n} (enregistré : ${s.repartition[i]})` },
      h("div", { class: "histo-barres" },
        h("span", { class: "apres", style: `height:${100 * n / max}%` }),
        h("span", { class: "avant", style: `height:${100 * s.repartition[i] / max}%` })),
      h("span", { class: "sous" }, String(i + 1)))));
  };
  const planifier = () => { clearTimeout(minuteur); minuteur = setTimeout(recalculer, 80); };
  const groupes = [
    ["axes", "Poids des axes", "Combien compte chaque axe du profil quand l'annonce cite ses compétences."],
    ["cible", "Score qui vaut 10", "La somme pondérée des axes qui donne 10. Plus bas : les notes montent."],
    ["titre", "Intitulé", "Ajouté ou retiré selon les mots du titre de l'offre."],
    ["exp", "Expérience demandée", "Retiré quand l'annonce demande au moins ce nombre d'années."],
  ];
  const blocs = groupes.map(([g, titre, sous]) => {
    const cs = d.curseurs.filter((c) => c.groupe === g);
    if (!cs.length) return null;
    return h("div", { class: "groupe-poids" }, h("h3", {}, titre), h("div", { class: "sous" }, sous),
      cs.map((c) => {
        const val = h("span", { class: "num" }, String(c.v));
        const curseur = h("input", { type: "range", min: c.b[0], max: c.b[1], step: c.b[2], value: c.v,
          oninput: (ev) => { valeurs[c.cle] = Number(ev.target.value); val.textContent = ev.target.value; planifier(); } });
        return h("label", { class: "ligne-poids" }, h("span", {}, c.nom), curseur, val);
      }));
  });
  recalculer();
  const enregistrer = async () => {
    const r = await ecrire("enregistrer_poids", valeurs);
    if (!r) return;
    toast("Poids enregistrés (l'ancienne version est gardée).");
    const ok = await dialogue("Recalculer les scores ?", "Recalculer maintenant le score enregistré de chaque offre de ta file ? Le tableau et le tri l'utilisent.",
      null, [["Recalculer", "plein", () => true]]);
    if (ok) lancer("rescore");
    redessiner();
  };
  return h("div", { class: "verre panneau large" }, h("div", { class: "titre-ligne" }, h("h2", {}, "Score : les poids")),
    h("div", { class: "sous", style: "margin-bottom:10px" }, "Chaque curseur recalcule la file aussitôt, sans rien écrire. Barres claires : les poids enregistrés."),
    h("div", { class: "poids" }, blocs), resume, histo,
    h("div", { class: "boutons", style: "margin-top:12px" },
      bouton("Enregistrer", "", enregistrer, "plein"),
      bouton("Annuler les modifications", "", () => redessiner()),
      bouton("Relire la file", "fleche", async () => { if (await ecrire("relire_composantes")) { essais = 0; resume.textContent = "Lecture de la file…"; setTimeout(recalculer, 1500); } })));
}

// Trades (3.74): one CV and one letter each. A trade is a domain of the profile: added
// here, it shows in the Offres screen's domain filter once the offers are classed again.
async function choixFichier(nom, ...args) {
  if (!window.pywebview) { toast(HORS_APPLI, true); return null; }
  let r;
  try { r = await window.pywebview.api[nom](...args); } catch (e) { toast(`Échec : ${(e && e.message) || e}`, true); return null; }
  if (!r || r.annule) return null;
  if (!r.ok) { toast(r.erreur || "Échec.", true); return null; }
  return r;
}

// A title word as the user reads it: « re:\b(isr|(?<![a-z])csrd(?![a-z]))\b » shows as
// « isr · csrd » (the user, 2026-11-04: the raw patterns ran over the card). The chip's
// tooltip keeps the pattern itself. The user, 2026-11-07: « pas l'affichage en code mais
// compréhensible pour tout le monde » — no leading « * » (search_settings.eclater: the
// word may also start inside a word), and a group spelled out: « account
// (executive|manager) » reads « account executive · account manager », « design(er)? »
// « design · designer ».
// The chip's tooltip: a pattern keeps its text, a « * » word says what it finds.
function titreMot(mot) {
  if (mot.startsWith("re:")) return `Motif : ${mot.slice(3)}`;
  return mot.startsWith("*") ? `« ${mot.slice(1)} », même au milieu d'un mot` : mot;
}

function motLisible(mot) {
  if (!mot.startsWith("re:")) return mot.replace(/^\*/, "");
  const s = mot.slice(3).replace(/\(\?<?[!=][^)]*\)/g, "").replace(/\\b|\^|\$/g, "").replace(/\(\?:/g, "(");
  // Every text the pattern means, null past 8 or on a sign it cannot spell (. + * \w…).
  let i = 0;
  const alternatives = () => {
    const tout = [];
    for (;;) {
      const v = suite();
      if (!v) return null;
      tout.push(...v);
      if (s[i] !== "|") return tout.length <= 8 ? tout : null;
      i++;
    }
  };
  const suite = () => {
    let v = [""];
    while (i < s.length && s[i] !== "|" && s[i] !== ")") {
      let morceau;
      const c = s[i];
      if (c === "(") {
        i++;
        morceau = alternatives();
        if (!morceau || s[i] !== ")") return null;
        i++;
      } else if (c === "[") {
        const fin = s.indexOf("]", i);
        if (fin < 0) return null;
        morceau = [...s.slice(i + 1, fin)];
        if (morceau.some((x) => !/[\p{L}\d ' -]/u.test(x))) return null;
        i = fin + 1;
      } else if (c === "\\") {
        const n = s[i + 1];
        if (!n || /[wdWDSB]/.test(n)) return null;
        morceau = [n === "s" ? " " : n];
        i += 2;
      } else if (/[.*+{}]/.test(c)) {
        return null;
      } else {
        morceau = [c];
        i++;
      }
      if (s[i] === "?") { morceau = ["", ...morceau]; i++; }
      v = v.flatMap((a) => morceau.map((b) => a + b));
      if (v.length > 8) return null;
    }
    return v;
  };
  const vus = alternatives();
  const mots = vus && i === s.length ? vus
    : s.replace(/\.[*+]?/g, " … ").replace(/\\(.)/g, "$1").replace(/[()?+*[\]]/g, "").split("|");
  return [...new Set(mots.map((x) => x.replace(/\s+/g, " ").trim()).filter(Boolean))].join(" · ");
}

async function carteMetiers() {
  const m = (await appel("metiers")) || { metiers: [] };
  const vrais = m.metiers.filter((x) => x.cle !== "General");
  const refaire = async (genre) => {
    const [titre, cle] = genre === "cv" ? ["Refaire les CV ?", "regenerer_cv"] : ["Refaire les lettres ?", "regenerer_lettres"];
    const ok = await dialogue(titre, "Refaire maintenant ceux déjà préparés pour les offres ?", null, [["Refaire", "plein", () => true]]);
    if (ok) lancer(cle);
  };
  const changer = async (x, genre) => {
    const r = await choixFichier(genre === "cv" ? "cv_metier" : "lettre_metier", x.cle);
    if (!r) return;
    toast(genre === "cv" ? `CV de « ${x.libelle} » : ${r.nom}.`
      : r.parcours ? `Lettre de « ${x.libelle} » : ${r.nom}. Son paragraphe de parcours est repris.` : `Lettre de « ${x.libelle} » : ${r.nom}. Aucun paragraphe de parcours reconnu.`);
    redessiner();
    refaire(genre);
  };
  const champsMetier = (x) => {
    const nom = h("input", { class: "champ-texte", value: x ? x.libelle : "", placeholder: "Ex. : Contrôle de gestion" });
    const mots = h("input", { class: "champ-texte", value: x ? x.mots.join(", ") : "", placeholder: "Ex. : contrôleur de gestion, contrôle de gestion, fp&a" });
    const bloc = h("div", { class: "formulaire" },
      h("label", { class: "champ-form" }, h("span", {}, "Nom du métier"), nom),
      x && x.cle === "General" ? null : h("label", { class: "champ-form" }, h("span", {}, "Mots du titre des offres (séparés par des virgules)"), mots));
    return { bloc, nom, mots };
  };
  const ajouter = async () => {
    const c = champsMetier(null);
    const v = await dialogue("Ajouter un métier", "Un CV pour un autre métier, et sa lettre si tu veux : les offres dont le titre contient un de ces mots le prennent. Choisis ensuite le CV.",
      c.bloc, [["Choisir le CV…", "plein", () => (c.nom.value.trim() && c.mots.value.trim() ? [c.nom.value, c.mots.value] : (toast("Il faut un nom et au moins un mot.", true), undefined))]]);
    if (!v) return;
    const r = await choixFichier("ajouter_metier", v[0], v[1]);
    if (!r) return;
    toast(`Métier ajouté, CV : ${r.cv}. Les offres prennent leur domaine…`);
    lancer("domaines");
    redessiner();
    const lettre = await dialogue("Ajouter sa lettre ?", "Ta lettre pour ce métier : son paragraphe de parcours sera repris dans les lettres de ses offres.", null, [["Choisir la lettre…", "plein", () => true]]);
    if (lettre) changer({ cle: r.cle, libelle: v[0] }, "lettre");
  };
  const modifier = async (x) => {
    const c = champsMetier(x);
    const ok = await dialogue(`Modifier « ${x.libelle} »`, null, c.bloc, [["Enregistrer", "plein", () => true]]);
    if (!ok) return;
    if (await ecrire("renommer_metier", x.cle, c.nom.value, c.mots.value)) { lancer("domaines"); redessiner(); }
  };
  const retirer = async (x) => {
    const ok = await dialogue(`Retirer « ${x.libelle} » ?`, "Ses offres passent aux autres métiers. Son CV et sa lettre restent dans leurs dossiers.", null, [["Retirer", "plein", () => true]]);
    if (ok && await ecrire("retirer_metier", x.cle)) { lancer("domaines"); redessiner(); }
  };
  const doc = (x, genre) => {
    const [lib, nom, chemin] = genre === "cv" ? ["CV", x.cv, x.cv_chemin] : ["Lettre", x.lettre, x.lettre_chemin];
    return h("div", { class: "doc-metier" },
      h("span", { class: "lab" }, lib),
      h("span", { class: `t ${nom ? "" : "vide-doc"}`, title: nom || "" }, nom || "aucune"),
      chemin ? h("button", { class: "lien", onclick: () => voirDocument(null, chemin, nom) }, "Voir") : null,
      h("button", { class: "lien", onclick: () => changer(x, genre) }, nom ? "Changer…" : "Ajouter…"));
  };
  return h("div", { class: "verre panneau large" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Mes métiers : CV et lettre"), h("span", { class: "compte" }, vrais.length),
      h("span", { style: "flex:1" }), bouton("Ajouter un métier…", "doc", ajouter, "plein")),
    h("div", { class: "sous", style: "margin:-6px 0 14px" }, "Chaque métier a son CV et sa lettre ; une offre prend le métier dont un mot est dans son titre. Chaque métier est un domaine du filtre des offres."),
    h("div", { class: "metiers" }, m.metiers.map((x) => h("div", { class: "metier" },
      h("div", { class: "metier-tete" },
        h("div", { style: "min-width:0" }, h("div", { class: "t" }, x.cle === "General" ? `${x.libelle} (le reste)` : x.libelle),
          h("div", { class: "sous", title: x.mots.map(motLisible).join(" · ") }, x.cle === "General" ? "les offres qu'aucun métier ne prend" : x.mots.map(motLisible).join(" · "))),
        h("div", { class: "outils-metier" },
          h("button", { class: "lien", onclick: () => modifier(x) }, "Modifier"),
          x.cle !== "General" && vrais.length > 1 ? h("button", { class: "lien", onclick: () => retirer(x) }, "Retirer") : null)),
      doc(x, "cv"), doc(x, "lettre")))),
    phrase(m));
}

// The sentence about you that every letter repeats, under the trades (was the « Lettre de
// motivation » card: one place for letters, 3.75).
function phrase(m) {
  const fr = h("textarea", { class: "champ-texte", rows: 3 }, m.phrase_fr || "");
  const en = h("textarea", { class: "champ-texte", rows: 3 }, m.phrase_en || "");
  const enregistrer = async () => {
    if (!await ecrire("enregistrer_phrases_lettre", fr.value, en.value)) return;
    toast("Enregistré (l'ancienne version est gardée).");
    const refaire = await dialogue("Refaire les lettres ?", "Refaire maintenant les lettres déjà préparées pour les offres ?", null, [["Refaire les lettres", "plein", () => true]]);
    if (refaire) lancer("regenerer_lettres");
  };
  return h("details", { class: "phrase-lettres" },
    h("summary", {}, "Ta phrase sur toi, reprise dans toutes les lettres"),
    h("label", { class: "champ-bloc" }, h("span", { class: "sous" }, "En français"), fr),
    h("label", { class: "champ-bloc" }, h("span", { class: "sous" }, "En anglais"), en),
    h("div", { class: "boutons" }, bouton("Enregistrer", "", enregistrer, "plein"),
      m.exemple ? bouton("Voir la dernière lettre", "doc", () => voirDocument(null, m.exemple, "Lettre")) : null));
}

// The whole profile as a form (3.74): what « Fichier du profil (avancé) » opened in
// Notepad. Each value keeps its type; lists of words are one per line.
async function profilAvance() {
  const r = await ecrire("profil_avance");
  if (!r) return;
  const donnees = structuredClone(r.profil);
  const corps = $("tiroir-corps");
  $("tiroir").classList.add("ouvert", "document");
  $("tiroir").classList.remove("large");
  $("voile").classList.add("ouvert");
  const nomLisible = (k) => String(k).replaceAll("_", " ");
  const scalaire = (v) => v === null || ["string", "number", "boolean"].includes(typeof v);
  const champ = (parent, cle, libelle) => {
    const v = parent[cle];
    if (typeof v === "boolean") {
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle),
        h("input", { type: "checkbox", checked: v, onchange: (e) => { parent[cle] = e.target.checked; } }));
    }
    if (typeof v === "number") {
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle),
        h("input", { class: "champ-texte av-nombre", type: "number", step: "any", value: String(v),
          oninput: (e) => { const n = parseFloat(e.target.value); if (!Number.isNaN(n)) parent[cle] = n; } }));
    }
    if (typeof v === "string" || v === null) {
      const long = (v || "").length > 70;
      const z = h(long ? "textarea" : "input", { class: "champ-texte", rows: long ? 3 : null, value: long ? null : (v || ""),
        oninput: (e) => { parent[cle] = e.target.value; } }, long ? v : null);
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle), z);
    }
    if (Array.isArray(v) && v.every(scalaire) && (v.length === 0 || v.every((x) => typeof x === "string"))) {
      const z = h("textarea", { class: "champ-texte", rows: Math.min(8, Math.max(2, v.length + 1)),
        oninput: (e) => { parent[cle] = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean); } }, v.join("\n"));
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle, h("span", { class: "sous" }, " · un par ligne")), z);
    }
    if (Array.isArray(v)) {
      return h("details", { class: "av-groupe" }, h("summary", {}, `${libelle} · ${v.length}`),
        v.map((x, i) => (scalaire(x) ? champ(v, i, `${i + 1}`)
          : h("details", { class: "av-groupe" }, h("summary", {}, (x && (x.libelle || x.nom || x.cle)) || `${i + 1}`),
            Object.keys(x).map((k) => champ(x, k, nomLisible(k)))))));
    }
    return h("details", { class: "av-groupe" }, h("summary", {}, libelle), Object.keys(v).map((k) => champ(v, k, nomLisible(k))));
  };
  const enregistrer = async () => {
    const e = await ecrire("enregistrer_profil_avance", donnees);
    if (!e) return;
    toast("Profil enregistré (l'ancienne version est gardée).");
    fermerTiroir();
    redessiner();
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Profil avancé"),
      h("div", { class: "sous" }, "Tout le profil, rubrique par rubrique. Les rubriques ne s'ajoutent ni ne se retirent ici ; le profil d'avant est gardé à chaque enregistrement."))),
    h("div", { class: "boutons" }, bouton("Enregistrer", "doc", enregistrer, "plein"), bouton("Fermer", "", fermerTiroir)),
    h("div", { class: "avance" }, Object.keys(donnees).map((k) => champ(donnees, k, nomLisible(k)))));
}

ACTIONS_OUTILS.profils = () => gererProfils();  // declared in app_navigation.js, loaded after

ACTIONS_OUTILS.documents = async () => {
  const reste = await ecrire("documents_restants");
  if (reste == null) return;
  const champ = h("input", { class: "champ-texte", type: "number", min: 1, max: 1000, value: Math.min(reste || 30, 50), style: "width:120px" });
  const n = await dialogue("CV et lettres", `Combien d'offres traiter ? ${reste} offre(s) à score 8 et plus attendent encore leurs documents.`,
    champ, [["Préparer", "plein", () => Number(champ.value) || undefined]]);
  if (n && await ecrire("documents_lot", n)) suivreTache();
};

ACTIONS_OUTILS.recettes = async () => {
  const r = await ecrire("recettes");
  if (!r) return;
  const corps = $("tiroir-corps");
  const zone = h("textarea", { class: "zone-code", rows: 8, spellcheck: "false" });
  zone.value = r.texte;
  const etat = h("div", { class: "sous" }, "");
  const corpsTable = h("tbody");
  const apercu = async () => {
    const a = await appel("apercu_recettes", zone.value);
    if (!a) return null;
    if (!a.ok) { toast(a.erreurs.join(" · "), true); return null; }
    etat.textContent = `${a.n} changement(s), ${a.ecartes} écarté(s). Rien n'est écrit.`;
    const raison = { candidature: "candidature : gardé", doublon: "doublon : gardé" };
    corpsTable.replaceChildren(...a.lignes.map((c) => h("tr", { class: c.ecarte ? "pale" : "" },
      h("td", {}, c.champ), h("td", {}, c.avant), h("td", {}, c.apres), h("td", {}, raison[c.ecarte] || ""))));
    return a;
  };
  const appliquer = async () => {
    const x = await ecrire("appliquer_recettes", zone.value);
    if (!x) return;
    if (x.tache) { fermerTiroir(); suivreTache(); } else toast(x.message);
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Recettes de nettoyage"),
      h("div", { class: "sous" }, "Une règle par ligne : champ | valeur à remplacer | nouvelle valeur. « re: » introduit un motif. Une offre à laquelle tu as postulé n'est jamais renommée."))),
    zone, etat,
    h("div", { class: "boutons" }, bouton("Aperçu", "loupe", apercu), bouton("Enregistrer et appliquer", "", appliquer, "plein")),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Champ", "Avant", "Après", "Remarque"].map((t) => h("th", {}, t)))), corpsTable)));
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
};

ACTIONS_OUTILS.comparer = async () => {
  const corps = $("tiroir-corps");
  const liste = h("div", { class: "liste-profils" });
  const diff = h("div", { class: "diff" });
  let choisi = null;
  const montrer = async (i) => {
    choisi = i;
    for (const el of liste.children) el.classList.toggle("on", Number(el.dataset.i) === i);
    const d = await ecrire("diff_document", i);
    if (!d) return diff.replaceChildren();
    diff.replaceChildren(...d.lignes.map(([g, p]) => h("p", { class: `diff-${{ "-": "moins", "+": "plus", "=": "egal" }[g]}` }, { "-": "− ", "+": "+ ", "=": "" }[g] + p)));
  };
  const remplir = async () => {
    const docs = (await ecrire("a_comparer")) || [];
    choisi = null;
    diff.replaceChildren(docs.length ? "" : h("div", { class: "sous" }, "Aucun document en attente de comparaison."));
    liste.replaceChildren(...docs.map((d) => h("div", { class: "ligne-profil", "data-i": d.i, onclick: () => montrer(d.i), style: "cursor:pointer" },
      h("span", {}, d.doc), h("span", { class: "etiq gris" }, `${d.ecart} paragraphe(s)`))));
    if (docs.length) montrer(docs[0].i);
  };
  const choisir = async (prendre) => {
    if (choisi == null) return;
    const r = await ecrire("choisir_version", choisi, prendre);
    if (r) { toast(r.message); remplir(); }
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Documents à comparer"),
      h("div", { class: "sous" }, "Tu as retouché ces documents ; une version plus récente attend à côté. Rouge : seulement dans ta version. Vert : seulement dans la nouvelle. Celle que tu ne gardes pas est mise de côté, jamais supprimée."))),
    liste,
    h("div", { class: "boutons" }, bouton("Prendre la nouvelle version", "", () => choisir(true), "plein"), bouton("Garder ma version", "", () => choisir(false))),
    diff);
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
  remplir();
};

// Maintenance's cards, at the end of Réglages (the user, 2026-11-04: « maintenance et
// réglages dans le même panneau »): engine, backups, last collection, data, tools.
async function cartesMaintenance() {
  const m = await appel("maintenance");
  if (!m) return [];
  const c = m.collecte;
  return [
    h("div", { class: "pile" },
      h("div", { class: "sombre" }, h("h2", {}, "Moteur"), h("div", { class: "chiffre", style: "margin-top:14px" }, m.version),
        h("div", { class: "sous", style: "color:#8f8783" }, "version installée"),
        h("div", { class: "actions-col" }, bouton("Chercher une mise à jour", "fleche", verifierMaj, "plein bouton-maj")),
        h("div", { class: "sous etat-maj", style: "color:#8f8783;margin-top:8px" }),
        m.beta == null ? null : h("label", { class: "case-beta", style: "display:flex;gap:8px;align-items:center;margin-top:12px;color:#c9c2bd" },
          h("input", { type: "checkbox", checked: m.beta, onchange: async (e) => {
            const r = await ecrire("regler_beta", e.target.checked);
            if (!r) { e.target.checked = !e.target.checked; return; }
            toast(r.beta ? "Versions de test activées : la prochaine recherche les propose." : "Versions de test désactivées.");
          } }),
          "Recevoir les versions de test")),
      carte("Sauvegardes", h("div", { class: "sous", style: "margin:0 0 10px" }, "une par jour, sept jours glissants"), puces(m.sauvegardes))),
    carte("Dernière collecte",
      h("div", { class: c.etat === "ok" ? "etat ok" : "etat" }, c.etat === "ok" ? "Réussie" : (c.etat ? lisible(c.etat) : "inconnue")),
      h("dl", { class: "paires", style: "margin-top:14px" },
        h("dt", {}, "Début"), h("dd", {}, c.debut || "—"), h("dt", {}, "Fin"), h("dd", {}, c.fin || "—"),
        h("dt", {}, "Erreurs"), h("dd", {}, String(c.erreurs)), h("dt", {}, "Dernier succès"), h("dd", {}, c.dernier_succes || "—"))),
    carte("Données",
      h("dl", { class: "paires" },
        h("dt", {}, "Offres"), h("dd", {}, nombre(m.offres)), h("dt", {}, "Candidatures"), h("dd", {}, `${nombre(m.candidatures)} suivies · ${nombre(m.envoyees)} envoyées`),
        m.tailles.map((t) => [h("dt", {}, t.nom), h("dd", {}, taille(t.octets))])),
      m.archivables ? h("div", { class: "actions-col" }, bouton(`Archiver ${nombre(m.archivables)} vieilles offres…`, "corbeille", () => archiverVieilles(m.archivables))) : null,
      m.effacable ? h("div", { class: "actions-col" }, bouton("Effacer mes données…", "corbeille", () => effacerDonnees(m))) : null,
      m.desinstallable ? h("div", { class: "actions-col" }, bouton("Désinstaller JobHunter…", "corbeille", () => desinstaller(m))) : null),
    carteOutils(await appel("outils")),
  ];
}

// Old offers nobody will read: a button, never a nightly job (api.archiver says why).
async function archiverVieilles(n) {
  const ok = await dialogue("Archiver les vieilles offres ?",
    `${nombre(n)} offres collectées il y a plus de 60 jours, notées sous le seuil, jamais ouvertes et sans candidature ` +
    "quittent la file. Elles sont d'abord copiées dans la corbeille de JobHunter et la collecte ne les reprend pas.",
    null, [["Archiver", "plein", () => true]]);
  if (!ok) return;
  const r = await ecrire("archiver", 60);
  if (r) { toast(`${nombre(r.n)} offres archivées.${gardees(r)}`); redessiner(); }
}

// Uninstalling keeps Documents/JobHunter: this starts again from nothing (Recycle Bin).
async function effacerDonnees(m) {
  const ok = await dialogue("Effacer mes données ?",
    `Le profil, les CV, les lettres, les ${nombre(m.offres)} offres et les ${nombre(m.candidatures)} candidatures suivies ` +
    "partent à la Corbeille, la collecte du matin est arrêtée et JobHunter se ferme. " +
    "Tant que la Corbeille n'est pas vidée, on peut tout restaurer.",
    null, [["Effacer et fermer", "plein", () => true]]);
  if (!ok) return;
  const r = await appel("effacer_donnees");
  if (r && !r.ok) toast(r.message, true);
}

// Uninstalling from Windows kept the data (2026-11-04): this removes both at once.
async function desinstaller(m) {
  const sous = m.effacable
    ? `JobHunter est retiré de cet ordinateur. Le profil, les CV, les lettres, les ${nombre(m.offres)} offres et les ${nombre(m.candidatures)} candidatures suivies partent à la Corbeille, d'où on peut les restaurer tant qu'elle n'est pas vidée.`
    : "JobHunter est retiré de cet ordinateur. Tes données restent dans leur dossier : il n'est pas celui de l'application.";
  const ok = await dialogue("Désinstaller JobHunter ?", sous, null, [["Désinstaller", "plein", () => true]]);
  if (!ok) return;
  const r = await appel("desinstaller");
  if (r && !r.ok) toast(r.message, true);
}
