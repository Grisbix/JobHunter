"""Textes de l'interface en anglais, indexés par le texte français affiché.

Partie de jobhunter.app (étape F5). Le texte français reste la source : un texte absent
d'ici s'affiche en français. `python outils/textes_interface.py` liste ceux qui manquent.
"""

EN: dict[str, str] = {
    # navigation et en-tête
    "JOBHUNTER": "JOBHUNTER",
    "RECHERCHE D'EMPLOI": "JOB SEARCH",
    "Offres": "Offers",
    "Mes CV": "My CVs",
    "Entreprises": "Companies",
    "Sites d'offres": "Job sites",
    "Statistiques": "Statistics",
    "Accès": "Access",
    "ACTIONS": "ACTIONS",
    "Actualiser les offres": "Refresh offers",
    "Maintenance ▸": "Maintenance ▸",
    "Maintenance ▾": "Maintenance ▾",
    "Recharger": "Reload",
    "Outils": "Tools",
    "↶ Retour": "↶ Back",
    "Retour": "Back",
    "Dossier": "Folder",
    "Arrêter": "Stop",
    "Langue : English": "Language: français",
    # tableau des offres
    "OFFRES EN FILE": "OFFERS IN QUEUE",
    "FIT ≥ 8": "FIT ≥ 8",
    "CANDIDATURES ENVOYÉES": "APPLICATIONS SENT",
    "Chercher": "Search",
    "Voir les masquées": "Show hidden",
    "Colonnes": "Columns",
    "Postuler": "Apply",
    "Écarter…": "Dismiss…",
    "Supprimer": "Delete",
    "Décocher": "Untick",
    "En-tête : filtrer  ·  Double-clic : fiche": "Header: filter  ·  Double-click: details",
    "FICHE DE L’OFFRE": "OFFER DETAILS",
    "Agrandir": "Expand",
    "Suivi et note ▸": "Tracking and note ▸",
    "Sélectionne une offre": "Select an offer",
    "Ajouter une offre": "Add an offer",
    "Statut": "Status",
    "Entreprise": "Company",
    "Poste": "Position",
    "Domaine": "Field",
    "Fit": "Fit",
    "Contrat": "Contract",
    "Zone": "Area",
    "Lieu": "Location",
    "Pays": "Country",
    "Région": "Region",
    "Date offre": "Posted",
    "Lien": "Link",
    "Suivi": "Tracking",
    "Date": "Date",
    "Note": "Note",
    "▲  Croissant": "▲  Ascending",
    "▼  Décroissant": "▼  Descending",
    "double-clic = seulement celle-ci": "double-click = only this one",
    "Garder": "Keep",
    "Exclure": "Exclude",
    "Tout": "All",
    # fiche et suivi
    "Envoi confirmé": "Sending confirmed",
    "Ouvrir l'offre": "Open offer",
    "Pas intéressé": "Not interested",
    "Enregistrer": "Save",
    "Associer un compte": "Link an account",
    "Retirer le compte": "Remove account",
    "Voir CV": "View CV",
    "Voir lettre": "View letter",
    "Fermer": "Close",
    "Chargement…": "Loading…",
    "Description": "Description",
    "CV": "CV",
    "Lettre": "Letter",
    "Ouvrir": "Open",
    "aucun CV/lettre lié à cette offre": "no CV or letter linked to this offer",
    "Annuler": "Cancel",
    "Écarter": "Dismiss",
    "ou une autre raison :": "or another reason:",
    # candidature
    "Ouverture de Chrome…": "Opening Chrome…",
    "Observation de la page…": "Watching the page…",
    "Programme terminé.": "Program finished.",
    # Mes CV
    "Chercher une offre (entreprise, poste)": "Search an offer (company, position)",
    "Sélectionne un CV ou une lettre à gauche": "Select a CV or a letter on the left",
    "CV ⇄ lettre": "CV ⇄ letter",
    "Faits du CV": "CV facts",
    "MAJ lettres": "Update letters",
    "Renommer (mon nom)": "Rename (my name)",
    "↑ Haut": "↑ Top",
    "↓ Bas": "↓ Bottom",
    # Accès
    "Accès aux sources": "Access to sources",
    "Rafraîchir": "Refresh",
    "Collecte des offres": "Offer collection",
    "Connexions pour candidater": "Sign-ins for applying",
    "État de la dernière collecte de chaque source. Un refus n'est pas "
    "réessayé avant 30 jours. Double-clic sur une source à clé : saisir sa clé.": "State of "
    "each source's last run. A refusal is not retried for 30 days. Double-click a source "
    "that needs a key to enter it.",
    "Saisir la clé": "Enter key",
    "Collecter cette source": "Collect this source",
    "Rendement des sources": "Source yield",
    "accès libre, aucune clé à saisir.": "open access, no key needed.",
    "saisis d'abord sa clé.": "enter its key first.",
    "Tu te connectes toi-même ; les mots de passe restent dans Chrome.": "You sign in "
    "yourself; passwords stay in Chrome.",
    "Clé": "Key",
    "Enregistrée dans Scripts/{f}, sur ce PC seulement (ignoré par git).": "Saved in "
    "Scripts/{f}, on this PC only (ignored by git).",
    "Une clé est déjà posée : un champ laissé vide la garde.": "A key is already set: a "
    "field left empty keeps it.",
    "Afficher la saisie": "Show input",
    "Elle sert dès la prochaine collecte ; « Collecter cette source » l'essaie.": "It is "
    "used from the next collection; “Collect this source” tries it.",
    "Obtenir une clé": "Get a key",
    "Filtrer : entreprise, outil ou adresse": "Filter: company, tool or address",
    "Adresse de sa page carrière, ou nom de l'entreprise (annuaire)": "Its careers page "
    "address, or the company name (directory)",
    "Annuaire": "Directory",
    "Annuaire des entreprises": "Company directory",
    "3 600 entreprises lues par l'API publique de Lever, Ashby ou Greenhouse. "
    "Double-clic ou Entrée : suivre.": "3,600 companies read through the public API of "
    "Lever, Ashby or Greenhouse. Double-click or Enter: follow.",
    "Identifiant": "Identifier",
    "Outil": "Tool",
    "suivie": "followed",
    "Ouvrir la connexion": "Open sign-in page",
    "Vérifier les sessions": "Check sessions",
    "Source": "Source",
    "Dernier état": "Last state",
    "Collecte du": "Collected on",
    "Site": "Site",
    "Identifiant (email)": "Login (email)",
    "Session": "Session",
    "Vérifiée le": "Checked on",
    "Flux ATS des entreprises (Greenhouse, Lever, Ashby…)": "Company ATS feeds (Greenhouse, "
    "Lever, Ashby…)",
    "Flux Workday des entreprises": "Company Workday feeds",
    "LinkedIn — pages publiques, sans connexion": "LinkedIn — public pages, no sign-in",
    "EURES (offres européennes)": "EURES (European offers)",
    "FIR (finance responsable)": "FIR (responsible finance)",
    "France Travail — API officielle": "France Travail — official API",
    "Adzuna — API officielle": "Adzuna — official API",
    "Jooble — API officielle": "Jooble — official API",
    # Entreprises
    "Entreprises suivies": "Followed companies",
    "Chaque entreprise est lue par son outil de recrutement (API publique) "
    "ou, à défaut, par son site carrière. Double-clic : ouvrir sa page. "
    "Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres ».": "Each company "
    "is read through its recruiting tool (public API) or, failing that, its careers site. "
    "Double-click: open its page. General job sites (LinkedIn, WTJ…) are under “Job sites”.",
    "Lue par": "Read by",
    "Fit max": "Best fit",
    "Dernière": "Latest",
    "Page": "Page",
    "Suivre": "Follow",
    "Ne plus suivre": "Unfollow",
    "Lire les sites carrière": "Read careers sites",
    # Sites d'offres
    "Sites d'offres généraux": "General job sites",
    "Ajouter": "Add",
    "Retirer": "Remove",
    "Scanner maintenant": "Scan now",
    "Analyse…": "Analysing…",
    # Statistiques
    "Liens OK": "Working links",
    "Avec description": "With description",
    "Dossiers préparés": "Prepared applications",
    "Postulé": "Applied",
    "Relancé": "Followed up",
    "Entretien": "Interview",
    "Refus": "Rejected",
    "Catégorie": "Category",
    "Nb": "Count",
    "Répartition": "Breakdown",
    "Type": "Type",
    # menus Maintenance et étapes
    "Scrape les sites": "Scrape sites",
    "Rattrapage 31 j": "31-day catch-up",
    "Sonder flux ATS": "Probe ATS feeds",
    "Sonder flux Workday": "Probe Workday feeds",
    "Sonder mots-clés": "Probe keywords",
    "Sync docs+format": "Sync docs + format",
    "Export CSV": "Export CSV",
    "Relire les lettres": "Review letters",
    "Pourquoi ce fit": "Why this fit",
    "Contrôler les dossiers": "Check application files",
    "URLs mortes": "Dead URLs",
    "Recheck 404": "Recheck 404",
    "Re-score": "Re-score",
    "Relances": "Follow-ups",
    "Alerte matchs": "Match alert",
    "Clés France Travail": "France Travail keys",
    "Fermer Chrome": "Close Chrome",
    "Tester accès aux sites": "Test site access",
    "Tests live (lent, ouvre un navigateur)": "Live tests (slow, opens a browser)",
    "1/6 Scan offres (ATS + LinkedIn + V.I.E)": "1/6 Scan offers (ATS + LinkedIn + V.I.E)",
    "3/6 Re-score fit + ATS": "3/6 Re-score fit + ATS",
    "4/6 Verif liens morts": "4/6 Check dead links",
    "5/6 Export CSV": "5/6 Export CSV",
    "6/6 Alerte nouveaux matchs": "6/6 New match alert",
    "Sources & offres": "Sources & offers",
    "Documents": "Documents",
    "Hygiène de la file": "Queue hygiene",
    "Accès & diagnostic": "Access & diagnostics",
    "CV/lettres…": "CVs/letters…",
    "Homepages": "Homepages",
    "Mettre à jour JobHunter": "Update JobHunter",
    "Scan offres": "Scan offers",
    "Candidatures en lot": "Batch applications",
    "LinkedIn": "LinkedIn",
    # cellules des panneaux
    "libre": "free",
    "clé": "key",
    "pas encore mesurée": "not measured yet",
    "clé à créer": "key to create",
    "clé refusée": "key refused",
    "vérifie-la": "check it",
    "ok": "ok",
    "refusé": "refused",
    "limité": "rate-limited",
    "partiel": "partial",
    "rien à prendre": "nothing new",
    "À revérifier": "Recheck",
    "Jamais vérifié": "Never checked",
    "Connecté": "Signed in",
    "Déconnecté": "Signed out",
    "Bloqué": "Blocked",
    "Erreur": "Error",
    "Indéterminé": "Unknown",
    "site (navigateur)": "site (browser)",
    "plan du site": "sitemap",
    "CV de base": "Base CVs",
    "Dossiers par offre": "Applications by offer",
    "prêts": "ready",
    "PDF à refaire": "PDF to redo",
    "incomplet": "incomplete",
    "autres : affine la recherche": "more: refine the search",
    # Boîtes de dialogue
    "Confirmer l'envoi": "Confirm submission",
    "As-tu envoyé cette candidature ?": "Did you submit this application?",
    "Supprimer les offres": "Delete offers",
    "Supprimer {n} offre(s) cochée(s) de la liste ?\n\n"
    "Une copie est gardée dans Scripts/_corbeille/ — rien n'est perdu.\n"
    "Pour qu'elles ne reviennent pas au prochain scan, préfère\n"
    "« Écarter » : le motif est retenu.": "Delete {n} ticked offer(s) from the list?\n\n"
    "A copy is kept in Scripts/_corbeille/ — nothing is lost.\n"
    "To keep them from coming back in the next scan, prefer\n"
    "“Dismiss”: the reason is remembered.",
    "JobHunter — mise à jour": "JobHunter — update",
    "La mise à jour n'a pas abouti ; le détail est dans "
    "le journal. Tes données n'ont pas été touchées.": "The update did not complete; "
    "details are in the log. Your data was not touched.",
    "Version {v} installée. Relancer JobHunter maintenant ?": "Version {v} installed. "
    "Restart JobHunter now?",
    "JobHunter — mise à jour disponible": "JobHunter — update available",
    "La version {v} est disponible (installée : {installee}).\n\n"
    "L'installer maintenant ? Ton profil, ton CV, tes lettres et ton suivi ne "
    "sont pas touchés, et la version d'avant est sauvegardée.": "Version {v} is available "
    "(installed: {installee}).\n\nInstall it now? Your profile, CV, letters and tracking "
    "are not touched, and the previous version is backed up.",
    "pas avant le": "not before",
    "offres": "offers",
    "offre": "offer",
}


# Journal de l'app (langue.journal) : une ligne affichée → sa traduction. Une clé avec
# des `{a}`, `{b}` est un modèle : chaque `{x}` reprend tel quel le morceau variable de la
# ligne. La sortie des programmes lancés n'est pas traduite (le moteur parle français).
JOURNAL_EN = {
    # ── lignes fixes ──
    "Sélectionne d'abord une offre.": "Select an offer first.",
    "Coche d'abord des offres (colonne ☐).": "Tick some offers first (☐ column).",
    "✗ un autre programme écrit suivi.json — réessaie dans un instant.": "✗ another program "
    "is writing suivi.json — try again in a moment.",
    "Rien à annuler.": "Nothing to undo.",
    "⏳ suivi.json occupé par un autre programme — réessaie dans un instant.": "⏳ suivi.json "
    "is busy with another program — try again in a moment.",
    "✗ un autre programme modifie la file — réessaie dans un instant.": "✗ another program "
    "is changing the queue — try again in a moment.",
    "Bilan de ce que la notation rate : python JobHunter.pyw exclusions": "What the scoring "
    "misses: python JobHunter.pyw exclusions",
    "Le panneau Candidatures est déjà ouvert.": "The Applications panel is already open.",
    "✗ édition réservée aux lettres/.txt — CV : 📂 Ouvrir (Word)": "✗ editing is for "
    "letters/.txt only — CV: 📂 Open (Word)",
    "Sélectionne d'abord un dossier d'offre dans la liste.": "Select an offer's folder in "
    "the list first.",
    "✗ édition intégrée réservée aux lettres/.txt — CV .docx : bouton 📂 Ouvrir (Word)": "✗ "
    "built-in editing is for letters/.txt only — CV .docx: 📂 Open (Word) button",
    "(clic droit sur l'offre → 🔔 Relance)": "(right-click the offer → 🔔 Follow-up)",
    "Prêt. « ▶ TOUT FAIRE » régénère.": "Ready. “▶ DO EVERYTHING” regenerates.",
    "⏳ tâche en cours.": "⏳ a task is running.",
    "⏳ un travail de fond écrit la file (descriptions ou sync docs).": "⏳ a background job "
    "is writing the queue (descriptions or document sync).",
    "Réessaie dans un instant — il se termine tout seul.": "Try again in a moment — it "
    "finishes on its own.",
    "▶ TOUT FAIRE — pipeline complet (6 etapes)": "▶ DO EVERYTHING — full pipeline (6 steps)",
    "🌐 Télécharge JobHunterSetup.exe sur la page ouverte, puis lance-le.": "🌐 Download "
    "JobHunterSetup.exe from the page that opened, then run it.",
    "⏳ Mise à jour : elle démarre dès que le travail en cours est fini.": "⏳ Update: it "
    "starts as soon as the current job is done.",
    "▶ Mise à jour de JobHunter": "▶ Updating JobHunter",
    "✅ TOUT FAIRE terminé.": "✅ DO EVERYTHING finished.",
    "(aucune tache en cours)": "(no task running)",
    "trace complète : Scripts/_logs/app_erreurs.log": "full trace: Scripts/_logs/app_erreurs.log",
    "Retour : aucune disposition à rétablir.": "Back: no layout to restore.",
    "✗ pas d'URL http pour récupérer la description": "✗ no http URL to fetch the description",
    "✅ description récupérée": "✅ description fetched",
    "✗ description introuvable (page JS/mur login ?)": "✗ description not found (JS page "
    "or login wall?)",
    "(pas d'URL → pas de host)": "(no URL → no host)",
    "Sélectionne d'abord une source dans la liste.": "Select a source in the list first.",
    "Selectionne d'abord un site dans la liste.": "Select a site in the list first.",
    "↪ c'est un site d'offres général → ajoute-le dans « Sites d'offres »": "↪ this is a "
    "general job site → add it under “Job sites”",
    "déjà suivi": "already followed",
    "Sélectionne d'abord une entreprise dans la liste.": "Select a company in the list first.",
    "✗ colle une URL http d'offre.": "✗ paste an http offer URL.",
    "Raccourcis : Echap retour · Alt+Gauche annule agrandir/rétrécir · Ctrl+R recharger · "
    "F5 tout faire · Ctrl+B barre · dans le tableau : Ctrl+Entree postuler, Ctrl+A/D "
    "cocher/decocher, Ctrl+Z annuler · Ctrl+L coller un lien · Ctrl+W arreter · Suppr pas "
    "intéressé": "Shortcuts: Esc back · Alt+Left undo enlarge/shrink · Ctrl+R reload · F5 do "
    "everything · Ctrl+B sidebar · in the table: Ctrl+Enter apply, Ctrl+A/D tick/untick, "
    "Ctrl+Z undo · Ctrl+L paste a link · Ctrl+W stop · Del not interested",
    # ── modèles ──
    "📌 statut: {a} → {b}": "📌 status: {a} → {b}",
    "! écriture suivi.json KO: {a}": "! writing suivi.json failed: {a}",
    "⊖ {a} offre(s) « pas intéressé » — masquées, Ctrl+Z pour annuler.": "⊖ {a} offer(s) "
    "“not interested” — hidden, Ctrl+Z to undo.",
    "✗ annulation impossible pour l'instant ({a}) — réessaie.": "✗ cannot undo right now "
    "({a}) — try again.",
    "↶ annulé ({a} offre(s)).": "↶ undone ({a} offer(s)).",
    "! écriture sélection KO: {a}": "! writing the selection failed: {a}",
    "ATTENTION : {a}, pas l'offre elle-meme{b}.": "WARNING: {a}, not the offer itself{b}.",
    "🔍 recherche web: {a}": "🔍 web search: {a}",
    "! exclusions.py introuvable: {a}": "! exclusions.py not found: {a}",
    "! écriture queue KO: {a}": "! writing the queue failed: {a}",
    "✕ {a} offre(s) écartée(s) — « {b} ». {c} nouvelle(s) exclusion(s) ; elles ne "
    "reviendront pas au scan.": "✕ {a} offer(s) dismissed — “{b}”. {c} new exclusion(s); "
    "they will not come back in the scan.",
    "! copie de sauvegarde KO ({a}) — suppression ANNULÉE.": "! backup copy failed ({a}) — "
    "deletion CANCELLED.",
    "🗑 {a} offre(s) supprimée(s) — copie dans Scripts/_corbeille/{b}": "🗑 {a} offer(s) "
    "deleted — copy in Scripts/_corbeille/{b}",
    "📮 Candidatures : {a} offre(s), panneau ouvert. Chrome s'ouvre.": "📮 Applications: {a} "
    "offer(s), panel open. Chrome is opening.",
    "💾 enregistré : {a}": "💾 saved: {a}",
    "! sauvegarde KO: {a}": "! save failed: {a}",
    "📄 PDF resynchronisé : {a}": "📄 PDF resynced: {a}",
    "✗ {a} : pièce manquante ({b})": "✗ {a}: missing document ({b})",
    "ℹ {a} description(s) manquante(s) — récupération auto en fond…": "ℹ {a} missing "
    "description(s) — fetching automatically in the background…",
    "✅ descriptions: +{a} récupérées ({b} restantes, dont Indeed/anti-bot).": "✅ "
    "descriptions: +{a} fetched ({b} left, incl. Indeed/anti-bot).",
    "🔁 sync docs : {a}": "🔁 document sync: {a}",
    "🔎 scan auto : +{a} offre(s). {b}": "🔎 auto scan: +{a} offer(s). {b}",
    "🔎 scan auto : {a}": "🔎 auto scan: {a}",
    "🔔 {a} candidature(s) à relancer : {b}": "🔔 {a} application(s) to follow up: {b}",
    "📧 brouillon relance ouvert ({a}) — envoie-le puis passe le statut à « relancé ».": "📧 "
    "follow-up draft opened ({a}) — send it, then set the status to “relancé”.",
    "▶ {a} — fenêtre CONSOLE ouverte. Chrome s'ouvre ; tape Entrée après chaque envoi. "
    "Ferme la console pour arrêter.": "▶ {a} — CONSOLE window opened. Chrome is opening; "
    "press Enter after each submission. Close the console to stop.",
    "! lancement console KO: {a}": "! console launch failed: {a}",
    "⏹ arrete (arbre du PID {a}).": "⏹ stopped (PID {a} tree).",
    "! arret KO ({a}) — repli sur terminate": "! stop failed ({a}) — falling back to terminate",
    "! panne interne [{a}] — {b}": "! internal error [{a}] — {b}",
    "✗ TOUT FAIRE interrompu à l'étape « {a} ».": "✗ DO EVERYTHING stopped at step “{a}”.",
    "－ compte retiré: {a}": "－ account removed: {a}",
    "Associer un compte ajouté: {a}": "Account link added: {a}",
    "! écriture comptes_sites.json KO: {a}": "! writing comptes_sites.json failed: {a}",
    "💾 suivi enregistré: {a} → {b}": "💾 tracking saved: {a} → {b}",
    "＋ site carrière ajouté, lu par le navigateur : {a}": "＋ careers site added, read by "
    "the browser: {a}",
    "✗ {a} : flux introuvable dans sources_config.json": "✗ {a}: feed not found in "
    "sources_config.json",
    "－ {a} ne sera plus collectée": "－ {a} will no longer be collected",
    "＋ ajouté : {a}": "＋ added: {a}",
    "－ retiré : {a}": "－ removed: {a}",
    "🔎 analyse de l'offre : {a}": "🔎 analysing the offer: {a}",
    "＋ flux {a} {b} — lu par API dès la prochaine collecte ({c})": "＋ {a} feed {b} — read "
    "by API from the next collection ({c})",
    "＋ flux {a} {b} — lu par API dès la prochaine collecte": "＋ {a} feed {b} — read by API "
    "from the next collection",
    "déjà suivi : {a} ({b})": "already followed: {a} ({b})",
    "déjà suivi : {a}": "already followed: {a}",
}
