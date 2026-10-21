"""English interface texts, indexed by the displayed French text.

Part of jobhunter.app (step F5). The French text stays the source: a text missing
from here is displayed in French. English is also the fallback of the other
languages (see `langue`), so this catalogue is the reference list of the texts to
translate: tests/test_language.py checks that every language covers it.
"""

NOM = "English"
RELANCER = "Restart JobHunter to use the English interface."

TEXTES: dict[str, str] = {
    # navigation and header
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
    "Langue / Language…": "Language / Langue…",
    # offers table
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
    # card and tracking
    "Envoi confirmé": "Sending confirmed",
    "Ouvrir l'offre": "Open offer",
    "Pas intéressé": "Not interested",
    "Enregistrer": "Save",
    # base CV (drag-and-drop, CV panel)
    "Remplacer mon CV de base…": "Replace my base CV…",
    "Dépose un CV au format .docx ou .pdf.": "Drop a CV in .docx or .pdf format.",
    "Choisis ton nouveau CV de base": "Choose your new base CV",
    "Remplacer ton CV de base ({ancien}) par {cv} ? L'ancien est gardé à côté, en .bak.": "Replace your base CV ({ancien}) with {cv}? The old one is kept next to it, as .bak.",
    "CV de base remplacé : {nom}": "Base CV replaced: {nom}",
    "CV de base remplacé. Refaire maintenant les CV déjà préparés pour les offres ?": "Base CV replaced. Redo now the CVs already prepared for the offers?",
    "Refaire les CV": "Redo the CVs",
    # offer card: provenance and changes, queue watched
    "Canal": "Channel",
    "Action": "Action",
    "Télétravail": "Remote work",
    "Compétences": "Skills",
    "Correspondance ATS": "ATS match",
    "État lien": "Link status",
    "Salaire / Avantages": "Salary / Benefits",
    "Profil requis": "Required profile",
    "Missions / Compétences": "Duties / Skills",
    "Pourquoi": "Why",
    "Recruteur": "Recruiter",
    "Process": "Process",
    "URL": "URL",
    "Aussi à": "Also in",
    "Expérience requise : {n} ans": "Experience required: {n} years",
    "Dossier : prêt (CV et lettre lisibles, une page, coordonnées)": "Application file: ready (CV and letter readable, one page, contact details)",
    "Dossier à revoir": "Application file to review",
    "Trouvée par": "Found by",
    "collecte {a}": "collection {a}",
    "Modifiée par son site": "Changed by its site",
    "La file a changé sur le disque : vue mise à jour.": "The queue changed on disk: view updated.",
    "poste": "title",
    "salaire": "salary",
    "contrat": "contract",
    "localisation": "location",
    "Appels d'API aujourd'hui (tous profils) : ": "API calls today (all profiles): ",
    "(file : {fit}, recalcul au prochain re-score)": "(queue: {fit}, recomputed at the next re-score)",
    "Tester la connexion": "Test the connection",
    "Test de {nom} : une requête, aucune offre importée…": "Testing {nom}: one request, no offer imported…",
    "{nom} : connexion vérifiée, la clé fonctionne.": "{nom}: connection checked, the key works.",
    "{nom} : aucune clé enregistrée (Saisir la clé).": "{nom}: no key saved (Enter the key).",
    "{nom} : clé refusée par le service — vérifie-la ou crée-en une nouvelle.": "{nom}: key refused by the service — check it or create a new one.",
    "{nom} : quota atteint — la clé est bonne, réessaie demain.": "{nom}: quota reached — the key is fine, try again tomorrow.",
    "{nom} : le service répond mais en erreur — réessaie plus tard.": "{nom}: the service answers with an error — try again later.",
    "{nom} : pas de réponse (hors ligne ?).": "{nom}: no answer (offline?).",
    "Historique du score": "Score history",
    "description": "description",
    "re-score": "re-score",
    "règles changées": "rules changed",
    "Ma recherche": "My search",
    "Mots-clés de recherche": "Search keywords",
    "Une recherche par ligne (LinkedIn, Welcome to the Jungle…).": "One search per line (LinkedIn, Welcome to the Jungle…).",
    "Intitulés à garder": "Titles to keep",
    "Un intitulé doit contenir l'un de ces mots pour être collecté. Une ligne qui commence par re: est un motif.": "A title must contain one of these words to be collected. A line starting with re: is a pattern.",
    "Intitulés à écarter": "Titles to set aside",
    "Un intitulé qui contient l'un de ces mots est écarté.": "A title containing one of these words is set aside.",
    "Ces réglages appartiennent au profil actif. Ils servent à la prochaine collecte ; l'aperçu montre leur effet sur les offres déjà dans ta file.": "These settings belong to the active profile. They are used by the next collection; the preview shows their effect on the offers already in your queue.",
    "Rien n'est enregistré :": "Nothing is saved:",
    "Recherche enregistrée (profil d'avant : {bak}). Effet à la prochaine collecte.": "Search saved (previous profile: {bak}). It applies from the next collection.",
    "Aperçu en cours (filtre du moteur sur ta file)…": "Preview running (the engine's filter on your queue)…",
    "Aperçu impossible": "Preview impossible",
    "Sur les {total} offres de ta file : {apres} passent ce filtre (actuellement {avant}).": "Of the {total} offers in your queue: {apres} pass this filter (currently {avant}).",
    "Seraient écartées, par exemple :": "Would be set aside, for example:",
    "Élargir la recherche se voit à la prochaine collecte.": "Widening the search shows at the next collection.",
    "Le CV à lire": "The CV to read",
    "Rien de nouveau dans ce CV : ton profil a déjà tout.": "Nothing new in this CV: your profile already has it all.",
    "{c} compétence(s) ajoutée(s) au profil ; {r} recherche(s) ajoutée(s) à la liste (Enregistrer pour les garder).": "{c} skill(s) added to the profile; {r} search(es) added to the list (Save to keep them).",
    "Aperçu sur ma file": "Preview on my queue",
    "Suggestions depuis mon CV…": "Suggestions from my CV…",
    "Annuler les modifications": "Undo changes",
    "Suggestions depuis ton CV": "Suggestions from your CV",
    "Coche ce que tu veux ajouter. Une compétence vient de ton CV (la phrase est citée) ; une recherche n'ajoute rien à tes CV ni à tes lettres.": "Tick what you want to add. A skill comes from your CV (the sentence is quoted); a search adds nothing to your CVs or letters.",
    "Compétence": "Skill",
    "Recherche": "Search",
    "Ajouter la sélection": "Add the selection",
    # profiles
    "Renommer « {nom} »…": "Rename “{nom}”…",
    "Archiver « {nom} »…": "Archive “{nom}”…",
    "Nouveau nom du profil": "New name of the profile",
    "Profil renommé : {nom}": "Profile renamed: {nom}",
    "Archiver ce profil ? Son dossier est rangé dans profiles/_archives (rien n'est supprimé) et JobHunter redémarre sur le profil principal.": "Archive this profile? Its folder is moved to profiles/_archives (nothing is deleted) and JobHunter restarts on the main profile.",
    "Une collecte tourne pour ce profil : réessaie quand elle aura fini.": "A collection is running for this profile: try again when it has finished.",
    "Profils…": "Profiles…",
    "Recherche : {a}": "Search: {a}",
    "Tout effacer": "Clear all",
    "Collecte : {a} nouvelle(s) offre(s), {b} source(s) sur {c} ont répondu": "Collection: {a} new offer(s), {b} source(s) out of {c} answered",
    "refusées : {a}": "refused: {a}",
    "limitées : {a}": "rate-limited: {a}",
    "interrompues : {a}": "interrupted: {a}",
    "Recettes de nettoyage…": "Cleanup recipes…",
    "Recettes de nettoyage": "Cleanup recipes",
    "Colonnes ▾": "Columns ▾",
    "Vues ▾": "Views ▾",
    "Enregistrer la vue actuelle…": "Save the current view…",
    "Supprimer une vue": "Delete a view",
    "Vue par défaut (aucun filtre)": "Default view (no filter)",
    "Enregistrer la vue": "Save the view",
    "Nom de la vue (filtres, tri, recherche et colonnes actuels) :": "Name of the view (current filters, sort, search and columns):",
    "Vue enregistrée : {a}": "View saved: {a}",
    "Supprimer la vue « {a} » ?": "Delete the view “{a}”?",
    "Vue compacte": "Compact view",
    "Toutes les colonnes": "All columns",
    "● changements non enregistrés — Enregistrer (Ctrl+S)": "● unsaved changes — Save (Ctrl+S)",
    "Enregistrer les changements de « {a} » ?": "Save the changes to “{a}”?",
    "Changements non enregistrés": "Unsaved changes",
    "ouvert dans Word": "open in Word",
    "Une règle par ligne : champ | valeur à remplacer | nouvelle valeur. Une valeur doit correspondre au champ entier (majuscules et espaces ignorés) ; « re: » introduit un motif. Rejouer les mêmes recettes ne change rien la deuxième fois. Une offre à laquelle tu as postulé n'est jamais renommée.": 'One rule per line: field | value to replace | new value. A value must match the whole field (case and spaces ignored); "re:" starts a pattern. Replaying the same recipes changes nothing the second time. An offer you applied to is never renamed.',
    "Champ": "Field",
    "Avant": "Before",
    "Après": "After",
    "Remarque": "Note",
    "candidature : gardé": "applied: kept",
    "doublon : gardé": "duplicate: kept",
    "{a} changement(s), {b} écarté(s). Rien n'est écrit.": "{a} change(s), {b} set aside. Nothing is written.",
    "Recettes enregistrées : rien à changer dans la file.": "Recipes saved: nothing to change in the queue.",
    "Aperçu": "Preview",
    "Enregistrer et appliquer": "Save and apply",
    "entreprise": "company",
    "Documents à comparer…": "Documents to compare…",
    "Documents à comparer": "Documents to compare",
    "Tu as retouché ces documents à la main ; une version plus récente a été générée à côté. Rouge : seulement dans ta version. Vert : seulement dans la nouvelle. La version que tu ne gardes pas est mise de côté dans _a_comparer/_anciennes/, jamais supprimée.": "You edited these documents by hand; a newer version was generated next to them. Red: only in your version. Green: only in the new one. The version you do not keep is set aside in _a_comparer/_anciennes/, never deleted.",
    "Document": "Document",
    "Paragraphes différents": "Paragraphs that differ",
    "Aucun document en attente de comparaison.": "No document waiting to be compared.",
    "Lecture impossible : {a}": "Cannot read it: {a}",
    "Impossible pour l'instant ({a}) : le document est-il ouvert dans Word ?": "Not possible right now ({a}): is the document open in Word?",
    "Version mise de côté : {a}": "Version set aside: {a}",
    "Prendre la nouvelle version": "Take the new version",
    "Garder ma version": "Keep my version",
    "Dernière collecte": "Last collection",
    "suspendue": "suspended",
    "Suspendre / Reprendre": "Suspend / Resume",
    "Un site lu par le navigateur ne se suspend pas : retire-le.": "A site read by the browser cannot be suspended: remove it instead.",
    "⏸ {a} suspendue": "⏸ {a} suspended",
    "▶ {a} reprise": "▶ {a} resumed",
    "Principal": "Main",
    "Nouveau profil…": "New profile…",
    "Que faire de {cv} ?": "What to do with {cv}?",
    "Remplacer mon CV de base": "Replace my base CV",
    "Nouveau profil depuis ce CV": "New profile from this CV",
    "Le CV du nouveau profil": "The new profile's CV",
    "Nom du nouveau profil (par exemple : Chargée RSE à Lyon)": "Name of the new profile (for example: CSR officer in Lyon)",
    "Un profil de ce nom existe déjà.": "A profile with this name already exists.",
    "Nouveau profil « {nom} » : réponds aux questions dans la fenêtre de commande.": "New profile “{nom}”: answer the questions in the command window.",
    "Profil changé : JobHunter doit redémarrer pour l'ouvrir. Redémarrer maintenant ?": "Profile changed: JobHunter must restart to open it. Restart now?",
    "Le profil n'a pas été créé (les questions n'ont pas été terminées).": "The profile was not created (the questions were not finished).",
    "Profil créé. L'ouvrir maintenant ? (JobHunter redémarre)": "Profile created. Open it now? (JobHunter restarts)",
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
    # application
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
    # Access
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
    # Job sites
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
    # Maintenance menus and steps
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
    "Collecte chaque matin…": "Collect every morning…",
    "Statuts depuis mes courriels…": "Statuses from my emails…",
    "Statuts depuis mes courriels": "Statuses from my emails",
    "Lecture seule : les courriels sont lus et classés (refus, entretien, accusé de "
    "réception), jamais modifiés. Chaque statut proposé attend ton accord.": "Read-only: "
    "emails are read and classified (rejection, interview, acknowledgement), never "
    "changed. Each suggested status waits for your approval.",
    "Candidature": "Application",
    "Formule trouvée": "Phrase found",
    "{a} courriel(s) lus, {b} statut(s) à proposer.": "{a} email(s) read, {b} status(es) "
    "to suggest.",
    "Lecture des courriels…": "Reading emails…",
    'Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".': "Gmail reading: "
    'first run pip install "jobhunter[gmail]".',
    "Fichier .mbox": ".mbox file",
    "Dossier de fichiers .eml": "Folder of .eml files",
    "Fichier .mbox…": ".mbox file…",
    "Dossier .eml…": ".eml folder…",
    "Gmail (lecture seule)": "Gmail (read-only)",
    "Suivi occupé : réessaie dans un instant.": "Tracking busy: try again in a moment.",
    "Le suivi a changé entre-temps : rien écrit.": "The tracking changed meanwhile: nothing "
    "written.",
    "Appliquer": "Apply",
    "Ignorer": "Ignore",
    "La collecte quotidienne est déjà planifiée. La retirer ?": "The daily collection is "
    "already scheduled. Remove it?",
    "Collecter les offres chaque jour à quelle heure ? (format 08:00)": "Collect offers every "
    "day at what time? (format 08:00)",
    "Scan offres": "Scan offers",
    "Candidatures en lot": "Batch applications",
    "LinkedIn": "LinkedIn",
    # panel cells
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
    # Dialog boxes
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
    # offer list (counts and placeholders)
    "Sélectionne une offre dans le tableau.": "Select an offer in the table.",
    "Double-clic ou Entrée : fiche complète  ·  clic droit : actions  ·  Suppr : pas intéressé": "Double-click or Enter: full details  ·  right-click: actions  ·  Del: not interested",
    "aucune offre ne contient « {t} » — Echap ou ✕ pour effacer": "no offer contains “{t}” — Esc or ✕ to clear",
    "aucune offre ne passe les filtres — clique sur ▾ dans une entete pour les lever": "no offer passes the filters — click ▾ in a header to clear them",
    "aucune offre dans la file": "no offer in the queue",
    "sur {base}": "of {base}",
    "{m} masquée(s) :": "{m} hidden:",
    "{n} offre(s)": "{n} offer(s)",
    "rechercher…": "search…",
    "coller un lien d'offre…": "paste an offer link…",
}


# App log (langue.journal): a displayed line → its translation. A key with
# `{a}`, `{b}` is a template: each `{x}` takes the variable part of the line as
# is. The launched programs' summaries are in SORTIE, below.
JOURNAL = {
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
    # ── templates ──
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

# The output of the programs the app launches (collection, "TOUT FAIRE"), translated line
# by line like JOURNAL: summaries and headers, not the offer-by-offer detail
# (company and job names, which are not translated). Each template must live in
# the package's code (test_langue).
SORTIE = {
    # Collecte (jobhunter.sources)
    "── recherche restreinte à la FRANCE ──": "── search restricted to FRANCE ──",
    "── ATS APIs (greenhouse/lever/ashby/recruitee/smartrecruiters) ──": "── ATS APIs "
    "(greenhouse/lever/ashby/recruitee/smartrecruiters) ──",
    "── Workday (API publique des grands groupes) ──": "── Workday (public API of large groups) ──",
    "── LinkedIn recherche publique (guest) ──": "── LinkedIn public search (guest) ──",
    "── V.I.E / V.I.A (Business France) ──": "── V.I.E / V.I.A (Business France) ──",
    "── FIR / French SIF (100 % ISR-ESG) ──": "── FIR / French SIF (100% SRI-ESG) ──",
    "── Talent.com (agrégateur) ──": "── Talent.com (aggregator) ──",
    "── Indeed (page 1 des résultats — voir le commentaire de scan_indeed) ──": "── Indeed "
    "(results page 1 — see the scan_indeed comment) ──",
    "── APEC (API publique, annonce entière dans la liste) ──": "── APEC (public API, full "
    "posting in the list) ──",
    "── Glassdoor (page 1 de la recherche, France entière) ──": "── Glassdoor (search page "
    "1, all of France) ──",
    "── eFinancialCareers ({a}, {b} site(s), sitemap public, crawl-delay 10 s) ──": "── "
    "eFinancialCareers ({a}, {b} site(s), public sitemap, crawl-delay 10 s) ──",
    "── EURES (portail officiel UE, API publique, crawl-delay 10 s) ──": "── EURES (official "
    "EU portal, public API, crawl-delay 10 s) ──",
    "── France Travail (API officielle) ──": "── France Travail (official API) ──",
    "── Adzuna (API officielle, France + 7 pays) ──": "── Adzuna (official API, France + 7 "
    "countries) ──",
    "── Jooble (API officielle) ──": "── Jooble (official API) ──",
    "── Welcome to the Jungle (sitemap public, débit bridé) ──": "── Welcome to the Jungle "
    "(public sitemap, throttled) ──",
    "Scan : {a} offres uniques (non ecrit : --dry)": "Scan: {a} unique offers (not written: --dry)",
    "Scan : {a} offres uniques (→ {b})": "Scan: {a} unique offers (→ {b})",
    "Refus rencontrés (une collecte vide peut venir de là) :": "Refusals met (an empty "
    "collection can come from them):",
    "Rendement par source :": "Yield per source:",
    "{a} ramenées · {b} nouvelles · {c} pertinentes · {d} s": "{a} fetched · {b} new · {c} "
    "relevant · {d} s",
    "Merge {a}: +{b} nouvelles, {c} enrichies (desc), {d} liens promus (LinkedIn -> vrai "
    "site), {e} hors de France, {f} écartées à la main, {g} déjà rejetées par le tri, {h} "
    "pays écartés, {i} bruits purgés — {j} total": "Merge {a}: +{b} new, {c} enriched "
    "(desc), {d} links promoted (LinkedIn -> real site), {e} outside France, {f} set aside "
    "by hand, {g} already rejected by sorting, {h} countries set aside, {i} noise purged — "
    "{j} total",
    "→ re-score + descriptions manquantes : automatiques au prochain lancement de l'app.": "→ "
    "re-score + missing descriptions: automatic at the next app start.",
    "Le scan est conserve dans {a} : `jobhunter collect --fusion-seule` le fusionnera.": "The "
    "scan is kept in {a}: `jobhunter collect --fusion-seule` will merge it.",
    "! journal de rendement non écrit : {a}": "! yield log not written: {a}",
    # Descriptions (scrape_desc)
    "Rien à faire : --key ou --all requis.": "Nothing to do: --key or --all required.",
    "Aucune offre ciblée.": "No offer targeted.",
    "{a} offre(s) à récupérer…": "{a} offer(s) to fetch…",
    "── {a}/{b} — {c} ok — {d}s/offre, reste ~{e} min": "── {a}/{b} — {c} ok — {d}s/offer, "
    "~{e} min left",
    "=== {a}/{b} descriptions enregistrées (API) ===": "=== {a}/{b} descriptions saved (API) ===",
    "=== {a}/{b} descriptions enregistrées dans apply_queue.json ===": "=== {a}/{b} "
    "descriptions saved to apply_queue.json ===",
    "✅ {a} car. (via {b})": "✅ {a} chars (via {b})",
    "✖ relance navigateur impossible : {a}": "✖ browser restart failed: {a}",
    # Re-score (rescore_ats)
    "{a} ATS% + {b} fit re-scorés / {c}": "{a} ATS% + {b} fit re-scored / {c}",
    "Offres exigeant ≥3 ans d'expérience (fit pénalisé) : {a}": "Offers requiring ≥3 years "
    "of experience (fit penalised): {a}",
    "Distribution ATS% : {a}": "ATS% distribution: {a}",
    # Liens morts (recheck_dead)
    "Aucune offre à revérifier (filtre trop strict ?).": "No offer to recheck (filter too "
    "strict?).",
    "{a} offre(s) à revérifier en navigateur (status={b})…": "{a} offer(s) to recheck in the "
    "browser (status={b})…",
    "✖ {a} échecs d'affilée — arrêt (relance plus tard, reprise auto)": "✖ {a} failures in a "
    "row — stopping (run again later, resumes automatically)",
    "── checkpoint {a}/{b} — {c}s/lien, reste ~{d} min": "── checkpoint {a}/{b} — {c}s/link, "
    "~{d} min left",
    "=== {a}changements: {b} ===": "=== {a}changes: {b} ===",
    # Export (export_queue_csv)
    "! apply_queue.json introuvable": "! apply_queue.json not found",
    "(suivi.json illisible : {a} — export sans le suivi)": "(suivi.json unreadable: {a} — "
    "export without the tracking)",
    "=== {a} offres -> {b} ({c} Ko) ===": "=== {a} offers -> {b} ({c} KB) ===",
    "rotation : {a} supprimé": "rotation: {a} deleted",
    # Alertes (notify_matches)
    "historique de notification remis à zéro": "notification history reset",
    "aucune NOUVELLE offre fit >= {a} (déjà notifiées : {b})": "no NEW offer with fit >= {a} "
    "(already notified: {b})",
    "=== {a} nouvelle(s) offre(s) fit >= {b} ===": "=== {a} new offer(s) with fit >= {b} ===",
    "[dry] pas de notification, historique inchangé": "[dry] no notification, history unchanged",
    "notifié — {a} marquée(s), historique {b}": "notified — {a} marked, history {b}",
    "non notifié (toast KO) — {a} marquée(s), historique {b}": "not notified (toast failed) — "
    "{a} marked, history {b}",
    "! toast échoué : {a}": "! toast failed: {a}",
    "! toast impossible : {a}": "! toast unavailable: {a}",
    # Update (mise_a_jour)
    "Version installée : {a} · disponible : {b}": "Installed version: {a} · available: {b}",
    "Version installée : {a} · c'est la plus récente.": "Installed version: {a} · it is the "
    "latest.",
    "Téléchargement de {a} …": "Downloading {a} …",
    "Signature de l'auteur vérifiée.": "Author's signature verified.",
    "Signature de l'auteur vérifiée : {a} fichiers de la {b}.": "Author's signature "
    "verified: {a} files of {b}.",
    "(Version non signée : empreinte publiée vérifiée.)": "(Unsigned version: published "
    "checksum verified.)",
    "(Version {a} non signée : la clé de l'auteur n'est pas encore publiée.)": "(Version {a} "
    "unsigned: the author's key is not published yet.)",
    "! Mise à jour refusée : {a}. Rien n'a été installé.": "! Update refused: {a}. Nothing "
    "was installed.",
    "! Mise à jour refusée : {a}. Rien n'a été modifié.": "! Update refused: {a}. Nothing "
    "was changed.",
    "! Téléchargement impossible ({a}) : la page des versions s'ouvre.": "! Download failed "
    "({a}): the releases page opens.",
    "L'installateur s'ouvre : suis ses étapes. Tes données sont gardées.": "The installer "
    "opens: follow its steps. Your data is kept.",
    # Collect every morning (planification)
    "Collecte planifiée chaque jour à {a}, si l'ordinateur est allumé. Journaux : {b}.": "Collection "
    "scheduled every day at {a}, if the computer is on. Logs: {b}.",
    "Collecte quotidienne retirée.": "Daily collection removed.",
    "La tâche n'a pas pu être créée : {a}": "The task could not be created: {a}",
    "La tâche n'a pas pu être retirée : {a}": "The task could not be removed: {a}",
    "Heure invalide : « {a} » (format 08:00).": "Invalid time: “{a}” (format 08:00).",
    "Hors Windows : lance ./launchers/schedule.sh depuis le dossier de JobHunter.": "Outside Windows: "
    "run ./launchers/schedule.sh from the JobHunter folder.",
}

# The lines of the fit explanation (scoring.fit.expliquer): language.explication.
FIT = {
    "{axe} {pct} (x{poids}) : {mots}": "{axe} {pct} (x{poids}): {mots}",
    "vocabulaire : {v}/10": "vocabulary: {v}/10",
    "intitulé du métier visé en second (finance)": "title of the second target job (finance)",
    "intitulé du cœur de cible : plafond 10": "title at the core of the target: cap 10",
    "plafond {cap} (cœur {c}, complément {k})": "cap {cap} (core {c}, complement {k})",
    "intitulé HSE : plafond {cap}": "HSE title: cap {cap}",
    "métier hors cible dans l'intitulé : plafond {cap}": "off-target job in the title: cap {cap}",
    "intitulé junior « {mot} » : +{b}": "junior title “{mot}”: +{b}",
    "intitulé senior : -{m}": "senior title: -{m}",
    "intitulé écarté « {mot} » : -2": "excluded title “{mot}”: -2",
    "annonce redigee en {lg} : plafond {p}": "posting written in {lg}: cap {p}",
    "annonce exige {x} : plafond {p}": "posting requires {x}: cap {p}",
    "{n} an(s) d'expérience demandés : -{m}": "{n} year(s) of experience required: -{m}",
}
