"""English interface texts, indexed by the displayed French text.

Shared by both windows (jobhunter.app.language, jobhunter.web.i18n) since 3.29;
it was jobhunter.app.texts_en. The French text stays the source: a text missing
from here is displayed in French. English is also the fallback of the other
languages (see `langue`), so this catalogue is the reference list of the texts to
translate: tests/test_language.py checks that every language covers it.
"""

NOM = "English"
RELANCER = "Restart JobHunter to use the English interface."

TEXTES: dict[str, str] = {
    # 3.15: indicators, history, kept posting, answers
    "offres en file": "offers in queue",
    "candidatures envoyées": "applications sent",
    "▶ Candidatures envoyées": "▶ Applications sent",
    "entretiens": "interviews",
    "sans réponse depuis 30 jours": "no answer for 30 days",
    "sur {n} réponse(s) datée(s)": "over {n} dated answer(s)",
    "{r} réponse(s), {e} entretien(s) · {p}": "{r} answer(s), {e} interview(s) · {p}",
    # navigation and header
    "JOBHUNTER": "JOBHUNTER",
    "Mes CV": "My CVs",
    "Entreprises": "Companies",
    "Accès": "Access",
    "ACTIONS": "ACTIONS",
    "Actualiser les offres": "Refresh offers",
    "↶ Retour": "↶ Back",
    "Retour": "Back",
    # offers table
    "Chercher": "Search",
    "Postuler": "Apply",
    "Suivi et note ▸": "Tracking and note ▸",
    "Fit": "Fit",
    "Lien": "Link",
    "Note": "Note",
    "Garder": "Keep",
    "Exclure": "Exclude",
    "Tout": "All",
    # card and tracking
    "Envoi confirmé": "Sending confirmed",
    # base CV (drag-and-drop, CV panel)
    "Remplacer mon CV de base…": "Replace my base CV…",
    "Choisis ton nouveau CV de base": "Choose your new base CV",
    # offer card: provenance and changes, queue watched
    "Canal": "Channel",
    "Action": "Action",
    "État lien": "Link status",
    "Pourquoi": "Why",
    "Process": "Process",
    "URL": "URL",
    "Aussi à": "Also in",
    "Dossier à revoir": "Application file to review",
    "collecte {a}": "collection {a}",
    "poste": "title",
    "salaire": "salary",
    "contrat": "contract",
    "localisation": "location",
    "Appels d'API aujourd'hui (tous profils) : ": "API calls today (all profiles): ",
    "{nom} : connexion vérifiée, la clé fonctionne.": "{nom}: connection checked, the key works.",
    "{nom} : aucune clé enregistrée (Saisir la clé).": "{nom}: no key saved (Enter the key).",
    "{nom} : clé refusée par le service — vérifie-la ou crée-en une nouvelle.": "{nom}: key refused by the service — check it or create a new one.",
    "{nom} : quota atteint — la clé est bonne, réessaie demain.": "{nom}: quota reached — the key is fine, try again tomorrow.",
    "{nom} : le service répond mais en erreur — réessaie plus tard.": "{nom}: the service answers with an error — try again later.",
    "{nom} : pas de réponse (hors ligne ?).": "{nom}: no answer (offline?).",
    "description": "description",
    "re-score": "re-score",
    "Mots-clés de recherche": "Search keywords",
    "Intitulés à garder": "Titles to keep",
    "Rien n'est enregistré :": "Nothing is saved:",
    "Suggestions depuis mon CV…": "Suggestions from my CV…",
    "Annuler les modifications": "Undo changes",
    "Suggestions depuis ton CV": "Suggestions from your CV",
    "Compétence": "Skill",
    # profiles
    "Renommer « {nom} »…": "Rename “{nom}”…",
    "Archiver ce profil ? Son dossier est rangé dans profiles/_archives (rien n'est supprimé) et JobHunter redémarre sur le profil principal.": "Archive this profile? Its folder is moved to profiles/_archives (nothing is deleted) and JobHunter restarts on the main profile.",
    "Une collecte tourne pour ce profil : réessaie quand elle aura fini.": "A collection is running for this profile: try again when it has finished.",
    "Profils…": "Profiles…",
    "Recettes de nettoyage…": "Cleanup recipes…",
    "Recettes de nettoyage": "Cleanup recipes",
    "Lancer la collecte du matin": "Run the morning collection",
    "Collecte du matin : {a} ✓": "Morning collection: {a} ✓",
    " · en erreur : {a}": " · in error: {a}",
    "Collecte en cours depuis {a}": "Collection running since {a}",
    "Collecte interrompue ({a}) — {b}": "Collection interrupted ({a}) — {b}",
    "Collecte arrêtée ({a} : {b}) — {c}": "Collection stopped ({a}: {b}) — {c}",
    "Aucune collecte du matin enregistrée": "No morning collection recorded",
    "Pas de collecte depuis {a}": "No collection since {a}",
    "dernière réussie : {a}": "last successful: {a}",
    "aucune réussie": "none successful",
    "aujourd'hui {a}": "today {a}",
    "hier {a}": "yesterday {a}",
    "Enregistrer la vue actuelle…": "Save the current view…",
    "Supprimer la vue « {a} » ?": "Delete the view “{a}”?",
    "Enregistrer les changements de « {a} » ?": "Save the changes to “{a}”?",
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
    "Enregistrer et appliquer": "Save and apply",
    "entreprise": "company",
    "Documents à comparer…": "Documents to compare…",
    "Documents à comparer": "Documents to compare",
    "Tu as retouché ces documents à la main ; une version plus récente a été générée à côté. Rouge : seulement dans ta version. Vert : seulement dans la nouvelle. La version que tu ne gardes pas est mise de côté dans _a_comparer/_anciennes/, jamais supprimée.": "You edited these documents by hand; a newer version was generated next to them. Red: only in your version. Green: only in the new one. The version you do not keep is set aside in _a_comparer/_anciennes/, never deleted.",
    "Aucun document en attente de comparaison.": "No document waiting to be compared.",
    "Lecture impossible : {a}": "Cannot read it: {a}",
    "Impossible pour l'instant ({a}) : le document est-il ouvert dans Word ?": "Not possible right now ({a}): is the document open in Word?",
    "Version mise de côté : {a}": "Version set aside: {a}",
    "Prendre la nouvelle version": "Take the new version",
    "Garder ma version": "Keep my version",
    "Dernière collecte": "Last collection",
    "suspendue": "suspended",
    "Un site lu par le navigateur ne se suspend pas : retire-le.": "A site read by the browser cannot be suspended: remove it instead.",
    "⏸ {a} suspendue": "⏸ {a} suspended",
    "▶ {a} reprise": "▶ {a} resumed",
    "Principal": "Main",
    "Nouveau profil depuis ce CV": "New profile from this CV",
    "Nouveau profil « {nom} » : vérifie et complète ce que JobHunter a lu dans le CV.": "New profile “{nom}”: check and complete what JobHunter read in the CV.",
    "Une tâche tourne sur ce profil : attends qu'elle finisse (ou « Arrêter »), puis change de profil.": 'A task is running on this profile: wait for it to finish (or "Stop"), then change profile.',
    "Le profil n'a pas été créé (les questions n'ont pas été terminées).": "The profile was not created (the questions were not finished).",
    "Profil créé. L'ouvrir maintenant ? (JobHunter redémarre)": "Profile created. Open it now? (JobHunter restarts)",
    "Voir CV": "View CV",
    "Voir lettre": "View letter",
    "Description": "Description",
    "CV": "CV",
    "ou une autre raison :": "or another reason:",
    # application
    "Ouverture de Chrome…": "Opening Chrome…",
    # Mes CV
    "Chercher une offre (entreprise, poste)": "Search an offer (company, position)",
    "↑ Haut": "↑ Top",
    "↓ Bas": "↓ Bottom",
    # Access
    "Rafraîchir": "Refresh",
    "Connexions pour candidater": "Sign-ins for applying",
    "État de la dernière collecte de chaque source. Un refus n'est pas "
    "réessayé avant 30 jours. Double-clic sur une source à clé : saisir sa clé.": "State of "
    "each source's last run. A refusal is not retried for 30 days. Double-click a source "
    "that needs a key to enter it.",
    "Saisir la clé": "Enter key",
    "saisis d'abord sa clé.": "enter its key first.",
    "Tu te connectes toi-même ; les mots de passe restent dans Chrome.": "You sign in "
    "yourself; passwords stay in Chrome.",
    "Clé": "Key",
    "Une clé est déjà posée : un champ laissé vide la garde.": "A key is already set: a "
    "field left empty keeps it.",
    "Afficher la saisie": "Show input",
    "Obtenir une clé": "Get a key",
    "Filtrer : entreprise, outil ou adresse": "Filter: company, tool or address",
    "Adresse de sa page carrière, ou nom de l'entreprise (annuaire)": "Its careers page "
    "address, or the company name (directory)",
    "Entreprises de mes offres : flux publics": "Companies of my offers: public feeds",
    "Annuaire": "Directory",
    "Annuaire des entreprises": "Company directory",
    "3 600 entreprises lues par l'API publique de Lever, Ashby ou Greenhouse. "
    "Double-clic ou Entrée : suivre.": "3,600 companies read through the public API of "
    "Lever, Ashby or Greenhouse. Double-click or Enter: follow.",
    "Identifiant": "Identifier",
    "Outil": "Tool",
    "Ouvrir la connexion": "Open sign-in page",
    "Vérifier les sessions": "Check sessions",
    "Dernier état": "Last state",
    "Collecte du": "Collected on",
    "Site": "Site",
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
    "Chaque entreprise est lue par son outil de recrutement (API publique) "
    "ou, à défaut, par son site carrière. Double-clic : ouvrir sa page. "
    "Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres ».": "Each company "
    "is read through its recruiting tool (public API) or, failing that, its careers site. "
    "Double-click: open its page. General job sites (LinkedIn, WTJ…) are under “Job sites”.",
    "Lue par": "Read by",
    "Dernière": "Latest",
    "Page": "Page",
    "Ne plus suivre": "Unfollow",
    "Lire les sites carrière": "Read careers sites",
    # Job sites
    "Ajouter": "Add",
    # Statistiques
    "Liens OK": "Working links",
    "Nb": "Count",
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
    "Alerte matchs": "Match alert",
    "Clés France Travail": "France Travail keys",
    "Fermer Chrome": "Close Chrome",
    "Tester accès aux sites": "Test site access",
    "Tests live (lent, ouvre un navigateur)": "Live tests (slow, opens a browser)",
    "Sources & offres": "Sources & offers",
    "Hygiène de la file": "Queue hygiene",
    "Accès & diagnostic": "Access & diagnostics",
    "CV/lettres…": "CVs/letters…",
    "Homepages": "Homepages",
    "Statuts depuis mes courriels…": "Statuses from my emails…",
    "Statuts depuis mes courriels": "Statuses from my emails",
    "Lecture seule : les courriels sont lus et classés (refus, entretien, accusé de "
    "réception), jamais modifiés. Chaque statut proposé attend ton accord.": "Read-only: "
    "emails are read and classified (rejection, interview, acknowledgement), never "
    "changed. Each suggested status waits for your approval.",
    "Candidature": "Application",
    "{a} courriel(s) lus, {b} statut(s) à proposer.": "{a} email(s) read, {b} status(es) "
    "to suggest.",
    "Lecture des courriels…": "Reading emails…",
    'Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".': "Gmail reading: "
    'first run pip install "jobhunter[gmail]".',
    "Fichier .mbox": ".mbox file",
    "Fichier .mbox…": ".mbox file…",
    "Dossier .eml…": ".eml folder…",
    "Gmail (lecture seule)": "Gmail (read-only)",
    "Ignorer": "Ignore",
    "La collecte quotidienne est déjà planifiée. La retirer ?": "The daily collection is "
    "already scheduled. Remove it?",
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
    "site (navigateur)": "site (browser)",
    "plan du site": "sitemap",
    "CV de base": "Base CVs",
    "prêts": "ready",
    "PDF à refaire": "PDF to redo",
    "incomplet": "incomplete",
    # Dialog boxes
    "Confirmer l'envoi": "Confirm submission",
    "As-tu envoyé cette candidature ?": "Did you submit this application?",
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
    "Version installée : {installee}": "Installed version: {installee}",
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
    "aucune offre ne passe les filtres — clique sur ▾ dans une entete pour les lever": "no offer passes the filters — click ▾ in a header to clear them",
    "aucune offre pour l'instant : clique « Actualiser les offres » à gauche": "no offers yet: click « Refresh offers » on the left",
    "sur {base}": "of {base}",
    "{n} offre(s)": "{n} offer(s)",
    # 3.18: the Profil panel (profiles, fit weights, skills)
    "Poids des axes": "Axis weights",
    "Combien compte chaque axe du profil quand l'annonce cite ses compétences.": "How much each axis of the profile counts when the posting cites its skills.",
    "Score qui vaut 10": "Score worth 10",
    "La somme pondérée des axes qui donne 10. Plus bas : les notes montent.": "The weighted sum of the axes that gives 10. Lower: the scores go up.",
    "Intitulé": "Title",
    "Ajouté ou retiré selon les mots du titre de l'offre.": "Added or removed according to the words of the offer's title.",
    "Relire la file": "Reread the queue",
    "Expérience demandée": "Experience asked for",
    "Retiré quand l'annonce demande au moins ce nombre d'années.": "Removed when the posting asks for at least this many years.",
    "Recalculer maintenant le fit enregistré de chaque offre de ta file ? Le tableau et le tri l'utilisent.": "Recompute now the stored fit of every offer in your queue? The table and the sorting use it.",
    "Lecture des offres de ta file… (une trentaine de secondes)": "Reading the offers of your queue… (about thirty seconds)",
    "Aucune offre choisie": "No offer chosen",
    "Rien à enregistrer : les poids sont ceux du profil.": "Nothing to save: the weights are the profile's.",
    "Lecture impossible": "Cannot read",
    "profil actif": "active profile",
    "profil principal": "main profile",
    "Compte pour les axes": "Counts for the axes",
    "Nouvelle": "New",
    "Compétences enregistrées (profil d'avant : {bak}).": "Skills saved (previous profile: {bak}).",
    "Un profil = une recherche complète : sa file d'offres, ses candidatures, ses CV et lettres, ses réglages. Ouvrir un autre profil redémarre JobHunter dessus ; un profil archivé est rangé, jamais supprimé.": "A profile = a complete search: its queue of offers, its applications, its CVs and letters, its settings. Opening another profile restarts JobHunter on it; an archived profile is put away, never deleted.",
    "Nouveau profil : choisis le CV (.docx ou .pdf) dont il partira": "New profile: choose the CV (.docx or .pdf) it will start from",
    "Donne un nom à la compétence.": "Give the skill a name.",
    "Rien à enregistrer.": "Nothing to save.",
    "{n} compétences dans le profil actif.": "{n} skills in the active profile.",
    # 3.19: statuses, contracts, statistics, settings
    "à postuler": "to apply",
    "postulé": "applied",
    "relancé": "followed up",
    "entretien": "interview",
    "refus": "rejected",
    "mauvaise": "poor match",
    "expiré": "expired",
    "CDI": "Permanent",
    "CDD": "Fixed-term",
    "Interim": "Temp",
    "Freelance": "Freelance",
    "V.I.E": "V.I.E",
    "Bénévolat": "Volunteer",
    "Saisonnier": "Seasonal",
    "Temps partiel": "Part-time",
    "Ne plus suivre « {nom} » ? Son adresse de flux sera retirée ; « Suspendre / Reprendre » la garde.": "Stop following “{nom}”? Its feed address will be removed; “Suspend / Resume” keeps it.",
    # Statistics: the default domain and the channel values.
    "Autre": "Other",
    "manuel": "manual",
    "auto": "automatic",
    "le {d}": "on {d}",
    "{n} j": "{n} d",
    "▶ Sur les offres à fit ≥ 8": "▶ Offers with fit ≥ 8",
    "{n} muette(s) depuis {j} j": "{n} silent for {j} d",
    "Paramètres": "Settings",
    "Langue de l'interface": "Interface language",
    "Version": "Version",
    "Vérifier les mises à jour": "Check for updates",
    # 3.19.1: the ⚙ menu
    "Vérifier les offres en ligne": "Check offers still online",
    # 3.19.1: the ⚑ column explained
    "⚑ Alerte — vide quand tout va bien": "⚑ Alert — empty when all is well",
    "⚠ condition éliminatoire (permis, nationalité, droit de travail, habilitation)": "⚠ knock-out condition (licence, nationality, right to work, clearance)",
    # 3.20.0: progress, the ☰ button, the Outils menu, the daily collection in Paramètres
    "Collecte automatique": "Automatic collection",
    "Chaque jour à l'heure choisie, l'ordinateur collecte les offres de tous tes profils, même si JobHunter est fermé.": "Every day at the chosen time, the computer collects the offers of all your profiles, even when JobHunter is closed.",
    "Pas planifiée.": "Not scheduled.",
    "☰ Menu": "☰ Menu",
    "{a}/{b} sources": "{a}/{b} sources",
    "~{d} restantes": "~{d} left",
    "Vérification {a}/{b}": "Check {a}/{b}",
    "Vérification des offres": "Offer check",
    # 3.21.0: places in « Ma recherche »
    "Où tu veux travailler": "Where you want to work",
    "Zones des offres mises à jour": "Offer zones updated",
    # 3.26: progress legend
    "✓ a répondu": "✓ answered",
    "… en cours": "… running",
    "Retirées de la file et bloquées au prochain scan. Le motif sert à corriger la notation.": "Removed from the queue and blocked at the next scan. The reason helps correct the scoring.",
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
    "site), {e} hors zone, {f} écartées à la main, {g} déjà rejetées par le tri, {h} "
    "pays écartés, {i} bruits purgés — {j} total": "Merge {a}: +{b} new, {c} enriched "
    "(desc), {d} links promoted (LinkedIn -> real site), {e} outside the area, {f} set aside "
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
