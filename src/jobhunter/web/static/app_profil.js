// --- Editing: chips, places, save bar --------------------------------------------------

// Calls an API method that writes; in the browser preview, says it cannot.
// A list of words edited in place: × removes, Enter adds. A long list shows its first
// fifteen; what is typed also filters, so a word is found among two hundred.
const PUCES_MAX = 15;
function editeurPuces(liste, sale, placeholder = "Ajouter…") {
  const boite = h("div", { class: "puces-edit" });
  let filtre = "";
  let tout = false;
  const dessiner = (focus = false) => {
    const champ = h("input", {
      placeholder, value: filtre,
      title: liste.length > PUCES_MAX ? "Entrée ajoute le mot ; taper filtre la liste" : "",
      oninput: (e) => { filtre = e.target.value; dessiner(true); },
      onkeydown: (e) => {
        const v = e.target.value.trim();
        if (e.key === "Enter" && v) {
          e.preventDefault();
          if (!liste.some((x) => x.toLowerCase() === v.toLowerCase())) { liste.push(v); sale(); }
          filtre = "";
          dessiner(true);
        } else if (e.key === "Backspace" && !e.target.value && liste.length && liste.length <= PUCES_MAX) {
          liste.pop(); sale(); dessiner(true);
        }
      },
    });
    const f = filtre.trim().toLowerCase();
    const vus = liste.map((x, i) => [x, i]).filter(([x]) => !f || x.toLowerCase().includes(f) || motLisible(x).toLowerCase().includes(f));
    const montres = f || tout ? vus : vus.slice(0, PUCES_MAX);
    const reste = vus.length - montres.length;
    boite.replaceChildren(...montres.map(([x, i]) => h("span", { class: "puce modifiable", title: titreMot(x) }, motLisible(x),
      h("button", { title: "Retirer", onclick: () => { liste.splice(i, 1); sale(); dessiner(); } }, "×"))),
      reste ? h("button", { class: "lien", onclick: () => { tout = true; dessiner(); } }, `+ ${reste} autres`)
        : tout && !f && liste.length > PUCES_MAX ? h("button", { class: "lien", onclick: () => { tout = false; dessiner(); } }, "Replier") : "",
      champ);
    if (focus) { champ.focus(); champ.selectionStart = champ.selectionEnd = champ.value.length; }
  };
  dessiner();
  return boite;
}

// Places: chips of {entree, libelle}, and a field that suggests places as you type.
const GENRES_LIEU = { ville: "ville et alentours", region: "région" };
function editeurLieux(liste, sale) {
  // A region holds its cities, a city does not hold its region: each choice says which.
  const genre = (x) => (GENRES_LIEU[x.genre] ? h("span", { class: "genre-lieu" }, GENRES_LIEU[x.genre]) : null);
  const boite = h("div", { class: "puces-edit lieux" });
  const suggestions = h("div", { class: "suggestions" });
  let minuteur;
  const dessiner = (focus = false) => {
    const champ = h("input", {
      placeholder: "Ville, région, pays…",
      oninput: (e) => {
        clearTimeout(minuteur);
        const q = e.target.value;
        minuteur = setTimeout(async () => {
          const r = q.trim().length < 2 ? [] : (await appel("lieux", q)) || [];
          suggestions.replaceChildren(...r.map((s) => h("button", {
            onclick: () => {
              const cle = JSON.stringify(s.entree).toLowerCase();
              if (!liste.some((x) => JSON.stringify(x.entree).toLowerCase() === cle)) { liste.push(s); sale(); }
              suggestions.replaceChildren();
              dessiner(true);
            },
          }, s.libelle, genre(s))));
        }, 200);
      },
      onkeydown: (e) => {
        if (e.key === "Enter") { e.preventDefault(); suggestions.querySelector("button")?.click(); }
        if (e.key === "Escape") suggestions.replaceChildren();
      },
    });
    boite.replaceChildren(...liste.map((x, i) => h("span", { class: "puce modifiable chaude" }, x.libelle, genre(x),
      h("button", { title: "Retirer", onclick: () => { liste.splice(i, 1); sale(); dessiner(); } }, "×"))), champ);
    if (focus) champ.focus();
  };
  dessiner();
  return h("div", { class: "lieux-boite" }, boite, suggestions);
}

// "Enregistrer" + a message; enabled once something changed.
function barreEnregistrer(enregistrer) {
  const msg = h("span", { class: "sous" });
  const b = h("button", { class: "bouton plein", disabled: true }, "Enregistrer");
  b.onclick = async () => {
    b.disabled = true;
    msg.textContent = "Enregistrement…";
    let r = null;
    try { r = await enregistrer(); }
    catch (e) { r = { ok: false, erreur: `Échec : ${(e && e.message) || e}` }; }
    if (r && r.ok) {
      msg.textContent = r.message || "Enregistré.";
    } else {
      msg.textContent = "";
      b.disabled = false;
      if (r) toast((r.erreurs || [r.erreur]).join(" · "), true);
    }
  };
  return {
    el: h("div", { class: "barre-enreg" }, b, msg),
    sale: () => { b.disabled = false; msg.textContent = "Modifications non enregistrées"; },
  };
}

const sousTitre = (t, marge = "16px 0 8px") => h("div", { class: "sous", style: `margin:${marge}` }, t);
const avecBak = (r) => r && r.ok ? { ...r, message: "Enregistré (l'ancienne version est gardée)." } : r;

ECRANS.profil = {
  titre: "Profil",
  actions: () => [
    bouton("Gérer les profils", "profil", gererProfils, "plein"),
    bouton("Profil avancé", "doc", profilAvance)],
  async dessiner(vue) {
    const [p, rech, comp] = await Promise.all([appel("profil"), appel("recherche"), appel("competences")]);

    // Identity and languages.
    const id = { ...p.identite, langues: [...p.langues] };
    const bId = barreEnregistrer(() => ecrire("enregistrer_identite", id).then(avecBak));
    const champ = (cle, lib) => h("label", { class: "champ-form" }, h("span", {}, lib),
      h("input", { value: id[cle] || "", oninput: (e) => { id[cle] = e.target.value; bId.sale(); } }));
    const carteId = h("div", { class: "verre panneau" },
      h("div", { class: "identite" }, h("span", { class: "avatar" }, (id.prenom || "?")[0]),
        h("div", { style: "min-width:0" }, h("div", { class: "nom" }, `${id.prenom} ${id.nom}`), h("div", { class: "sous" }, id.ville))),
      h("div", { class: "formulaire" }, champ("prenom", "Prénom"), champ("nom", "Nom"), champ("ville", "Ville"),
        champ("email", "Mail"), champ("linkedin", "LinkedIn")),
      sousTitre("Langues parlées (codes : fr, en, de…)"), editeurPuces(id.langues, bId.sale, "code…"),
      bId.el);

    // The search: keywords, titles, places.
    const r = rech || { mots_cles: [], garder: [], ecarter: [], prioritaires: [], secondaires: [] };
    const bR = barreEnregistrer(async () => {
      const res = await ecrire("enregistrer_recherche", r);
      if (res && res.ok) {
        res.message = "Enregistré (l'ancienne version est gardée). Effet à la prochaine collecte."
          + (res.zones ? " Zones des offres en cours de mise à jour." : "");
        if (res.zones) suivreTache();
      }
      return res;
    });
    const carteRech = h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Ma recherche")),
      h("div", { class: "deux-colonnes" },
        h("div", {},
          sousTitre(`Mots-clés de collecte · ${r.mots_cles.length}`, "0 0 8px"), editeurPuces(r.mots_cles, bR.sale, "nouveau mot-clé…"),
          Object.assign(sousTitre("Zones prioritaires"), { id: "zones-profil" }), editeurLieux(r.prioritaires, bR.sale),
          sousTitre("Zones secondaires"), editeurLieux(r.secondaires, bR.sale)),
        h("div", {},
          sousTitre("Intitulés à garder (un mot du titre suffit)", "0 0 8px"), editeurPuces(r.garder, bR.sale, "mot d'intitulé…"),
          sousTitre("Intitulés à écarter"), editeurPuces(r.ecarter, bR.sale, "mot à écarter…"))),
      bR.el);

    // Skills: words searched in the postings, and the axes they count for.
    const liste = comp ? comp.liste : [];
    const axes = comp ? comp.axes : [];
    const corps = h("div", { class: "liste-comp" });
    const bC = barreEnregistrer(async () => {
      const res = avecBak(await ecrire("enregistrer_competences", liste));
      if (res && res.ok) {
        // The axes of the offers changed: their fit follows only once recomputed.
        if (!bC.el.querySelector(".rescore")) bC.el.append(bouton("Recalculer les scores", "fleche", () => lancer("rescore"), "rescore"));
      }
      return res;
    });
    const dessinerComp = () => corps.replaceChildren(...liste.map((c, i) => h("div", { class: "ligne-comp" },
      h("div", { class: "nom-comp" }, c.nom, c.base ? h("span", { class: "etiq gris", title: "Compétence de base du CV" }, "base") : null),
      h("div", { class: "axes-comp" }, axes.map((a) => h("button", {
        class: `bascule ${c.axes.includes(a) ? "on" : ""}`,
        title: "Compte pour cet axe du score",
        onclick: () => { c.axes = c.axes.includes(a) ? c.axes.filter((x) => x !== a) : [...c.axes, a]; bC.sale(); dessinerComp(); },
      }, a))),
      editeurPuces(c.synonymes, bC.sale, "mot cherché…"),
      c.base ? h("span") : h("button", { class: "retirer", title: "Retirer la compétence", onclick: () => { liste.splice(i, 1); bC.sale(); dessinerComp(); } }, "×"))));
    dessinerComp();
    const nouvelle = h("input", { placeholder: "Nouvelle compétence…", onkeydown: (e) => {
      const v = e.target.value.trim();
      if (e.key !== "Enter" || !v) return;
      if (liste.some((c) => c.nom.toLowerCase() === v.toLowerCase())) return toast("Elle existe déjà.", true);
      liste.push({ nom: v, axes: [], synonymes: [v.toLowerCase()], en: "", base: false });
      e.target.value = "";
      bC.sale();
      dessinerComp();
    } });
    const carteComp = h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Compétences"), h("span", { class: "compte" }, liste.length)),
      h("div", { class: "sous", style: "margin:-6px 0 14px" }, "Les mots cherchés dans les annonces, et les axes du score pour lesquels chaque compétence compte."),
      corps,
      h("label", { class: "champ", style: "margin-top:14px" }, svg("plus"), nouvelle),
      bC.el);

    // CVs and letters first, side by side (the user, 2026-11-02: « mettre ajout lettre
    // de motivation plus haut dans le panneau profil à côté de CV »).
    vue.replaceChildren(h("div", { class: "grille grille-profil" },
      carteId,
      // Beside the identity, the score settings and the tools: alone, the first stretched
      // to the identity's height and the tools sat by themselves on the last row (the
      // user, 2026-11-04: « adapte l'espace pour éviter qu'il y ait des parties vides »).
      // style.css: the tools take the height left and scroll inside it.
      h("div", { class: "pile pile-profil" },
        // Two pairs a line: one a line left the card's right two-thirds empty.
        carte("Score : réglages", h("dl", { class: "paires deux" }, Object.entries(p.scoring).map(([k, v]) =>
          [h("dt", {}, k.replaceAll("_", " ")), h("dd", {}, String(v))]))),
        Object.assign(carte("Outils", puces(p.outils)), { className: "verre panneau outils-profil" })),
      await carteMetiers(),
      carteRech,
      carteComp,
      await cartePoids()));
  },
};

let ongletSources = "recherche";
ECRANS.sources = {
  titre: "Sources",
  plein: () => ongletSources !== "recherche",
  actions: () => [action("Lancer la collecte", "collecte", "collecte", "plein")],
  async dessiner(vue) {
    const tete = segment([["recherche", "Mots-clés et rendement"], ["entreprises", "Entreprises suivies"], ["vues", "Entreprises vues"],
      ["sites", "Sites d'offres"], ["acces", "Accès et clés"]], ongletSources, (v) => { ongletSources = v; ECRANS.sources.dessiner(vue); });
    const corps = h("div", { class: "corps-onglet" });
    vue.classList.toggle("plein", ECRANS.sources.plein());
    vue.replaceChildren(h("div", { class: "colonne" }, h("div", { class: "barre-outils" }, tete), corps));
    await ONGLETS_SOURCES[ongletSources](corps);
  },
};

const ONGLETS_SOURCES = {};
ONGLETS_SOURCES.recherche = async (vue) => {
  {
    const s = await appel("sources");
    const max = Math.max(1, ...s.rendement.map((r) => r.nouvelles));
    const ats = Object.values(s.ats).reduce((a, b) => a + b, 0);

    const mots = [...s.mots_cles];
    const bM = barreEnregistrer(async () => {
      const r = await appel("recherche");
      if (!r) return ecrire("recherche");
      return avecBak(await ecrire("enregistrer_recherche", { ...r, mots_cles: mots }));
    });
    const excl = { contrats_exclus: [...s.contrats_exclus], pays_exclus: [...s.pays_exclus] };
    const bE = barreEnregistrer(() => ecrire("enregistrer_exclusions", excl));

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
          h("tbody", {}, s.rendement.map((r) => h("tr", {},
            h("td", {}, h("span", { class: "avec-logo" }, logoSource(r.source), lisible(r.source))), h("td", {}, nombre(r.ramenees)), h("td", {}, nombre(r.nouvelles)),
            h("td", {}, h("div", { class: "prog" }, h("i", { style: `width:${100 * r.nouvelles / max}%` }))),
            h("td", {}, `${dateFr(r.dernier)} `, r.verdict ? h("span", { class: r.verdict === "ok" ? "etiq gris" : "etiq" }, r.verdict) : null)))))
        : h("div", { class: "vide" }, "Pas encore de journal de rendement.")),
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Mots-clés de collecte"), h("span", { class: "compte" }, mots.length)),
        editeurPuces(mots, bM.sale, "nouveau mot-clé…"), bM.el),
      // auto-fit: Exclusions and the career sites share the row, no empty third column.
      h("div", { class: "grille ajustee" },
        carte("Exclusions", sousTitre("Contrats", "0 0 8px"), editeurPuces(excl.contrats_exclus, bE.sale, "type de contrat…"),
          sousTitre("Pays"), editeurPuces(excl.pays_exclus, bE.sale, "pays…"), bE.el),
        carte("Sites carrières (ATS)", ats ? h("dl", { class: "paires" }, Object.entries(s.ats).map(([k, v]) =>
          [h("dt", {}, lisible(k)), h("dd", {}, `${v} entreprises`)]))
          : [h("div", { class: "sous", style: "margin-bottom:12px" }, "Aucune entreprise suivie sur son site carrières. Ajoute celles qui t'intéressent : leurs offres arrivent dès leur publication."),
            bouton("Entreprises suivies", "valise", () => { ongletSources = "entreprises"; ECRANS.sources.dessiner($("vue")); })]))));
  }
};

// --- Statuses from emails (Candidatures) -----------------------------------------------

ACTIONS_OUTILS.courriels = () => ouvrirCourriels();
function ouvrirCourriels() {
  const corps = $("tiroir-corps");
  const liste = h("div", { class: "colonne" });
  const info = h("div", { class: "sous" }, "Choisis d'où lire tes courriels. Rien n'est écrit sans ton clic « Appliquer ».");
  const lire = async (source) => {
    info.textContent = "Lecture des courriels…";
    liste.replaceChildren();
    // Not ecrire(): its toast would leave "Lecture des courriels…" standing, as if the
    // reading never ended (the user, 2026-10-27). The reason stays here, in full.
    if (!window.pywebview) { info.textContent = HORS_APPLI; return; }
    const r = await window.pywebview.api.lire_courriels(source);
    if (!r || !r.ok) { info.textContent = !r ? "Lecture impossible." : r.annule ? "Aucun fichier choisi." : r.erreur; return; }
    info.textContent = `${nombre(r.lus)} courriels lus · ${r.propositions.length} statut(s) proposé(s).`;
    liste.replaceChildren(...r.propositions.map((p, i) => {
      const [entreprise, poste] = p.oid.split("|");
      const ligne = h("div", { class: "carte proposition" },
        h("div", { class: "t" }, entreprise), h("div", { class: "s" }, poste),
        h("div", { class: "puces", style: "margin:8px 0" }, h("span", { class: "puce" }, p.actuel || "sans statut"), "→", h("span", { class: "puce chaude" }, p.propose)),
        h("div", { class: "sous" }, `« ${p.raison} » — ${p.de}, ${dateFr(p.le) || p.le}`),
        h("div", { class: "sous", title: p.sujet }, p.sujet),
        h("div", { class: "boutons", style: "margin-top:10px" },
          bouton("Appliquer", "avion", async () => {
            const a = await ecrire("appliquer_proposition", i);
            if (!a) return;
            if (!a.ok) return toast(a.erreur, true);
            toast(`${entreprise} : ${p.propose}`);
            ligne.remove();
            redessiner();
          }, "plein"),
          bouton("Ignorer", null, () => ligne.remove())));
      return ligne;
    }));
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Statuts depuis mes courriels"), h("div", { class: "sous" }, "Lecture seule : rien n'est envoyé."))),
    h("div", { class: "boutons" },
      bouton("Fichier .mbox…", "doc", () => lire("mbox")),
      bouton("Dossier .eml…", "doc", () => lire("eml")),
      bouton("Gmail (lecture seule)", "cloche", () => lire("gmail"))),
    info, liste);
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
}
