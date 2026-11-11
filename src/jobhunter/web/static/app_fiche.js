// --- Drawer: one offer --------------------------------------------------------------

function fermerTiroir() {
  $("tiroir").classList.remove("ouvert", "document", "large");
  $("voile").classList.remove("ouvert");
}

// A CV or a letter in the drawer (the user, 2026-10-27): its PDF to look at, the text of
// its .docx to change. Only the paragraphs changed are written, in place (their bold and
// italics stay); the PDF is made again from the .docx.
// `o` is the offer it was made for, or null when opened from the Documents screen.
// The PDF is shown as pictures of its pages (3.73): the web view's own PDF reader is not
// always there, and the user had to open Word to see the document. In « Modifier », the
// pages stay beside the text, and an element (a bullet, a line) is removed or added.
// `focus`: the paragraph to put the cursor in after the page is drawn again.
async function voirDocument(o, chemin, titre, mode = "apercu", focus = -1) {
  const corps = $("tiroir-corps");
  $("tiroir").classList.add("ouvert", "document");
  $("voile").classList.add("ouvert");
  const retour = o
    ? h("button", { class: "bouton", onclick: () => ouvrirOffre(o.id) }, svg("fleche"), "Retour à l'offre")
    : h("button", { class: "bouton", onclick: fermerTiroir }, svg("fleche"), "Fermer");
  corps.replaceChildren(h("div", { class: "vide" }, "Chargement…"));
  if (!window.pywebview) return corps.replaceChildren(retour, h("div", { class: "vide" }, HORS_APPLI));
  const d = await window.pywebview.api.document(chemin);
  if (!d || !d.ok) return corps.replaceChildren(retour, h("div", { class: "vide" }, d ? d.erreur : "Lecture impossible."));
  const textes = [...d.paragraphes];
  const place = h("div");
  // The document as it will be sent: its pages as pictures, else the PDF, else its text.
  const pagesDoc = () => {
    if ((d.pages || []).length) {
      return h("div", { class: "apercu-pages", "aria-label": titre },
        d.pages.map((b, i) => h("img", { src: `data:image/png;base64,${b}`, alt: `${titre}, page ${i + 1}` })));
    }
    if (d.pdf) {
      const octets = Uint8Array.from(atob(d.pdf), (c) => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([octets], { type: "application/pdf" }));
      return h("iframe", { class: "apercu-doc", src: url, title: titre });
    }
    // No PDF (no LibreOffice): its text, without the layout.
    return h("div", {},
      h("div", { class: "sous", style: "margin-bottom:12px" }, "Aperçu du texte, sans la mise en page : installe LibreOffice (libreoffice.org) pour voir le document tel qu'il sera envoyé."),
      h("div", { class: "texte-doc" }, textes.filter((t) => t.trim()).map((t) => h("p", {}, t))));
  };
  const montrer = (m) => {
    mode = d.docx ? m : "apercu";  // a PDF alone: shown, not edited
    $("tiroir").classList.toggle("large", mode === "texte");
    onglets.replaceChildren(d.docx ? segment([["apercu", "Aperçu"], ["texte", "Modifier"]], mode, montrer) : "");
    place.classList.toggle("remplit-doc", mode === "apercu");  // style.css: the pages fill the drawer
    if (mode === "apercu") return place.replaceChildren(pagesDoc());
    const ajuster = (t) => { t.style.height = "auto"; t.style.height = `${t.scrollHeight + 2}px`; };
    const zones = [];
    const lignes = textes.map((t, i) => {
      if (!t.trim()) return null;
      const z = h("textarea", {
        class: "champ-texte para-doc", rows: 1, readonly: !d.modifiables[i], "data-i": String(i),
        title: d.modifiables[i] ? null : "Contient un lien : à modifier dans Word.",
        "aria-label": `Élément ${i + 1}`,
        oninput: (e) => { textes[i] = e.target.value.replace(/\n/g, " "); ajuster(e.target); },
      }, t);
      zones.push(z);
      return h("div", { class: "ligne-doc" }, z,
        h("div", { class: "outils-ligne" },
          h("button", { class: "mini", title: "Ajouter un élément après celui-ci", "aria-label": "Ajouter un élément après", onclick: () => structurer("ajouter", i) }, "+"),
          h("button", { class: "mini", title: "Supprimer cet élément", "aria-label": "Supprimer l'élément", onclick: () => structurer("supprimer", i) }, "×")));
    }).filter(Boolean);
    place.replaceChildren(h("div", { class: "edition-cote" },
      h("div", {},
        h("div", { class: "sous", style: "margin-bottom:10px" }, "Change un texte puis « Enregistrer » ; + ajoute un élément de même forme juste après, × le retire. Le PDF est refait à chaque fois."),
        h("div", { class: "edition-doc" }, lignes),
        h("div", { class: "boutons", style: "margin-top:12px" },
          bouton("Enregistrer", "doc", () => enregistrer(), "plein"),
          bouton("Annuler les changements", "", () => voirDocument(o, chemin, titre, "texte")))),
      h("div", { class: "cote-apercu" }, pagesDoc())));
    requestAnimationFrame(() => {
      zones.forEach(ajuster);
      const z = zones.find((x) => x.dataset.i === String(focus));
      if (z) { z.focus(); z.select(); z.scrollIntoView({ block: "center" }); }
    });
  };
  const changes = () => textes.some((t, i) => t !== d.paragraphes[i]);
  // `garder`: stay in « Modifier » (the text changes saved before a + or ×).
  const enregistrer = async (garder = false) => {
    const r = await window.pywebview.api.enregistrer_document(chemin, d.paragraphes, textes);
    if (!r || !r.ok) { toast(r ? r.erreur : "Lecture impossible.", true); return false; }
    if (!r.modifies) {
      if (r.refuses || !garder) toast(r.refuses ? "Rien n'a pu être écrit : le fichier a changé, recharge-le." : "Rien n'a changé.", !!r.refuses);
      return !r.refuses;
    }
    if (garder) return true;
    toast(`${r.modifies} paragraphe(s) modifié(s)${r.pdf ? ", PDF refait" : ", PDF non refait (LibreOffice ?)"}.`);
    voirDocument(o, chemin, titre, "texte");
    return true;
  };
  const structurer = async (action, i) => {
    if (changes() && !(await enregistrer(true))) return;
    const r = await window.pywebview.api.structurer_document(chemin, action, i, textes[i], action === "ajouter" ? "Nouvel élément" : "");
    if (!r || !r.ok) return toast(r ? r.erreur : "Lecture impossible.", true);
    if (!r.pdf) toast("PDF non refait (LibreOffice ?).", true);
    voirDocument(o, chemin, titre, "texte", action === "ajouter" ? i + 1 : -1);
  };
  const onglets = h("div");
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", { style: "min-width:0" }, h("h2", {}, titre), o ? h("div", { class: "sous" }, `${o.poste} · ${o.entreprise}`) : null)),
    h("div", { class: "boutons" }, retour, onglets, bouton("Ouvrir dans Word", "sortie", () => ouvrirFichier(d.docx))),
    place);
  montrer(mode);
}

// What to check before applying (programs/reposts, 3.67): the signals said in words, not
// only as the list's ⚑ sign. Observations: they change neither the score nor the order.
function carteSignaux(o) {
  const lignes = (o.signal || "").split(" · ").filter(Boolean).map((s) => {
    const m = s.match(/^republiée ×(\d+)/);
    if (m) return ["↻", `Republiée ${m[1]} fois en 90 jours`,
      "Une annonce remise en ligne sans cesse est souvent une offre « fantôme » (pas de recrutement en cours) ou un poste difficile à pourvoir. Vérifie sur le site de l'entreprise avant d'y passer du temps."];
    if (s.startsWith("⚠")) return ["⚠", `Condition éliminatoire : ${s.slice(1).trim()}`,
      "L'annonce l'exige explicitement : vérifie que tu la remplis."];
    const [etiquette, noms] = s.split(" : ");
    if (etiquette === "même texte") return ["≡", `Même texte chez ${noms}`,
      "Souvent un cabinet ou un site d'emploi qui reprend l'offre d'un employeur : mieux vaut postuler à la source."];
    if (etiquette === "doublon") return ["≡", `En double : ${noms}`, "La même offre sous un autre nom du même groupe."];
    return ["•", s, ""];
  });
  if (!lignes.length) return null;
  return h("div", { class: "carte signaux", role: "note" }, h("h3", {}, "À vérifier avant de postuler"),
    lignes.map(([signe, titre, aide]) => h("div", { class: "signal" },
      h("span", { class: "signe", "aria-hidden": "true" }, signe),
      h("div", {}, h("div", { class: "t" }, titre), aide ? h("div", { class: "sous" }, aide) : null))));
}

async function ouvrirOffre(id) {
  const corps = $("tiroir-corps");
  $("tiroir").classList.remove("document", "large");
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
      [o.lieu, o.contrat !== "non precise" && o.contrat, o.zone, o.date && `publiée le ${dateFr(o.date)}`, o.suivi]
        .map((t, i) => t && h("span", { class: i === 4 ? "puce chaude" : "puce" }, t)).filter(Boolean)),
    h("div", { class: "boutons" },
      bouton("Voir l'annonce", "sortie", () => ouvrir(o.url), "plein"),
      o.cv ? bouton("CV", "doc", () => voirDocument(o, o.cv, "CV")) : null,
      o.lettre ? bouton("Lettre", "doc", () => voirDocument(o, o.lettre, "Lettre")) : null,
      bouton(o.cv ? "Refaire CV et lettre" : "Préparer CV et lettre", "plume", () => lancer("documents", o.id)),
      ["postulé", "relancé", "entretien", "refus"].includes(o.suivi) ? null
        : bouton("J'ai envoyé cette candidature", "avion", () => declarerEnvoi(o.id), "chaud")),
    h("div", { class: "boutons secondaires" },
      ["pas intéressé", "expiré", "mauvaise"].includes(o.suivi)
        ? bouton("Finalement intéressé", "fleche", () => marquer(o.id, ""))
        : bouton("Pas intéressé", "", () => marquer(o.id, "pas intéressé")),
      ["postulé", "relancé"].includes(o.suivi) ? bouton("Brouillon de relance", "cloche", () => lancer("relance", o.id)) : null,
      // « Pas intéressé » and « Écarter… » side by side read as the same button (2026-11-03):
      // the first keeps the offer, set aside, undoable; the second takes it out of the
      // queue for good, with a reason. That one goes with the rarer actions.
      plus([
        ["Retirer de la file, avec un motif…", "", () => ecarter([o.id])],
        ["Chercher sur le web", "loupe", () => ecrire("chercher_web", o.id)],
        [o.description ? "Recharger la description" : "Récupérer la description", "fleche", () => lancer("description", o.id)],
        ["J'ai un compte sur ce site", "cle", async () => {
          const r = await ecrire("compte", o.id);
          if (r) toast(r.compte ? `Compte noté pour ${r.site}.` : `Compte retiré pour ${r.site}.`);
        }],
      ])),
    (() => {
      const st = h("select", { class: "choix" }, h("option", { value: "" }, "Pas de statut"),
        STATUTS.map((s) => h("option", { value: s, selected: s === o.suivi }, majuscule(s))));
      const note = h("textarea", { class: "champ-texte", rows: 3, placeholder: "Note (contact, impression, suite…)" }, o.note || "");
      const le = h("input", { class: "champ-texte", type: "date", value: o.postule_le || "" });
      return h("div", { class: "carte suivi-fiche" }, h("h3", {}, "Suivi"),
        h("div", { class: "champs-suivi" }, h("label", {}, "Statut", st), h("label", {}, "Date", le)),
        note,
        h("div", { class: "boutons" }, bouton("Enregistrer le suivi", "", async () => {
          const r = await ecrire("suivre", o.id, { statut: st.value, note: note.value, date: le.value });
          if (r) { toast("Suivi enregistré."); ouvrirOffre(o.id); redessiner(); }
        }, "plein"), o.envoi ? h("span", { class: "sous" }, `envoi ${o.envoi}`) : null));
    })(),
    carteSignaux(o),
    o.pourquoi ? h("div", { class: "carte description" }, h("h3", {}, "Pourquoi ce score"),
      h("div", { translate: "no" }, traduireFit(o.pourquoi))) : null,
    h("div", { class: "carte description" },
      o.description ? h("div", { translate: "no" }, o.description) : "Pas de description enregistrée pour cette offre."),
    h("dl", { class: "paires" },
      h("dt", {}, "Domaine"), h("dd", {}, o.domaine ? lisible(o.domaine) : "—"),
      h("dt", {}, "Source"), h("dd", { title: o.source, class: "avec-logo" }, logoSource(o.source), o.source ? lisible(o.source.split(":")[0]) : "—"),
      h("dt", {}, "Statut"), h("dd", {}, o.statut || "—"),
      h("dt", {}, "Score fin"), h("dd", {}, o.fit_fin ? o.fit_fin.toFixed(2) : "—"),
      h("dt", {}, "Expérience"), h("dd", {}, o.exp_requise ? `${o.exp_requise} ans` : "—"),
      h("dt", {}, "Salaire"), h("dd", {}, o.salaire || "—"),
      h("dt", {}, "Télétravail"), h("dd", {}, o.teletravail || "—")),
  ].filter(Boolean));
}
