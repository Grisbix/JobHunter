// --- Companies, job boards, access and keys (the desktop's panels) ------------------

// Sector lists (sources.company_lists): tick a sector to collect its companies, then
// untick one company inside it if needed. Any profession gets companies in two clicks,
// not only finance (the user, 2026-10-27).
function carteListes(listes, rafraichir) {
  const lignes = listes.map((l) => {
    const suivies = l.entreprises.filter((e) => e.suivie).length;
    const detail = h("div", { class: "entreprises-liste", hidden: true },
      l.entreprises.map((e) => h("label", { class: `case${l.active ? "" : " pale"}` },
        h("input", { type: "checkbox", checked: e.suivie, disabled: !l.active, onchange: async (ev) => {
          const r = await ecrire("suivre_dans_liste", e.outil, e.cle, ev.target.checked);
          if (r) rafraichir(); else ev.target.checked = !ev.target.checked;
        } }), e.nom)));
    return h("div", { class: `liste-secteur${l.active ? " active" : ""}` },
      h("div", { class: "tete-liste" },
        h("label", { class: "case" },
          h("input", { type: "checkbox", checked: l.active, onchange: async (ev) => {
            const r = await ecrire("activer_liste", l.id, ev.target.checked);
            if (r) { toast(r.message); rafraichir(); } else ev.target.checked = !ev.target.checked;
          } }),
          h("span", { class: "t" }, l.titre)),
        h("span", { class: "sous" }, l.active ? `${suivies} sur ${l.entreprises.length} entreprises` : `${l.entreprises.length} entreprises`),
        bouton("Voir les entreprises", "", () => { detail.hidden = !detail.hidden; })),
      h("div", { class: "sous" }, l.description), detail);
  });
  return h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Listes par secteur")),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Coche les secteurs à collecter. Dans une liste, décoche une entreprise pour la laisser de côté ; ses offres déjà en file restent."),
    ...lignes);
}

ONGLETS_SOURCES.entreprises = async (vue) => {
  const [d, listes] = await Promise.all([appel("entreprises"), appel("listes_entreprises")]);
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  let filtre = "";
  const ouverts = new Set();
  const corps = h("tbody");
  const compte = h("span", { class: "sous" });
  const dessiner = () => {
    const f = filtre.toLowerCase();
    const lignes = d.lignes.filter((l) => !f || `${l.nom} ${l.outil} ${(l.flux || [l]).map((x) => x.lien).join(" ")}`.toLowerCase().includes(f));
    compte.textContent = `${lignes.length} / ${d.lignes.length} entreprises (${nombre(d.lignes.reduce((s, l) => s + (l.flux || [l]).length, 0))} flux) · ${nombre(d.lignes.reduce((s, l) => s + l.offres, 0))} offres en file`
      + (d.muettes ? ` · ${d.muettes} muette(s) depuis ${d.muet_jours} j` : "");
    // One row per company; its feeds (API, site…) open under it when it has several.
    const actions = (x, nom) => [
      bouton("", "sortie", () => ecrire("ouvrir_lien", x.lien), "icone"),
      x.site ? null : bouton(x.suspendue ? "Reprendre" : "Suspendre", "", async () => {
        const r = await ecrire("suspendre_entreprise", x.id);
        if (r) { toast(r.message); ONGLETS_SOURCES.entreprises(vue); }
      }),
      bouton("Retirer", "", async () => {
        const ok = await dialogue(`Ne plus suivre « ${nom} » ?`, "Son adresse de flux sera retirée ; « Suspendre » la garde.", null, [["Retirer", "chaud", () => true]]);
        if (!ok) return;
        const r = await ecrire("retirer_entreprise", x.id);
        if (r) { toast(r.message); ONGLETS_SOURCES.entreprises(vue); }
      })];
    const etat = (x) => x.suspendue
      ? h("span", { class: "etiq gris", title: x.collecte }, x.auto ? "suspendue auto" : "suspendue")
      : x.collecte;
    corps.replaceChildren(...lignes.flatMap((l) => {
      const plusieurs = (l.flux || []).length > 1;
      const tete = h("tr", { class: l.offres ? "" : "pale" },
        h("td", {}, h("div", { class: "t" }, l.nom,
          l.ajoutee ? [" ", h("span", { class: "etiq", title: l.ajoutee }, "suivie auto")] : null)),
        h("td", {}, l.outil),
        h("td", {}, etat(l)),
        h("td", { class: "num" }, nombre(l.offres)),
        h("td", { class: "num" }, l.fit ?? "—"),
        h("td", {}, l.derniere || "—"),
        h("td", { class: "actions-ligne" }, ...(plusieurs
          ? [bouton("", "sortie", () => ecrire("ouvrir_lien", l.lien), "icone"),
            bouton(`${l.flux.length} flux ${ouverts.has(l.id) ? "▴" : "▾"}`, "", () => {
              ouverts.has(l.id) ? ouverts.delete(l.id) : ouverts.add(l.id);
              dessiner();
            })]
          : actions(l, l.nom))));
      if (!plusieurs || !ouverts.has(l.id)) return [tete];
      return [tete, ...l.flux.map((x) => h("tr", { class: `sous-ligne${x.offres ? "" : " pale"}` },
        h("td", {}, h("div", { class: "sous" }, "↳ ", x.lien || x.id)),
        h("td", {}, x.outil),
        h("td", {}, etat(x)),
        h("td", { class: "num" }, nombre(x.offres)),
        h("td", { class: "num" }, x.fit ?? "—"),
        h("td", {}, x.derniere || "—"),
        h("td", { class: "actions-ligne" }, ...actions(x, l.nom))))];
    }));
  };
  const champ = h("input", { class: "champ-texte", placeholder: "Adresse de sa page carrière, ou nom de l'entreprise (annuaire)" });
  const ajouter = async () => {
    const v = champ.value.trim();
    if (!v) return;
    if (!/^https?:\/\//.test(v)) return ouvrirAnnuaire(v, () => ONGLETS_SOURCES.entreprises(vue));
    const r = await ecrire("suivre_entreprise", v);
    if (r) { toast(r.message); ONGLETS_SOURCES.entreprises(vue); }
  };
  champ.addEventListener("keydown", (e) => { if (e.key === "Enter") ajouter(); });
  dessiner();
  vue.replaceChildren(h("div", { class: "colonne" }, listes ? carteListes(listes, () => ONGLETS_SOURCES.entreprises(vue)) : null, h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Entreprises suivies"), compte),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Chaque entreprise est lue par son outil de recrutement (API publique) ou, à défaut, par son site carrière. Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres »."),
    h("div", { class: "ligne-ajout" }, champ, bouton("Ajouter", "", ajouter, "plein"), bouton("Annuaire…", "loupe", () => ouvrirAnnuaire(champ.value.trim(), () => ONGLETS_SOURCES.entreprises(vue)))),
    h("label", { class: "champ", style: "margin:12px 0" }, svg("loupe"), h("input", { type: "search", placeholder: "Filtrer : entreprise, outil ou adresse", oninput: (e) => { filtre = e.target.value; dessiner(); } })),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Entreprise", "Lue par", "Dernière collecte", "Offres", "Score max", "Dernière", ""].map((t) => h("th", {}, t)))),
      corps)))));
};

// Every company a collection has seen, kept after its offers leave the queue (the user,
// 2026-10-27: « note l'entreprise quelque part pour trouver ses offres »).
ONGLETS_SOURCES.vues = async (vue) => {
  const d = await appel("entreprises_vues");
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  let filtre = "";
  const corps = h("tbody");
  const compte = h("span", { class: "sous" });
  const offres = (l) => {
    Object.assign(filtresOffres, { texte: l.nom, statut: "toutes", page: 0 });
    aller("offres");
  };
  const dessiner = () => {
    const f = filtre.toLowerCase();
    const lignes = d.lignes.filter((l) => !f || `${l.nom} ${l.sites.join(" ")} ${l.outil || ""}`.toLowerCase().includes(f));
    compte.textContent = `${nombre(lignes.length)} / ${nombre(d.lignes.length)} entreprises`;
    corps.replaceChildren(...lignes.slice(0, 300).map((l) => h("tr", { class: l.offres ? "" : "pale" },
      h("td", {}, h("div", { class: "t" }, l.nom)),
      h("td", { class: "num" }, nombre(l.offres)),
      h("td", { class: "num" }, l.fit ?? "—"),
      h("td", {}, l.sites.join(", ") || "—"),
      h("td", {}, l.derniere || "—"),
      h("td", { class: "actions-ligne" },
        l.offres ? bouton("Ses offres", "loupe", () => offres(l)) : null,
        l.suivie ? h("span", { class: "etiq gris" }, "suivie")
          : l.url_flux ? bouton(`Suivre (${l.outil})`, "", async () => {
            const r = await ecrire("suivre_entreprise", l.url_flux);
            if (r) { toast(r.message); ONGLETS_SOURCES.vues(vue); }
          }) : null))));
  };
  dessiner();
  vue.replaceChildren(h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Entreprises vues"), compte,
      bouton("Chercher leurs offres", "loupe", () => lancer("sites_carrieres")),
      bouton("Suivre celles à score ≥ 7", "signet", async () => {
        const n = d.lignes.filter((l) => l.url_flux && !l.suivie && (l.fit || 0) >= 7).length;
        if (!n) return toast("Aucune entreprise bien notée à suivre.");
        const ok = await dialogue(`Suivre ${n} entreprise(s) ?`, "Chacune est d'abord vérifiée : une requête à son outil de recrutement, suivie seulement si elle a des offres ouvertes.", null, [["Suivre", "", () => true]]);
        if (!ok) return;
        const r = await ecrire("suivre_vues", 7);
        if (r) { toast(r.message); ONGLETS_SOURCES.vues(vue); }
      })),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Chaque collecte note les entreprises de ses offres, même écartées ou fermées depuis. « Chercher leurs offres » demande à 150 d'entre elles, chaque matin aussi, ce qu'elles ont d'ouvert sur leur site carrière : par leur outil de recrutement, par freehire, sinon en devinant leur outil par leur nom (annuaire Workday compris) ou en lisant leur page carrière. L'outil trouvé est retenu pour la fois suivante. « Suivre » lit ensuite ses offres à chaque collecte, quand son lien d'offre donne son outil de recrutement."),
    h("label", { class: "champ", style: "margin:12px 0" }, svg("loupe"), h("input", { type: "search", placeholder: "Filtrer : entreprise, site ou outil", oninput: (e) => { filtre = e.target.value; dessiner(); } })),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Entreprise", "Offres", "Score max", "Vue sur", "Dernière fois", ""].map((t) => h("th", {}, t)))),
      corps))));
};

async function ouvrirAnnuaire(texte, apres) {
  const champ = h("input", { class: "champ-texte", value: texte || "", placeholder: "Nom de l'entreprise" });
  const liste = h("div", { class: "motifs" });
  let minuteur;
  const chercher = async () => {
    const r = (await appel("annuaire", champ.value)) || [];
    liste.replaceChildren(...(r.length ? r.map((e) => h("button", { class: "motif", disabled: e.suivi, onclick: async () => {
      const x = await ecrire("suivre_annuaire", e.outil, e.jeton);
      if (x) { toast(x.message); e.suivi = true; chercher(); apres && apres(); }
    } }, `${e.nom} · ${e.outil_nom}${e.suivi ? " (déjà suivie)" : ""}`)) : [h("div", { class: "sous" }, "Aucune entreprise de ce nom dans les annuaires Lever, Ashby, Greenhouse, Workday.")]));
  };
  champ.addEventListener("input", () => { clearTimeout(minuteur); minuteur = setTimeout(chercher, 250); });
  chercher();
  const workday = h("div", { class: "sous", style: "margin-top:12px" }, "Workday : son annuaire se construit sur ton PC, depuis Common Crawl (archive publique du web).",
    bouton("Construire l'annuaire Workday", "fleche", () => lancer("annuaire_workday")));
  await dialogue("Annuaire des entreprises", "Lever, Ashby, Greenhouse et Workday : clique une entreprise pour la suivre.", h("div", {}, champ, liste, workday), []);
}

ONGLETS_SOURCES.sites = async (vue) => {
  const d = await appel("sites_offres");
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  const genre = h("select", { class: "choix" }, d.types.map((t) => h("option", { value: t }, t === "board" ? "site d'offres (adresse)" : `${t} (slug)`)));
  const champ = h("input", { class: "champ-texte", placeholder: "https://… ou le slug de l'entreprise" });
  const ajouter = async () => {
    if (await ecrire("ajouter_site_offres", genre.value, champ.value)) { toast("Ajouté."); ONGLETS_SOURCES.sites(vue); }
  };
  champ.addEventListener("keydown", (e) => { if (e.key === "Enter") ajouter(); });
  vue.replaceChildren(h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Sites d'offres et flux ATS"), h("span", { class: "compte" }, d.lignes.length)),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Un slug ATS est lu par son API ; un site d'offres est lu par « Scrape les sites »."),
    h("div", { class: "ligne-ajout" }, genre, champ, bouton("Ajouter", "", ajouter, "plein")),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Type", "Source", "Offres en file", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, d.lignes.map((l) => h("tr", {},
        h("td", {}, l.type), h("td", {}, l.source), h("td", { class: "num" }, nombre(l.offres)),
        h("td", { class: "actions-ligne" },
          bouton("", "sortie", () => ecrire("ouvrir_lien", l.lien), "icone"),
          bouton("Retirer", "", async () => {
            const ok = await dialogue(`Retirer « ${l.source} » ?`, "Ses offres déjà en file restent.", null, [["Retirer", "chaud", () => true]]);
            if (ok && await ecrire("retirer_site_offres", l.type, l.type === "board" ? l.lien : l.source)) ONGLETS_SOURCES.sites(vue);
          })))))))));
};

ONGLETS_SOURCES.acces = async (vue) => {
  const d = await appel("acces");
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  const recharger = () => ONGLETS_SOURCES.acces(vue);
  vue.replaceChildren(h("div", { class: "grille" },
    h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Collecte des offres"),
        h("span", { class: "sous" }, "Appels d'API aujourd'hui (tous profils) : " + d.quotas.map((q) => `${q.nom} ${q.n}${q.plafond ? "/" + q.plafond : ""}`).join(" · "))),
      h("div", { class: "sous", style: "margin:4px 0 12px" }, "État de la dernière collecte de chaque source. Un refus n'est pas réessayé avant 30 jours."),
      h("table", { class: "tableau-simple" },
        h("thead", {}, h("tr", {}, ["Source", "Accès", "Dernier état", "Collecte du", ""].map((t) => h("th", {}, t)))),
        h("tbody", {}, d.sources.map((s) => h("tr", {},
          h("td", {}, s.libelle), h("td", {}, s.acces),
          h("td", {}, h("span", { class: `etat-source ${s.gravite}` }, s.etat)), h("td", {}, s.le || "—"),
          h("td", { class: "actions-ligne" },
            s.cle ? bouton("Saisir la clé", "cle", () => saisirCle(s.source, recharger)) : null,
            s.cle ? bouton("Tester", "", async () => { const r = await ecrire("tester_cle", s.source); if (r) toast(r.message, !r.reussi); }) : null,
            bouton("Collecter", "collecte", async () => { if (await ecrire("collecter_source", s.source)) suivreTache(); }, s.bloque ? "" : "plein")))))),
      h("div", { class: "boutons", style: "margin-top:12px" }, bouton("Rendement des sources", "", async () => { if (await ecrire("rendement_sources")) suivreTache(); }))),
    h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Connexions pour candidater")),
      h("div", { class: "sous", style: "margin:4px 0 12px" }, "Tu te connectes toi-même ; les mots de passe restent dans le navigateur."),
      h("table", { class: "tableau-simple" },
        // The button's column at its width: a fifth of a narrow window cut it at the card's edge.
        h("colgroup", {}, h("col", {}), h("col", {}), h("col", {}), h("col", {}), h("col", { style: "width:210px" })),
        h("thead", {}, h("tr", {}, ["Site", "Identifiant", "Session", "Vérifiée le", ""].map((t) => h("th", {}, t)))),
        h("tbody", {}, d.connexions.map((c) => h("tr", {},
          h("td", {}, c.site), h("td", {}, c.identifiant || "—"),
          h("td", {}, h("span", { class: `etat-source ${c.gravite}` }, c.session)), h("td", {}, c.le || "—"),
          h("td", { class: "actions-ligne" }, bouton("Ouvrir la connexion", "sortie", async () => {
            if (await ecrire("connexion", c.site)) toast("Console ouverte : connecte-toi dans le navigateur.");
          })))))),
      h("div", { class: "boutons", style: "margin-top:12px" }, bouton("Vérifier les sessions", "", async () => {
        if (await ecrire("connexion", "", true)) toast("Vérification lancée dans une console.");
      })))));
};

// A key is typed here and goes straight to its file; it is never shown again.
async function saisirCle(nom, apres) {
  const c = await ecrire("cle_champs", nom);
  if (!c) return;
  const champs = c.champs.map((x) => [x.nom, h("input", { class: "champ-texte", type: x.secret ? "password" : "text", autocomplete: "off",
    placeholder: c.deja ? "laisser vide : garder la valeur enregistrée" : "" })]);
  const valeurs = await dialogue(`Clé ${c.libelle}`, `${c.deja ? "Une clé est déjà enregistrée. " : ""}Crée-la sur ${c.obtenir}. Elle va dans son fichier, jamais ailleurs.`,
    h("div", { class: "formulaire" }, champs.map(([n, e]) => h("label", { class: "champ-form" }, n, e))),
    [["Enregistrer", "plein", () => Object.fromEntries(champs.map(([n, e]) => [n, e.value]))]]);
  champs.forEach(([, e]) => { e.value = ""; });
  if (!valeurs) return;
  if (await ecrire("saisir_cle", nom, valeurs)) { toast(`Clé ${c.libelle} enregistrée.`); apres && apres(); }
}

// --- Statistics (the desktop's Stats panel) -----------------------------------------

ECRANS.stats = {
  titre: "Statistiques",
  actions: () => [bouton("Rafraîchir", "fleche", () => redessiner())],
  async dessiner(vue) {
    const d = await appel("stats");
    if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
    // The shares only when asked for, in Réglages (the user, 2026-11-04: too busy).
    const avecPc = !!(reglagesCourants && reglagesCourants.pourcentages);
    const pc = (p) => (p == null || !avecPc ? "" : `${Math.round(p * 100)} %`);
    const e = d.entonnoir;
    const barres = (s) => {
      const max = Math.max(1, ...s.lignes.map((l) => (typeof l.n === "number" ? l.n : 0)));
      return h("div", { class: "verre panneau" }, h("div", { class: "titre-ligne" }, h("h2", {}, s.titre)),
        s.lignes.map((l) => h("div", { class: "ligne-barre" },
          h("span", { class: "nom", title: lisible(l.nom) }, lisible(l.nom)),
          h("span", { class: "piste" }, h("span", { class: "rempli", style: `width:${100 * l.n / max}%` })),
          h("span", { class: "num" }, `${nombre(l.n)} ${pc(l.part)}`.trim()))));
    };
    // No hole between panels (the user, 2026-10-27): the sections go into three stacks of
    // about the same height, the longest first, and the last panel of each stack grows.
    const piles = [[], [], []];
    const hauteur = (pile) => pile.reduce((n, s) => n + s.lignes.length + 3, 0);
    [...d.sections].sort((a, b) => b.lignes.length - a.lignes.length)
      .forEach((s) => piles.reduce((m, p) => (hauteur(p) < hauteur(m) ? p : m)).push(s));
    const parChamp = (ch, titre) => (e.par[ch].length < 2 ? null : h("div", {}, h("h3", {}, titre),
      h("dl", { class: "paires alignees" }, e.par[ch].map((x) => [h("dt", {}, x.val),
        h("dd", {}, `${x.env} envoyée(s) · ${x.rep} réponse(s), ${x.ent} entretien(s)${avecPc ? ` · ${pc(x.rep / x.env)}` : ""}`)]))));
    // The applications sent make a fourth stack, on the left, instead of a full-width band:
    // the screen holds in a 1280 × 720 window when it opens (the user, 2026-10-28).
    const envoyees = e ? h("div", { class: "verre panneau envoyees" },
        h("div", {}, h("h2", {}, "Candidatures envoyées"),
          h("dl", { class: "paires alignees" },
            avecPc ? [h("dt", {}, "Taux de réponse"), h("dd", {}, e.taux != null ? pc(e.taux) : "—")] : null,
            h("dt", {}, "Sans réponse depuis 30 jours"), h("dd", {}, String(e.silence)),
            h("dt", {}, "Délai médian de réponse"), h("dd", {}, e.delai_median == null ? "—" : `${Math.round(e.delai_median)} j (sur ${e.n_delais} réponse(s) datée(s))`))),
        parChamp("contrat", "Par contrat"), parChamp("domaine", "Par domaine")) : null;
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "cartes-stats" }, d.cartes.map((c) => h("div", { class: "verre carte-stat" },
        h("div", { class: "chiffre" }, nombre(c.n)), h("div", { class: "sous" }, c.nom)))),
      h("div", { class: "piles-stats" }, envoyees ? h("div", { class: "pile" }, envoyees) : null,
        piles.filter((p) => p.length).map((p) => h("div", { class: "pile" }, p.map(barres))))));
  },
};
