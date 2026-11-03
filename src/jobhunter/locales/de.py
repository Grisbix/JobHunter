"""German interface texts, indexed by the displayed French text.

Shared by both windows since 3.29 (it was jobhunter.app.texts_de). A text missing from
here is displayed in English, then in French. The keys are those of `en.TEXTES`,
`JOURNAL` and `SORTIE`.
"""

NOM = "Deutsch"
RELANCER = "Starte JobHunter neu, um die deutsche Oberfläche zu nutzen."

TEXTES: dict[str, str] = {
    # 3.15: indicators, history, kept posting, answers
    "offres en file": "Angebote in der Liste",
    "candidatures envoyées": "gesendete Bewerbungen",
    "▶ Candidatures envoyées": "▶ Gesendete Bewerbungen",
    "entretiens": "Gespräche",
    "sans réponse depuis 30 jours": "seit 30 Tagen ohne Antwort",
    "sur {n} réponse(s) datée(s)": "aus {n} datierten Antwort(en)",
    "{r} réponse(s), {e} entretien(s) · {p}": "{r} Antwort(en), {e} Gespräch(e) · {p}",
    # navigation and header
    "JOBHUNTER": "JOBHUNTER",
    "Mes CV": "Meine Lebensläufe",
    "Entreprises": "Unternehmen",
    "Accès": "Zugang",
    "ACTIONS": "AKTIONEN",
    "Actualiser les offres": "Angebote aktualisieren",
    "↶ Retour": "↶ Zurück",
    "Retour": "Zurück",
    # offers table
    "Chercher": "Suchen",
    "Postuler": "Bewerben",
    "Suivi et note ▸": "Status und Notiz ▸",
    "Fit": "Fit",
    "Lien": "Link",
    "Note": "Notiz",
    "Garder": "Behalten",
    "Exclure": "Ausschließen",
    "Tout": "Alle",
    # card and tracking
    "Envoi confirmé": "Versand bestätigt",
    # base CV (drag-and-drop, CV panel)
    "Remplacer mon CV de base…": "Meinen Basis-Lebenslauf ersetzen…",
    "Choisis ton nouveau CV de base": "Wähle deinen neuen Basis-Lebenslauf",
    # offer card: provenance and changes, queue watched
    "Canal": "Kanal",
    "Action": "Aktion",
    "État lien": "Linkstatus",
    "Pourquoi": "Warum",
    "Process": "Ablauf",
    "URL": "URL",
    "Aussi à": "Auch in",
    "Dossier à revoir": "Unterlagen prüfen",
    "collecte {a}": "Sammlung {a}",
    "poste": "Titel",
    "salaire": "Gehalt",
    "contrat": "Vertrag",
    "localisation": "Ort",
    "Appels d'API aujourd'hui (tous profils) : ": "API-Aufrufe heute (alle Profile): ",
    "{nom} : connexion vérifiée, la clé fonctionne.": "{nom}: Verbindung geprüft, der Schlüssel funktioniert.",
    "{nom} : aucune clé enregistrée (Saisir la clé).": "{nom}: kein Schlüssel gespeichert (Schlüssel eingeben).",
    "{nom} : clé refusée par le service — vérifie-la ou crée-en une nouvelle.": "{nom}: Schlüssel vom Dienst abgelehnt — prüfe ihn oder erstelle einen neuen.",
    "{nom} : quota atteint — la clé est bonne, réessaie demain.": "{nom}: Kontingent erreicht — der Schlüssel ist gültig, versuche es morgen erneut.",
    "{nom} : le service répond mais en erreur — réessaie plus tard.": "{nom}: der Dienst antwortet mit einem Fehler — versuche es später erneut.",
    "{nom} : pas de réponse (hors ligne ?).": "{nom}: keine Antwort (offline?).",
    "description": "Beschreibung",
    "re-score": "Neubewertung",
    "Mots-clés de recherche": "Suchbegriffe",
    "Intitulés à garder": "Behaltene Titel",
    "Rien n'est enregistré :": "Nichts wurde gespeichert:",
    "Suggestions depuis mon CV…": "Vorschläge aus meinem Lebenslauf…",
    "Annuler les modifications": "Änderungen verwerfen",
    "Suggestions depuis ton CV": "Vorschläge aus deinem Lebenslauf",
    "Compétence": "Kompetenz",
    # profiles
    "Renommer « {nom} »…": "„{nom}“ umbenennen…",
    "Archiver ce profil ? Son dossier est rangé dans profiles/_archives (rien n'est supprimé) et JobHunter redémarre sur le profil principal.": "Dieses Profil archivieren? Sein Ordner wird nach profiles/_archives verschoben (nichts wird gelöscht) und JobHunter startet mit dem Hauptprofil neu.",
    "Une collecte tourne pour ce profil : réessaie quand elle aura fini.": "Für dieses Profil läuft eine Sammlung: versuche es erneut, wenn sie fertig ist.",
    "Profils…": "Profile…",
    "Recettes de nettoyage…": "Bereinigungsregeln…",
    "Recettes de nettoyage": "Bereinigungsregeln",
    "Lancer la collecte du matin": "Morgensammlung starten",
    "Collecte du matin : {a} ✓": "Morgensammlung: {a} ✓",
    " · en erreur : {a}": " · mit Fehler: {a}",
    "Collecte en cours depuis {a}": "Sammlung läuft seit {a}",
    "Collecte interrompue ({a}) — {b}": "Sammlung unterbrochen ({a}) — {b}",
    "Collecte arrêtée ({a} : {b}) — {c}": "Sammlung abgebrochen ({a}: {b}) — {c}",
    "Aucune collecte du matin enregistrée": "Keine Morgensammlung erfasst",
    "Pas de collecte depuis {a}": "Keine Sammlung seit {a}",
    "dernière réussie : {a}": "letzte erfolgreiche: {a}",
    "aucune réussie": "keine erfolgreiche",
    "aujourd'hui {a}": "heute {a}",
    "hier {a}": "gestern {a}",
    "Enregistrer la vue actuelle…": "Aktuelle Ansicht speichern…",
    "Supprimer la vue « {a} » ?": "Ansicht „{a}“ löschen?",
    "Enregistrer les changements de « {a} » ?": "Änderungen an „{a}“ speichern?",
    "ouvert dans Word": "in Word geöffnet",
    "Une règle par ligne : champ | valeur à remplacer | nouvelle valeur. Une valeur doit correspondre au champ entier (majuscules et espaces ignorés) ; « re: » introduit un motif. Rejouer les mêmes recettes ne change rien la deuxième fois. Une offre à laquelle tu as postulé n'est jamais renommée.": "Eine Regel pro Zeile: Feld | zu ersetzender Wert | neuer Wert. Ein Wert muss dem ganzen Feld entsprechen (Groß-/Kleinschreibung und Leerzeichen egal); „re:“ leitet ein Muster ein. Dieselben Regeln erneut anzuwenden ändert beim zweiten Mal nichts. Ein Angebot, auf das du dich beworben hast, wird nie umbenannt.",
    "Champ": "Feld",
    "Avant": "Vorher",
    "Après": "Nachher",
    "Remarque": "Hinweis",
    "candidature : gardé": "beworben: behalten",
    "doublon : gardé": "Duplikat: behalten",
    "{a} changement(s), {b} écarté(s). Rien n'est écrit.": "{a} Änderung(en), {b} übersprungen. Nichts wird geschrieben.",
    "Recettes enregistrées : rien à changer dans la file.": "Regeln gespeichert: nichts in der Liste zu ändern.",
    "Enregistrer et appliquer": "Speichern und anwenden",
    "entreprise": "Unternehmen",
    "Documents à comparer…": "Dokumente vergleichen…",
    "Documents à comparer": "Dokumente vergleichen",
    "Tu as retouché ces documents à la main ; une version plus récente a été générée à côté. Rouge : seulement dans ta version. Vert : seulement dans la nouvelle. La version que tu ne gardes pas est mise de côté dans _a_comparer/_anciennes/, jamais supprimée.": "Du hast diese Dokumente von Hand bearbeitet; daneben wurde eine neuere Version erzeugt. Rot: nur in deiner Version. Grün: nur in der neuen. Die nicht behaltene Version wird in _a_comparer/_anciennes/ abgelegt, nie gelöscht.",
    "Aucun document en attente de comparaison.": "Kein Dokument wartet auf einen Vergleich.",
    "Lecture impossible : {a}": "Nicht lesbar: {a}",
    "Impossible pour l'instant ({a}) : le document est-il ouvert dans Word ?": "Im Moment nicht möglich ({a}): Ist das Dokument in Word geöffnet?",
    "Version mise de côté : {a}": "Version abgelegt: {a}",
    "Prendre la nouvelle version": "Neue Version übernehmen",
    "Garder ma version": "Meine Version behalten",
    "Dernière collecte": "Letzte Sammlung",
    "suspendue": "pausiert",
    "Un site lu par le navigateur ne se suspend pas : retire-le.": "Eine vom Browser gelesene Seite lässt sich nicht pausieren: entferne sie.",
    "⏸ {a} suspendue": "⏸ {a} pausiert",
    "▶ {a} reprise": "▶ {a} fortgesetzt",
    "Principal": "Haupt",
    "Nouveau profil depuis ce CV": "Neues Profil aus diesem Lebenslauf",
    "Nouveau profil « {nom} » : vérifie et complète ce que JobHunter a lu dans le CV.": "Neues Profil „{nom}“: Prüfe und ergänze, was JobHunter im Lebenslauf gelesen hat.",
    "Une tâche tourne sur ce profil : attends qu'elle finisse (ou « Arrêter »), puis change de profil.": "Auf diesem Profil läuft eine Aufgabe: warte, bis sie fertig ist (oder „Stoppen“), dann wechsle das Profil.",
    "Le profil n'a pas été créé (les questions n'ont pas été terminées).": "Das Profil wurde nicht erstellt (die Fragen wurden nicht beendet).",
    "Profil créé. L'ouvrir maintenant ? (JobHunter redémarre)": "Profil erstellt. Jetzt öffnen? (JobHunter startet neu)",
    "Voir CV": "Lebenslauf ansehen",
    "Voir lettre": "Anschreiben ansehen",
    "Description": "Beschreibung",
    "CV": "Lebenslauf",
    "ou une autre raison :": "oder ein anderer Grund:",
    # application
    "Ouverture de Chrome…": "Chrome wird geöffnet…",
    # Mes CV
    "Chercher une offre (entreprise, poste)": "Angebot suchen (Unternehmen, Stelle)",
    "↑ Haut": "↑ Oben",
    "↓ Bas": "↓ Unten",
    # Access
    "Rafraîchir": "Aktualisieren",
    "Connexions pour candidater": "Anmeldungen für Bewerbungen",
    "État de la dernière collecte de chaque source. Un refus n'est pas "
    "réessayé avant 30 jours. Double-clic sur une source à clé : saisir sa clé.": "Stand der "
    "letzten Sammlung jeder Quelle. Eine Ablehnung wird 30 Tage lang nicht erneut versucht. "
    "Doppelklick auf eine Quelle mit Schlüssel: Schlüssel eingeben.",
    "Saisir la clé": "Schlüssel eingeben",
    "saisis d'abord sa clé.": "gib zuerst ihren Schlüssel ein.",
    "Tu te connectes toi-même ; les mots de passe restent dans Chrome.": "Du meldest dich "
    "selbst an; die Passwörter bleiben in Chrome.",
    "Clé": "Schlüssel",
    "Une clé est déjà posée : un champ laissé vide la garde.": "Ein Schlüssel ist bereits "
    "gesetzt: ein leeres Feld behält ihn.",
    "Afficher la saisie": "Eingabe anzeigen",
    "Obtenir une clé": "Schlüssel beantragen",
    "Filtrer : entreprise, outil ou adresse": "Filtern: Unternehmen, Werkzeug oder Adresse",
    "Adresse de sa page carrière, ou nom de l'entreprise (annuaire)": "Adresse der "
    "Karriereseite oder Name des Unternehmens (Verzeichnis)",
    "Entreprises de mes offres : flux publics": "Firmen meiner Angebote: öffentliche Feeds",
    "Annuaire": "Verzeichnis",
    "Annuaire des entreprises": "Unternehmensverzeichnis",
    "3 600 entreprises lues par l'API publique de Lever, Ashby ou Greenhouse. "
    "Double-clic ou Entrée : suivre.": "3.600 Unternehmen, gelesen über die öffentliche API "
    "von Lever, Ashby oder Greenhouse. Doppelklick oder Eingabe: folgen.",
    "Identifiant": "Kennung",
    "Outil": "Werkzeug",
    "Ouvrir la connexion": "Anmeldeseite öffnen",
    "Vérifier les sessions": "Sitzungen prüfen",
    "Dernier état": "Letzter Stand",
    "Collecte du": "Gesammelt am",
    "Site": "Website",
    "Session": "Sitzung",
    "Vérifiée le": "Geprüft am",
    "Flux ATS des entreprises (Greenhouse, Lever, Ashby…)": "ATS-Feeds der Unternehmen "
    "(Greenhouse, Lever, Ashby…)",
    "Flux Workday des entreprises": "Workday-Feeds der Unternehmen",
    "LinkedIn — pages publiques, sans connexion": "LinkedIn — öffentliche Seiten, ohne Anmeldung",
    "EURES (offres européennes)": "EURES (europäische Angebote)",
    "FIR (finance responsable)": "FIR (nachhaltige Finanzen)",
    "France Travail — API officielle": "France Travail — offizielle API",
    "Adzuna — API officielle": "Adzuna — offizielle API",
    "Jooble — API officielle": "Jooble — offizielle API",
    # Entreprises
    "Chaque entreprise est lue par son outil de recrutement (API publique) "
    "ou, à défaut, par son site carrière. Double-clic : ouvrir sa page. "
    "Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres ».": "Jedes "
    "Unternehmen wird über sein Recruiting-Tool (öffentliche API) gelesen, sonst über seine "
    "Karriereseite. Doppelklick: Seite öffnen. Allgemeine Jobbörsen (LinkedIn, WTJ…) stehen "
    "unter „Jobbörsen“.",
    "Lue par": "Gelesen über",
    "Dernière": "Neueste",
    "Page": "Seite",
    "Ne plus suivre": "Nicht mehr folgen",
    "Lire les sites carrière": "Karriereseiten lesen",
    # Job sites
    "Ajouter": "Hinzufügen",
    # Statistiques
    "Liens OK": "Funktionierende Links",
    "Nb": "Anzahl",
    # Maintenance menus and steps
    "Scrape les sites": "Websites auslesen",
    "Rattrapage 31 j": "31 Tage nachholen",
    "Sonder flux ATS": "ATS-Feeds prüfen",
    "Sonder flux Workday": "Workday-Feeds prüfen",
    "Sonder mots-clés": "Suchbegriffe prüfen",
    "Sync docs+format": "Dokumente + Format abgleichen",
    "Export CSV": "CSV-Export",
    "Relire les lettres": "Anschreiben prüfen",
    "Pourquoi ce fit": "Warum dieser Fit",
    "Contrôler les dossiers": "Bewerbungsunterlagen prüfen",
    "URLs mortes": "Tote URLs",
    "Recheck 404": "404 erneut prüfen",
    "Re-score": "Neu bewerten",
    "Alerte matchs": "Treffer-Alarm",
    "Clés France Travail": "France-Travail-Schlüssel",
    "Fermer Chrome": "Chrome schließen",
    "Tester accès aux sites": "Zugang zu Websites testen",
    "Tests live (lent, ouvre un navigateur)": "Live-Tests (langsam, öffnet einen Browser)",
    "Sources & offres": "Quellen & Angebote",
    "Hygiène de la file": "Pflege der Liste",
    "Accès & diagnostic": "Zugang & Diagnose",
    "CV/lettres…": "Lebensläufe/Anschreiben…",
    "Homepages": "Homepages",
    "Statuts depuis mes courriels…": "Status aus meinen E-Mails…",
    "Statuts depuis mes courriels": "Status aus meinen E-Mails",
    "Lecture seule : les courriels sont lus et classés (refus, entretien, accusé de "
    "réception), jamais modifiés. Chaque statut proposé attend ton accord.": "Nur lesend: "
    "E-Mails werden gelesen und eingeordnet (Absage, Gespräch, Eingangsbestätigung), nie "
    "verändert. Jeder vorgeschlagene Status wartet auf deine Zustimmung.",
    "Candidature": "Bewerbung",
    "{a} courriel(s) lus, {b} statut(s) à proposer.": "{a} E-Mail(s) gelesen, {b} "
    "Status-Vorschlag/-Vorschläge.",
    "Lecture des courriels…": "E-Mails werden gelesen…",
    'Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".': "Gmail lesen: "
    'zuerst pip install "jobhunter[gmail]" ausführen.',
    "Fichier .mbox": ".mbox-Datei",
    "Fichier .mbox…": ".mbox-Datei…",
    "Dossier .eml…": ".eml-Ordner…",
    "Gmail (lecture seule)": "Gmail (nur lesend)",
    "Ignorer": "Ignorieren",
    "La collecte quotidienne est déjà planifiée. La retirer ?": "Die tägliche Sammlung ist "
    "bereits geplant. Entfernen?",
    "Candidatures en lot": "Sammelbewerbungen",
    "LinkedIn": "LinkedIn",
    # panel cells
    "libre": "frei",
    "clé": "Schlüssel",
    "pas encore mesurée": "noch nicht gemessen",
    "clé à créer": "Schlüssel anzulegen",
    "clé refusée": "Schlüssel abgelehnt",
    "vérifie-la": "prüfe ihn",
    "ok": "ok",
    "refusé": "abgelehnt",
    "limité": "gedrosselt",
    "partiel": "teilweise",
    "rien à prendre": "nichts Neues",
    "site (navigateur)": "Website (Browser)",
    "plan du site": "Sitemap",
    "CV de base": "Basis-Lebensläufe",
    "prêts": "fertig",
    "PDF à refaire": "PDF neu erstellen",
    "incomplet": "unvollständig",
    # Dialog boxes
    "Confirmer l'envoi": "Versand bestätigen",
    "As-tu envoyé cette candidature ?": "Hast du diese Bewerbung abgeschickt?",
    "Supprimer {n} offre(s) cochée(s) de la liste ?\n\n"
    "Une copie est gardée dans Scripts/_corbeille/ — rien n'est perdu.\n"
    "Pour qu'elles ne reviennent pas au prochain scan, préfère\n"
    "« Écarter » : le motif est retenu.": "{n} markierte(s) Angebot(e) aus der Liste löschen?\n\n"
    "Eine Kopie bleibt in Scripts/_corbeille/ — nichts geht verloren.\n"
    "Damit sie beim nächsten Scan nicht zurückkommen, nimm lieber\n"
    "„Aussortieren“: der Grund wird gespeichert.",
    "JobHunter — mise à jour": "JobHunter — Aktualisierung",
    "La mise à jour n'a pas abouti ; le détail est dans "
    "le journal. Tes données n'ont pas été touchées.": "Die Aktualisierung ist nicht "
    "abgeschlossen; Details stehen im Protokoll. Deine Daten wurden nicht angerührt.",
    "Version installée : {installee}": "Installierte Version: {installee}",
    "JobHunter — mise à jour disponible": "JobHunter — Aktualisierung verfügbar",
    "La version {v} est disponible (installée : {installee}).\n\n"
    "L'installer maintenant ? Ton profil, ton CV, tes lettres et ton suivi ne "
    "sont pas touchés, et la version d'avant est sauvegardée.": "Version {v} ist verfügbar "
    "(installiert: {installee}).\n\nJetzt installieren? Dein Profil, Lebenslauf, Anschreiben "
    "und deine Statusliste bleiben unberührt, und die vorige Version wird gesichert.",
    "pas avant le": "nicht vor dem",
    "offres": "Angebote",
    "offre": "Angebot",
    # offer list (counts and placeholders)
    "Sélectionne une offre dans le tableau.": "Wähle ein Angebot in der Tabelle.",
    "aucune offre ne passe les filtres — clique sur ▾ dans une entete pour les lever": "kein Angebot passt zu den Filtern — klicke ▾ in einer Kopfzeile, um sie aufzuheben",
    "aucune offre pour l'instant : clique « Actualiser les offres » à gauche": "noch keine Angebote: links auf « Angebote aktualisieren » klicken",
    "sur {base}": "von {base}",
    "{n} offre(s)": "{n} Angebot(e)",
    # 3.18: the Profil panel (profiles, fit weights, skills)
    "Poids des axes": "Gewichtung der Achsen",
    "Combien compte chaque axe du profil quand l'annonce cite ses compétences.": "Wie stark jede Achse des Profils zählt, wenn die Anzeige ihre Kompetenzen nennt.",
    "Score qui vaut 10": "Punktzahl für 10",
    "La somme pondérée des axes qui donne 10. Plus bas : les notes montent.": "Die gewichtete Summe der Achsen, die 10 ergibt. Niedriger: die Noten steigen.",
    "Intitulé": "Titel",
    "Ajouté ou retiré selon les mots du titre de l'offre.": "Je nach den Wörtern im Titel der Stelle addiert oder abgezogen.",
    "Relire la file": "Liste neu lesen",
    "Expérience demandée": "Verlangte Erfahrung",
    "Retiré quand l'annonce demande au moins ce nombre d'années.": "Abgezogen, wenn die Anzeige mindestens so viele Jahre verlangt.",
    "Recalculer maintenant le fit enregistré de chaque offre de ta file ? Le tableau et le tri l'utilisent.": "Den gespeicherten Fit jeder Stelle deiner Liste jetzt neu berechnen? Tabelle und Sortierung verwenden ihn.",
    "Lecture des offres de ta file… (une trentaine de secondes)": "Die Stellen deiner Liste werden gelesen… (etwa dreißig Sekunden)",
    "Aucune offre choisie": "Keine Stelle gewählt",
    "Rien à enregistrer : les poids sont ceux du profil.": "Nichts zu speichern: die Gewichte sind die des Profils.",
    "Lecture impossible": "Lesen unmöglich",
    "profil actif": "aktives Profil",
    "profil principal": "Hauptprofil",
    "Compte pour les axes": "Zählt für die Achsen",
    "Nouvelle": "Neu",
    "Compétences enregistrées (profil d'avant : {bak}).": "Kompetenzen gespeichert (vorheriges Profil: {bak}).",
    "Un profil = une recherche complète : sa file d'offres, ses candidatures, ses CV et lettres, ses réglages. Ouvrir un autre profil redémarre JobHunter dessus ; un profil archivé est rangé, jamais supprimé.": "Ein Profil = eine vollständige Suche: seine Stellenliste, seine Bewerbungen, seine Lebensläufe und Briefe, seine Einstellungen. Ein anderes Profil öffnen startet JobHunter darauf neu; ein archiviertes Profil wird weggelegt, nie gelöscht.",
    "Nouveau profil : choisis le CV (.docx ou .pdf) dont il partira": "Neues Profil: wähle den Lebenslauf (.docx oder .pdf), von dem es ausgeht",
    "Donne un nom à la compétence.": "Gib der Kompetenz einen Namen.",
    "Rien à enregistrer.": "Nichts zu speichern.",
    "{n} compétences dans le profil actif.": "{n} Kompetenzen im aktiven Profil.",
    # 3.19: statuses, contracts, statistics, settings
    "à postuler": "zu bewerben",
    "postulé": "beworben",
    "relancé": "nachgefasst",
    "entretien": "Vorstellungsgespräch",
    "refus": "Absage",
    "mauvaise": "unpassend",
    "expiré": "abgelaufen",
    "CDI": "Unbefristet",
    "CDD": "Befristet",
    "Interim": "Zeitarbeit",
    "Freelance": "Freiberuflich",
    "V.I.E": "V.I.E",
    "Bénévolat": "Ehrenamt",
    "Saisonnier": "Saisonarbeit",
    "Temps partiel": "Teilzeit",
    "Ne plus suivre « {nom} » ? Son adresse de flux sera retirée ; « Suspendre / Reprendre » la garde.": "„{nom}“ nicht mehr verfolgen? Die Feed-Adresse wird entfernt; „Pausieren / Fortsetzen“ behält sie.",
    # Statistics: the default domain and the channel values.
    "Autre": "Sonstiges",
    "manuel": "manuell",
    "auto": "automatisch",
    "le {d}": "am {d}",
    "{n} j": "{n} T",
    "▶ Sur les offres à fit ≥ 8": "▶ Stellen mit Fit ≥ 8",
    "{n} muette(s) depuis {j} j": "{n} still seit {j} T",
    "Paramètres": "Einstellungen",
    "Langue de l'interface": "Sprache der Oberfläche",
    "Version": "Version",
    "Vérifier les mises à jour": "Nach Updates suchen",
    # 3.19.1: the ⚙ menu
    "Vérifier les offres en ligne": "Stellen noch online?",
    # 3.19.1: the ⚑ column explained
    "⚑ Alerte — vide quand tout va bien": "⚑ Warnung — leer, wenn alles passt",
    "⚠ condition éliminatoire (permis, nationalité, droit de travail, habilitation)": "⚠ Ausschlusskriterium (Führerschein, Staatsangehörigkeit, Arbeitserlaubnis, Sicherheitsfreigabe)",
    # 3.20.0: progress, the ☰ button, the Outils menu, the daily collection in Paramètres
    "Collecte automatique": "Automatische Sammlung",
    "Chaque jour à l'heure choisie, l'ordinateur collecte les offres de tous tes profils, même si JobHunter est fermé.": "Jeden Tag zur gewählten Uhrzeit sammelt der Computer die Angebote aller deiner Profile, auch wenn JobHunter geschlossen ist.",
    "Pas planifiée.": "Nicht geplant.",
    "☰ Menu": "☰ Menü",
    "{a}/{b} sources": "{a}/{b} Quellen",
    "~{d} restantes": "noch ~{d}",
    "Vérification {a}/{b}": "Prüfung {a}/{b}",
    "Vérification des offres": "Angebotsprüfung",
    # 3.21.0: places in « Ma recherche »
    "Où tu veux travailler": "Wo du arbeiten willst",
    "Zones des offres mises à jour": "Zonen der Angebote aktualisiert",
    # 3.26: progress legend
    "✓ a répondu": "✓ hat geantwortet",
    "… en cours": "… läuft",
    "Retirées de la file et bloquées au prochain scan. Le motif sert à corriger la notation.": "Aus der Liste entfernt und beim nächsten Scan gesperrt. Der Grund hilft, die Bewertung zu korrigieren.",
}


# App log (langue.journal): a displayed line → its translation; `{a}` keeps the
# variable part of the line as is.
JOURNAL = {
    # ── lignes fixes ──
    "Sélectionne d'abord une offre.": "Wähle zuerst ein Angebot.",
    "Coche d'abord des offres (colonne ☐).": "Markiere zuerst Angebote (Spalte ☐).",
    "✗ un autre programme écrit suivi.json — réessaie dans un instant.": "✗ ein anderes "
    "Programm schreibt suivi.json — versuche es gleich nochmal.",
    "Rien à annuler.": "Nichts rückgängig zu machen.",
    "⏳ suivi.json occupé par un autre programme — réessaie dans un instant.": "⏳ suivi.json "
    "wird von einem anderen Programm benutzt — versuche es gleich nochmal.",
    "✗ un autre programme modifie la file — réessaie dans un instant.": "✗ ein anderes "
    "Programm ändert die Liste — versuche es gleich nochmal.",
    "Bilan de ce que la notation rate : python JobHunter.pyw exclusions": "Was die Bewertung "
    "verfehlt: python JobHunter.pyw exclusions",
    "Le panneau Candidatures est déjà ouvert.": "Das Bewerbungsfenster ist bereits offen.",
    "✗ édition réservée aux lettres/.txt — CV : 📂 Ouvrir (Word)": "✗ Bearbeiten nur für "
    "Anschreiben/.txt — Lebenslauf: 📂 Öffnen (Word)",
    "Sélectionne d'abord un dossier d'offre dans la liste.": "Wähle zuerst den Ordner eines "
    "Angebots in der Liste.",
    "✗ édition intégrée réservée aux lettres/.txt — CV .docx : bouton 📂 Ouvrir (Word)": "✗ "
    "eingebautes Bearbeiten nur für Anschreiben/.txt — Lebenslauf .docx: Knopf 📂 Öffnen (Word)",
    "⏳ tâche en cours.": "⏳ eine Aufgabe läuft.",
    "⏳ un travail de fond écrit la file (descriptions ou sync docs).": "⏳ ein Hintergrundjob "
    "schreibt die Liste (Beschreibungen oder Dokumentabgleich).",
    "Réessaie dans un instant — il se termine tout seul.": "Versuche es gleich nochmal — er "
    "endet von selbst.",
    "▶ TOUT FAIRE — pipeline complet (6 etapes)": "▶ ALLES ERLEDIGEN — kompletter Ablauf "
    "(6 Schritte)",
    "⏳ Mise à jour : elle démarre dès que le travail en cours est fini.": "⏳ Aktualisierung: "
    "sie startet, sobald die laufende Arbeit fertig ist.",
    "▶ Mise à jour de JobHunter": "▶ JobHunter wird aktualisiert",
    "✅ TOUT FAIRE terminé.": "✅ ALLES ERLEDIGEN abgeschlossen.",
    "(aucune tache en cours)": "(keine Aufgabe läuft)",
    "trace complète : Scripts/_logs/app_erreurs.log": "vollständiges Protokoll: "
    "Scripts/_logs/app_erreurs.log",
    "Retour : aucune disposition à rétablir.": "Zurück: keine Ansicht wiederherzustellen.",
    "✗ pas d'URL http pour récupérer la description": "✗ keine http-URL, um die "
    "Beschreibung zu holen",
    "✅ description récupérée": "✅ Beschreibung geholt",
    "✗ description introuvable (page JS/mur login ?)": "✗ Beschreibung nicht gefunden "
    "(JS-Seite oder Login-Sperre?)",
    "(pas d'URL → pas de host)": "(keine URL → kein Host)",
    "Sélectionne d'abord une source dans la liste.": "Wähle zuerst eine Quelle in der Liste.",
    "Selectionne d'abord un site dans la liste.": "Wähle zuerst eine Website in der Liste.",
    "↪ c'est un site d'offres général → ajoute-le dans « Sites d'offres »": "↪ das ist eine "
    "allgemeine Jobbörse → füge sie unter „Jobbörsen“ hinzu",
    "déjà suivi": "bereits gefolgt",
    "Sélectionne d'abord une entreprise dans la liste.": "Wähle zuerst ein Unternehmen in "
    "der Liste.",
    "✗ colle une URL http d'offre.": "✗ füge eine http-URL eines Angebots ein.",
    # ── templates ──
    "📌 statut: {a} → {b}": "📌 Status: {a} → {b}",
    "! écriture suivi.json KO: {a}": "! suivi.json schreiben fehlgeschlagen: {a}",
    "⊖ {a} offre(s) « pas intéressé » — masquées, Ctrl+Z pour annuler.": "⊖ {a} Angebot(e) "
    "„kein Interesse“ — ausgeblendet, Strg+Z zum Rückgängigmachen.",
    "✗ annulation impossible pour l'instant ({a}) — réessaie.": "✗ Rückgängig gerade nicht "
    "möglich ({a}) — versuche es nochmal.",
    "↶ annulé ({a} offre(s)).": "↶ rückgängig gemacht ({a} Angebot(e)).",
    "! écriture sélection KO: {a}": "! Auswahl schreiben fehlgeschlagen: {a}",
    "ATTENTION : {a}, pas l'offre elle-meme{b}.": "ACHTUNG: {a}, nicht das Angebot selbst{b}.",
    "🔍 recherche web: {a}": "🔍 Websuche: {a}",
    "! exclusions.py introuvable: {a}": "! exclusions.py nicht gefunden: {a}",
    "! écriture queue KO: {a}": "! Liste schreiben fehlgeschlagen: {a}",
    "✕ {a} offre(s) écartée(s) — « {b} ». {c} nouvelle(s) exclusion(s) ; elles ne "
    "reviendront pas au scan.": "✕ {a} Angebot(e) aussortiert — „{b}“. {c} neue(r) "
    "Ausschluss/Ausschlüsse; sie kommen beim Scan nicht zurück.",
    "! copie de sauvegarde KO ({a}) — suppression ANNULÉE.": "! Sicherungskopie fehlgeschlagen "
    "({a}) — Löschen ABGEBROCHEN.",
    "🗑 {a} offre(s) supprimée(s) — copie dans Scripts/_corbeille/{b}": "🗑 {a} Angebot(e) "
    "gelöscht — Kopie in Scripts/_corbeille/{b}",
    "📮 Candidatures : {a} offre(s), panneau ouvert. Chrome s'ouvre.": "📮 Bewerbungen: {a} "
    "Angebot(e), Fenster offen. Chrome wird geöffnet.",
    "💾 enregistré : {a}": "💾 gespeichert: {a}",
    "! sauvegarde KO: {a}": "! Speichern fehlgeschlagen: {a}",
    "📄 PDF resynchronisé : {a}": "📄 PDF neu abgeglichen: {a}",
    "✗ {a} : pièce manquante ({b})": "✗ {a}: fehlendes Dokument ({b})",
    "ℹ {a} description(s) manquante(s) — récupération auto en fond…": "ℹ {a} fehlende "
    "Beschreibung(en) — werden automatisch im Hintergrund geholt…",
    "✅ descriptions: +{a} récupérées ({b} restantes, dont Indeed/anti-bot).": "✅ "
    "Beschreibungen: +{a} geholt ({b} übrig, inkl. Indeed/Anti-Bot).",
    "🔁 sync docs : {a}": "🔁 Dokumentabgleich: {a}",
    "🔎 scan auto : +{a} offre(s). {b}": "🔎 automatischer Scan: +{a} Angebot(e). {b}",
    "🔎 scan auto : {a}": "🔎 automatischer Scan: {a}",
    "📧 brouillon relance ouvert ({a}) — envoie-le puis passe le statut à « relancé ».": "📧 "
    "Nachfass-Entwurf geöffnet ({a}) — schick ihn ab und setze dann den Status auf „relancé“.",
    "▶ {a} — fenêtre CONSOLE ouverte. Chrome s'ouvre ; tape Entrée après chaque envoi. "
    "Ferme la console pour arrêter.": "▶ {a} — KONSOLEN-Fenster geöffnet. Chrome wird "
    "geöffnet; drücke nach jedem Absenden Eingabe. Schließe die Konsole zum Stoppen.",
    "! lancement console KO: {a}": "! Konsolenstart fehlgeschlagen: {a}",
    "⏹ arrete (arbre du PID {a}).": "⏹ gestoppt (Prozessbaum von PID {a}).",
    "! arret KO ({a}) — repli sur terminate": "! Stoppen fehlgeschlagen ({a}) — Ausweichen "
    "auf terminate",
    "! panne interne [{a}] — {b}": "! interner Fehler [{a}] — {b}",
    "✗ TOUT FAIRE interrompu à l'étape « {a} ».": "✗ ALLES ERLEDIGEN bei Schritt „{a}“ "
    "abgebrochen.",
    "－ compte retiré: {a}": "－ Konto entfernt: {a}",
    "Associer un compte ajouté: {a}": "Kontoverknüpfung hinzugefügt: {a}",
    "! écriture comptes_sites.json KO: {a}": "! comptes_sites.json schreiben fehlgeschlagen: {a}",
    "💾 suivi enregistré: {a} → {b}": "💾 Status gespeichert: {a} → {b}",
    "＋ site carrière ajouté, lu par le navigateur : {a}": "＋ Karriereseite hinzugefügt, "
    "gelesen über den Browser: {a}",
    "✗ {a} : flux introuvable dans sources_config.json": "✗ {a}: Feed nicht in "
    "sources_config.json gefunden",
    "－ {a} ne sera plus collectée": "－ {a} wird nicht mehr gesammelt",
    "＋ ajouté : {a}": "＋ hinzugefügt: {a}",
    "－ retiré : {a}": "－ entfernt: {a}",
    "🔎 analyse de l'offre : {a}": "🔎 Angebot wird analysiert: {a}",
    "＋ flux {a} {b} — lu par API dès la prochaine collecte ({c})": "＋ {a}-Feed {b} — ab der "
    "nächsten Sammlung per API gelesen ({c})",
    "＋ flux {a} {b} — lu par API dès la prochaine collecte": "＋ {a}-Feed {b} — ab der "
    "nächsten Sammlung per API gelesen",
    "déjà suivi : {a} ({b})": "bereits gefolgt: {a} ({b})",
    "déjà suivi : {a}": "bereits gefolgt: {a}",
}

# The output of the programs the app launches, translated line by line like JOURNAL.
SORTIE = {
    # Collecte (jobhunter.sources)
    "── recherche restreinte à la FRANCE ──": "── Suche auf FRANKREICH beschränkt ──",
    "── ATS APIs (greenhouse/lever/ashby/recruitee/smartrecruiters) ──": "── ATS-APIs "
    "(greenhouse/lever/ashby/recruitee/smartrecruiters) ──",
    "── Workday (API publique des grands groupes) ──": "── Workday (öffentliche API großer "
    "Konzerne) ──",
    "── LinkedIn recherche publique (guest) ──": "── LinkedIn öffentliche Suche (Gast) ──",
    "── V.I.E / V.I.A (Business France) ──": "── V.I.E / V.I.A (Business France) ──",
    "── FIR / French SIF (100 % ISR-ESG) ──": "── FIR / French SIF (100 % SRI-ESG) ──",
    "── Talent.com (agrégateur) ──": "── Talent.com (Aggregator) ──",
    "── Indeed (page 1 des résultats — voir le commentaire de scan_indeed) ──": "── Indeed "
    "(Ergebnisseite 1 — siehe Kommentar von scan_indeed) ──",
    "── APEC (API publique, annonce entière dans la liste) ──": "── APEC (öffentliche API, "
    "ganze Anzeige in der Liste) ──",
    "── Glassdoor (page 1 de la recherche, France entière) ──": "── Glassdoor (Suchseite 1, "
    "ganz Frankreich) ──",
    "── eFinancialCareers ({a}, {b} site(s), sitemap public, crawl-delay 10 s) ──": "── "
    "eFinancialCareers ({a}, {b} Website(s), öffentliche Sitemap, Crawl-Delay 10 s) ──",
    "── EURES (portail officiel UE, API publique, crawl-delay 10 s) ──": "── EURES (offizielles "
    "EU-Portal, öffentliche API, Crawl-Delay 10 s) ──",
    "── France Travail (API officielle) ──": "── France Travail (offizielle API) ──",
    "── Adzuna (API officielle, France + 7 pays) ──": "── Adzuna (offizielle API, Frankreich "
    "+ 7 Länder) ──",
    "── Jooble (API officielle) ──": "── Jooble (offizielle API) ──",
    "── Welcome to the Jungle (sitemap public, débit bridé) ──": "── Welcome to the Jungle "
    "(öffentliche Sitemap, gedrosselt) ──",
    "Scan : {a} offres uniques (non ecrit : --dry)": "Scan: {a} eindeutige Angebote (nicht "
    "geschrieben: --dry)",
    "Scan : {a} offres uniques (→ {b})": "Scan: {a} eindeutige Angebote (→ {b})",
    "Refus rencontrés (une collecte vide peut venir de là) :": "Ablehnungen (eine leere "
    "Sammlung kann daher kommen):",
    "Rendement par source :": "Ertrag je Quelle:",
    "{a} ramenées · {b} nouvelles · {c} pertinentes · {d} s": "{a} geholt · {b} neu · {c} "
    "relevant · {d} s",
    "Merge {a}: +{b} nouvelles, {c} enrichies (desc), {d} liens promus (LinkedIn -> vrai "
    "site), {e} hors zone, {f} écartées à la main, {g} déjà rejetées par le tri, {h} "
    "pays écartés, {i} bruits purgés — {j} total": "Zusammenführung {a}: +{b} neu, {c} "
    "ergänzt (Beschr.), {d} Links hochgestuft (LinkedIn -> echte Seite), {e} außerhalb "
    "Frankreichs, {f} von Hand aussortiert, {g} schon vom Sortieren abgelehnt, {h} Länder "
    "ausgeschlossen, {i} Rauschen entfernt — {j} gesamt",
    "→ re-score + descriptions manquantes : automatiques au prochain lancement de l'app.": "→ "
    "Neubewertung + fehlende Beschreibungen: automatisch beim nächsten App-Start.",
    "Le scan est conserve dans {a} : `jobhunter collect --fusion-seule` le fusionnera.": "Der "
    "Scan bleibt in {a}: `jobhunter collect --fusion-seule` führt ihn zusammen.",
    "! journal de rendement non écrit : {a}": "! Ertragsprotokoll nicht geschrieben: {a}",
    # Descriptions (scrape_desc)
    "Rien à faire : --key ou --all requis.": "Nichts zu tun: --key oder --all nötig.",
    "Aucune offre ciblée.": "Kein Angebot ausgewählt.",
    "{a} offre(s) à récupérer…": "{a} Angebot(e) zu holen…",
    "── {a}/{b} — {c} ok — {d}s/offre, reste ~{e} min": "── {a}/{b} — {c} ok — "
    "{d}s/Angebot, noch ~{e} Min.",
    "=== {a}/{b} descriptions enregistrées (API) ===": "=== {a}/{b} Beschreibungen "
    "gespeichert (API) ===",
    "=== {a}/{b} descriptions enregistrées dans apply_queue.json ===": "=== {a}/{b} "
    "Beschreibungen in apply_queue.json gespeichert ===",
    "✅ {a} car. (via {b})": "✅ {a} Zeichen (über {b})",
    "✖ relance navigateur impossible : {a}": "✖ Browser-Neustart fehlgeschlagen: {a}",
    # Re-score (rescore_ats)
    "{a} ATS% + {b} fit re-scorés / {c}": "{a} ATS% + {b} Fit neu bewertet / {c}",
    "Offres exigeant ≥3 ans d'expérience (fit pénalisé) : {a}": "Angebote mit ≥3 Jahren "
    "Erfahrung (Fit abgewertet): {a}",
    "Distribution ATS% : {a}": "ATS%-Verteilung: {a}",
    # Liens morts (recheck_dead)
    "Aucune offre à revérifier (filtre trop strict ?).": "Kein Angebot erneut zu prüfen "
    "(Filter zu streng?).",
    "{a} offre(s) à revérifier en navigateur (status={b})…": "{a} Angebot(e) im Browser "
    "erneut zu prüfen (status={b})…",
    "✖ {a} échecs d'affilée — arrêt (relance plus tard, reprise auto)": "✖ {a} Fehlschläge "
    "in Folge — Stopp (später erneut starten, setzt automatisch fort)",
    "── checkpoint {a}/{b} — {c}s/lien, reste ~{d} min": "── Zwischenstand {a}/{b} — "
    "{c}s/Link, noch ~{d} Min.",
    "=== {a}changements: {b} ===": "=== {a}Änderungen: {b} ===",
    # Export (export_queue_csv)
    "! apply_queue.json introuvable": "! apply_queue.json nicht gefunden",
    "(suivi.json illisible : {a} — export sans le suivi)": "(suivi.json unlesbar: {a} — "
    "Export ohne Statusliste)",
    "=== {a} offres -> {b} ({c} Ko) ===": "=== {a} Angebote -> {b} ({c} KB) ===",
    "rotation : {a} supprimé": "Rotation: {a} gelöscht",
    # Alertes (notify_matches)
    "historique de notification remis à zéro": "Benachrichtigungsverlauf zurückgesetzt",
    "aucune NOUVELLE offre fit >= {a} (déjà notifiées : {b})": "kein NEUES Angebot mit Fit "
    ">= {a} (bereits gemeldet: {b})",
    "=== {a} nouvelle(s) offre(s) fit >= {b} ===": "=== {a} neue(s) Angebot(e) mit Fit >= {b} ===",
    "[dry] pas de notification, historique inchangé": "[dry] keine Benachrichtigung, Verlauf "
    "unverändert",
    "notifié — {a} marquée(s), historique {b}": "gemeldet — {a} markiert, Verlauf {b}",
    "non notifié (toast KO) — {a} marquée(s), historique {b}": "nicht gemeldet (Toast "
    "fehlgeschlagen) — {a} markiert, Verlauf {b}",
    "! toast échoué : {a}": "! Toast fehlgeschlagen: {a}",
    "! toast impossible : {a}": "! Toast nicht verfügbar: {a}",
    # Update (mise_a_jour)
    "Version installée : {a} · disponible : {b}": "Installierte Version: {a} · verfügbar: {b}",
    "Version installée : {a} · c'est la plus récente.": "Installierte Version: {a} · das ist "
    "die neueste.",
    "Téléchargement de {a} …": "{a} wird heruntergeladen …",
    "Signature de l'auteur vérifiée.": "Signatur des Autors geprüft.",
    "Signature de l'auteur vérifiée : {a} fichiers de la {b}.": "Signatur des Autors geprüft: "
    "{a} Dateien von {b}.",
    "(Version non signée : empreinte publiée vérifiée.)": "(Unsignierte Version: "
    "veröffentlichte Prüfsumme geprüft.)",
    "(Version {a} non signée : la clé de l'auteur n'est pas encore publiée.)": "(Version {a} "
    "unsigniert: der Schlüssel des Autors ist noch nicht veröffentlicht.)",
    "! Mise à jour refusée : {a}. Rien n'a été installé.": "! Aktualisierung abgelehnt: {a}. "
    "Nichts wurde installiert.",
    "! Mise à jour refusée : {a}. Rien n'a été modifié.": "! Aktualisierung abgelehnt: {a}. "
    "Nichts wurde geändert.",
    "! Téléchargement impossible ({a}) : la page des versions s'ouvre.": "! Download "
    "fehlgeschlagen ({a}): die Versionsseite öffnet sich.",
    "L'installateur s'ouvre : suis ses étapes. Tes données sont gardées.": "Das "
    "Installationsprogramm öffnet sich: folge seinen Schritten. Deine Daten bleiben erhalten.",
    # Collect every morning (planification)
    "Collecte planifiée chaque jour à {a}, si l'ordinateur est allumé. Journaux : {b}.": "Sammlung "
    "jeden Tag um {a} geplant, wenn der Computer an ist. Protokolle: {b}.",
    "Collecte quotidienne retirée.": "Tägliche Sammlung entfernt.",
    "La tâche n'a pas pu être créée : {a}": "Die Aufgabe konnte nicht erstellt werden: {a}",
    "La tâche n'a pas pu être retirée : {a}": "Die Aufgabe konnte nicht entfernt werden: {a}",
    "Heure invalide : « {a} » (format 08:00).": "Ungültige Uhrzeit: „{a}“ (Format 08:00).",
    "Hors Windows : lance ./launchers/schedule.sh depuis le dossier de JobHunter.": "Außerhalb von "
    "Windows: starte ./launchers/schedule.sh im JobHunter-Ordner.",
}

# The lines of the fit explanation (scoring.fit.expliquer): language.explication.
FIT = {
    "{axe} {pct} (x{poids}) : {mots}": "{axe} {pct} (x{poids}): {mots}",
    "vocabulaire : {v}/10": "Vokabular: {v}/10",
    "intitulé du métier visé en second (finance)": "Titel des zweiten Zielberufs (Finanzen)",
    "intitulé du cœur de cible : plafond 10": "Titel im Kern des Ziels: Obergrenze 10",
    "plafond {cap} (cœur {c}, complément {k})": "Obergrenze {cap} (Kern {c}, Ergänzung {k})",
    "intitulé HSE : plafond {cap}": "HSE-Titel: Obergrenze {cap}",
    "métier hors cible dans l'intitulé : plafond {cap}": "Beruf außerhalb des Ziels im Titel: Obergrenze {cap}",
    "intitulé junior « {mot} » : +{b}": "Junior-Titel „{mot}“: +{b}",
    "intitulé senior : -{m}": "Senior-Titel: -{m}",
    "intitulé écarté « {mot} » : -2": "ausgeschlossener Titel „{mot}“: -2",
    "annonce redigee en {lg} : plafond {p}": "Anzeige verfasst auf {lg}: Obergrenze {p}",
    "annonce exige {x} : plafond {p}": "Anzeige verlangt {x}: Obergrenze {p}",
    "{n} an(s) d'expérience demandés : -{m}": "{n} Jahr(e) Erfahrung verlangt: -{m}",
}
