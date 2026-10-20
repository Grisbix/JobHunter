"""Spanish interface texts, indexed by the displayed French text.

Part of jobhunter.app (see `langue`). A text missing from here is displayed in English,
then in French. The keys are those of `texts_en.TEXTES`, `JOURNAL` and `SORTIE`.
"""

NOM = "Español"
RELANCER = "Reinicia JobHunter para usar la interfaz en español."

TEXTES: dict[str, str] = {
    # navigation and header
    "JOBHUNTER": "JOBHUNTER",
    "RECHERCHE D'EMPLOI": "BÚSQUEDA DE EMPLEO",
    "Offres": "Ofertas",
    "Mes CV": "Mis CV",
    "Entreprises": "Empresas",
    "Sites d'offres": "Portales de empleo",
    "Statistiques": "Estadísticas",
    "Accès": "Acceso",
    "ACTIONS": "ACCIONES",
    "Actualiser les offres": "Actualizar ofertas",
    "Maintenance ▸": "Mantenimiento ▸",
    "Maintenance ▾": "Mantenimiento ▾",
    "Recharger": "Recargar",
    "Outils": "Herramientas",
    "↶ Retour": "↶ Volver",
    "Retour": "Volver",
    "Dossier": "Carpeta",
    "Arrêter": "Detener",
    "Langue / Language…": "Idioma / Language…",
    # offers table
    "OFFRES EN FILE": "OFERTAS EN LA LISTA",
    "FIT ≥ 8": "FIT ≥ 8",
    "CANDIDATURES ENVOYÉES": "CANDIDATURAS ENVIADAS",
    "Chercher": "Buscar",
    "Voir les masquées": "Ver ocultas",
    "Colonnes": "Columnas",
    "Postuler": "Postular",
    "Écarter…": "Descartar…",
    "Supprimer": "Eliminar",
    "Décocher": "Desmarcar",
    "En-tête : filtrer  ·  Double-clic : fiche": "Encabezado: filtrar  ·  Doble clic: ficha",
    "FICHE DE L’OFFRE": "FICHA DE LA OFERTA",
    "Agrandir": "Ampliar",
    "Suivi et note ▸": "Seguimiento y nota ▸",
    "Sélectionne une offre": "Selecciona una oferta",
    "Ajouter une offre": "Añadir una oferta",
    "Statut": "Estado",
    "Entreprise": "Empresa",
    "Poste": "Puesto",
    "Domaine": "Área",
    "Fit": "Fit",
    "Contrat": "Contrato",
    "Zone": "Zona",
    "Lieu": "Lugar",
    "Pays": "País",
    "Région": "Región",
    "Date offre": "Publicada",
    "Lien": "Enlace",
    "Suivi": "Seguimiento",
    "Date": "Fecha",
    "Note": "Nota",
    "▲  Croissant": "▲  Ascendente",
    "▼  Décroissant": "▼  Descendente",
    "double-clic = seulement celle-ci": "doble clic = solo esta",
    "Garder": "Mantener",
    "Exclure": "Excluir",
    "Tout": "Todo",
    # card and tracking
    "Envoi confirmé": "Envío confirmado",
    "Ouvrir l'offre": "Abrir la oferta",
    "Pas intéressé": "No me interesa",
    "Enregistrer": "Guardar",
    # base CV (drag-and-drop, CV panel)
    "Remplacer mon CV de base…": "Reemplazar mi CV base…",
    "Dépose un CV au format .docx ou .pdf.": "Suelta un CV en formato .docx o .pdf.",
    "Choisis ton nouveau CV de base": "Elige tu nuevo CV base",
    "Remplacer ton CV de base ({ancien}) par {cv} ? L'ancien est gardé à côté, en .bak.": "¿Reemplazar tu CV base ({ancien}) por {cv}? El anterior se guarda al lado, como .bak.",
    "CV de base remplacé : {nom}": "CV base reemplazado: {nom}",
    "CV de base remplacé. Refaire maintenant les CV déjà préparés pour les offres ?": "CV base reemplazado. ¿Rehacer ahora los CV ya preparados para las ofertas?",
    "Refaire les CV": "Rehacer los CV",
    # offer card: provenance and changes, queue watched
    "Canal": "Canal",
    "Action": "Acción",
    "Télétravail": "Teletrabajo",
    "Compétences": "Competencias",
    "Correspondance ATS": "Coincidencia ATS",
    "État lien": "Estado del enlace",
    "Salaire / Avantages": "Salario / Ventajas",
    "Profil requis": "Perfil requerido",
    "Missions / Compétences": "Funciones / Competencias",
    "Pourquoi": "Por qué",
    "Recruteur": "Reclutador",
    "Process": "Proceso",
    "URL": "URL",
    "Aussi à": "También en",
    "Expérience requise : {n} ans": "Experiencia requerida: {n} años",
    "Dossier : prêt (CV et lettre lisibles, une page, coordonnées)": "Expediente: listo (CV y carta legibles, una página, datos de contacto)",
    "Dossier à revoir": "Expediente por revisar",
    "Trouvée par": "Encontrada por",
    "Modifiée par son site": "Modificada por su sitio",
    "La file a changé sur le disque : vue mise à jour.": "La lista cambió en el disco: vista actualizada.",
    "poste": "puesto",
    "salaire": "salario",
    "contrat": "contrato",
    "localisation": "ubicación",
    # profiles
    "Profils…": "Perfiles…",
    "Principal": "Principal",
    "Nouveau profil…": "Nuevo perfil…",
    "Que faire de {cv} ?": "¿Qué hacer con {cv}?",
    "Remplacer mon CV de base": "Sustituir mi CV base",
    "Nouveau profil depuis ce CV": "Nuevo perfil a partir de este CV",
    "Le CV du nouveau profil": "El CV del nuevo perfil",
    "Nom du nouveau profil (par exemple : Chargée RSE à Lyon)": "Nombre del nuevo perfil (por ejemplo: responsable de RSC en Lyon)",
    "Un profil de ce nom existe déjà.": "Ya existe un perfil con este nombre.",
    "Nouveau profil « {nom} » : réponds aux questions dans la fenêtre de commande.": "Nuevo perfil «{nom}»: responde a las preguntas en la ventana de comandos.",
    "Profil changé : JobHunter doit redémarrer pour l'ouvrir. Redémarrer maintenant ?": "Perfil cambiado: JobHunter debe reiniciarse para abrirlo. ¿Reiniciar ahora?",
    "Le profil n'a pas été créé (les questions n'ont pas été terminées).": "El perfil no se ha creado (las preguntas no se terminaron).",
    "Profil créé. L'ouvrir maintenant ? (JobHunter redémarre)": "Perfil creado. ¿Abrirlo ahora? (JobHunter se reinicia)",
    "Associer un compte": "Vincular una cuenta",
    "Retirer le compte": "Quitar la cuenta",
    "Voir CV": "Ver CV",
    "Voir lettre": "Ver carta",
    "Fermer": "Cerrar",
    "Chargement…": "Cargando…",
    "Description": "Descripción",
    "CV": "CV",
    "Lettre": "Carta",
    "Ouvrir": "Abrir",
    "aucun CV/lettre lié à cette offre": "ningún CV ni carta vinculados a esta oferta",
    "Annuler": "Cancelar",
    "Écarter": "Descartar",
    "ou une autre raison :": "u otro motivo:",
    # application
    "Ouverture de Chrome…": "Abriendo Chrome…",
    "Observation de la page…": "Observando la página…",
    "Programme terminé.": "Programa terminado.",
    # Mes CV
    "Chercher une offre (entreprise, poste)": "Buscar una oferta (empresa, puesto)",
    "Sélectionne un CV ou une lettre à gauche": "Selecciona un CV o una carta a la izquierda",
    "CV ⇄ lettre": "CV ⇄ carta",
    "Faits du CV": "Datos del CV",
    "MAJ lettres": "Actualizar cartas",
    "Renommer (mon nom)": "Renombrar (mi nombre)",
    "↑ Haut": "↑ Arriba",
    "↓ Bas": "↓ Abajo",
    # Access
    "Accès aux sources": "Acceso a las fuentes",
    "Rafraîchir": "Refrescar",
    "Collecte des offres": "Recogida de ofertas",
    "Connexions pour candidater": "Inicios de sesión para postular",
    "État de la dernière collecte de chaque source. Un refus n'est pas "
    "réessayé avant 30 jours. Double-clic sur une source à clé : saisir sa clé.": "Estado de "
    "la última recogida de cada fuente. Un rechazo no se reintenta antes de 30 días. Doble "
    "clic en una fuente con clave: introducir su clave.",
    "Saisir la clé": "Introducir la clave",
    "Collecter cette source": "Recoger esta fuente",
    "Rendement des sources": "Rendimiento de las fuentes",
    "accès libre, aucune clé à saisir.": "acceso libre, sin clave.",
    "saisis d'abord sa clé.": "introduce primero su clave.",
    "Tu te connectes toi-même ; les mots de passe restent dans Chrome.": "Inicias sesión tú "
    "mismo; las contraseñas se quedan en Chrome.",
    "Clé": "Clave",
    "Enregistrée dans Scripts/{f}, sur ce PC seulement (ignoré par git).": "Guardada en "
    "Scripts/{f}, solo en este PC (ignorada por git).",
    "Une clé est déjà posée : un champ laissé vide la garde.": "Ya hay una clave: un campo "
    "vacío la conserva.",
    "Afficher la saisie": "Mostrar lo escrito",
    "Elle sert dès la prochaine collecte ; « Collecter cette source » l'essaie.": "Se usa desde "
    "la próxima recogida; «Recoger esta fuente» la prueba.",
    "Obtenir une clé": "Obtener una clave",
    "Filtrer : entreprise, outil ou adresse": "Filtrar: empresa, herramienta o dirección",
    "Adresse de sa page carrière, ou nom de l'entreprise (annuaire)": "Dirección de su página "
    "de empleo, o nombre de la empresa (directorio)",
    "Annuaire": "Directorio",
    "Annuaire des entreprises": "Directorio de empresas",
    "3 600 entreprises lues par l'API publique de Lever, Ashby ou Greenhouse. "
    "Double-clic ou Entrée : suivre.": "3.600 empresas leídas mediante la API pública de "
    "Lever, Ashby o Greenhouse. Doble clic o Intro: seguir.",
    "Identifiant": "Identificador",
    "Outil": "Herramienta",
    "suivie": "seguida",
    "Ouvrir la connexion": "Abrir el inicio de sesión",
    "Vérifier les sessions": "Comprobar sesiones",
    "Source": "Fuente",
    "Dernier état": "Último estado",
    "Collecte du": "Recogida del",
    "Site": "Sitio",
    "Identifiant (email)": "Usuario (correo)",
    "Session": "Sesión",
    "Vérifiée le": "Comprobada el",
    "Flux ATS des entreprises (Greenhouse, Lever, Ashby…)": "Feeds ATS de las empresas "
    "(Greenhouse, Lever, Ashby…)",
    "Flux Workday des entreprises": "Feeds Workday de las empresas",
    "LinkedIn — pages publiques, sans connexion": "LinkedIn — páginas públicas, sin iniciar sesión",
    "EURES (offres européennes)": "EURES (ofertas europeas)",
    "FIR (finance responsable)": "FIR (finanzas responsables)",
    "France Travail — API officielle": "France Travail — API oficial",
    "Adzuna — API officielle": "Adzuna — API oficial",
    "Jooble — API officielle": "Jooble — API oficial",
    # Entreprises
    "Entreprises suivies": "Empresas seguidas",
    "Chaque entreprise est lue par son outil de recrutement (API publique) "
    "ou, à défaut, par son site carrière. Double-clic : ouvrir sa page. "
    "Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres ».": "Cada empresa "
    "se lee mediante su herramienta de selección (API pública) o, si no, su página de "
    "empleo. Doble clic: abrir su página. Los portales generales (LinkedIn, WTJ…) están en "
    "«Portales de empleo».",
    "Lue par": "Leída por",
    "Fit max": "Mejor fit",
    "Dernière": "Última",
    "Page": "Página",
    "Suivre": "Seguir",
    "Ne plus suivre": "Dejar de seguir",
    "Lire les sites carrière": "Leer las páginas de empleo",
    # Job sites
    "Sites d'offres généraux": "Portales de empleo generales",
    "Ajouter": "Añadir",
    "Retirer": "Quitar",
    "Scanner maintenant": "Escanear ahora",
    "Analyse…": "Analizando…",
    # Statistiques
    "Liens OK": "Enlaces válidos",
    "Avec description": "Con descripción",
    "Dossiers préparés": "Candidaturas preparadas",
    "Postulé": "Postulado",
    "Relancé": "Recordatorio enviado",
    "Entretien": "Entrevista",
    "Refus": "Rechazo",
    "Catégorie": "Categoría",
    "Nb": "Núm.",
    "Répartition": "Distribución",
    "Type": "Tipo",
    # Maintenance menus and steps
    "Scrape les sites": "Extraer los sitios",
    "Rattrapage 31 j": "Recuperar 31 días",
    "Sonder flux ATS": "Sondear feeds ATS",
    "Sonder flux Workday": "Sondear feeds Workday",
    "Sonder mots-clés": "Sondear palabras clave",
    "Sync docs+format": "Sincronizar documentos + formato",
    "Export CSV": "Exportar CSV",
    "Relire les lettres": "Revisar las cartas",
    "Pourquoi ce fit": "Por qué este fit",
    "Contrôler les dossiers": "Comprobar las candidaturas",
    "URLs mortes": "URL muertas",
    "Recheck 404": "Volver a comprobar 404",
    "Re-score": "Recalcular nota",
    "Relances": "Recordatorios",
    "Alerte matchs": "Alerta de coincidencias",
    "Clés France Travail": "Claves de France Travail",
    "Fermer Chrome": "Cerrar Chrome",
    "Tester accès aux sites": "Probar el acceso a los sitios",
    "Tests live (lent, ouvre un navigateur)": "Pruebas en vivo (lento, abre un navegador)",
    "1/6 Scan offres (ATS + LinkedIn + V.I.E)": "1/6 Escanear ofertas (ATS + LinkedIn + V.I.E)",
    "3/6 Re-score fit + ATS": "3/6 Recalcular fit + ATS",
    "4/6 Verif liens morts": "4/6 Comprobar enlaces muertos",
    "5/6 Export CSV": "5/6 Exportar CSV",
    "6/6 Alerte nouveaux matchs": "6/6 Alerta de nuevas coincidencias",
    "Sources & offres": "Fuentes y ofertas",
    "Documents": "Documentos",
    "Hygiène de la file": "Limpieza de la lista",
    "Accès & diagnostic": "Acceso y diagnóstico",
    "CV/lettres…": "CV/cartas…",
    "Homepages": "Páginas de inicio",
    "Mettre à jour JobHunter": "Actualizar JobHunter",
    "Collecte chaque matin…": "Recoger cada mañana…",
    "Statuts depuis mes courriels…": "Estados desde mis correos…",
    "Statuts depuis mes courriels": "Estados desde mis correos",
    "Lecture seule : les courriels sont lus et classés (refus, entretien, accusé de "
    "réception), jamais modifiés. Chaque statut proposé attend ton accord.": "Solo lectura: "
    "los correos se leen y se clasifican (rechazo, entrevista, acuse de recibo), nunca se "
    "modifican. Cada estado propuesto espera tu aprobación.",
    "Candidature": "Candidatura",
    "Formule trouvée": "Frase encontrada",
    "{a} courriel(s) lus, {b} statut(s) à proposer.": "{a} correo(s) leído(s), {b} estado(s) "
    "por proponer.",
    "Lecture des courriels…": "Leyendo los correos…",
    'Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".': "Lectura de Gmail: "
    'ejecuta primero pip install "jobhunter[gmail]".',
    "Fichier .mbox": "Archivo .mbox",
    "Dossier de fichiers .eml": "Carpeta de archivos .eml",
    "Fichier .mbox…": "Archivo .mbox…",
    "Dossier .eml…": "Carpeta .eml…",
    "Gmail (lecture seule)": "Gmail (solo lectura)",
    "Suivi occupé : réessaie dans un instant.": "Seguimiento ocupado: inténtalo de nuevo en "
    "un momento.",
    "Le suivi a changé entre-temps : rien écrit.": "El seguimiento cambió mientras tanto: no "
    "se escribió nada.",
    "Appliquer": "Aplicar",
    "Ignorer": "Ignorar",
    "La collecte quotidienne est déjà planifiée. La retirer ?": "La recogida diaria ya está "
    "programada. ¿Quitarla?",
    "Collecter les offres chaque jour à quelle heure ? (format 08:00)": "¿A qué hora recoger "
    "las ofertas cada día? (formato 08:00)",
    "Scan offres": "Escanear ofertas",
    "Candidatures en lot": "Candidaturas en lote",
    "LinkedIn": "LinkedIn",
    # panel cells
    "libre": "libre",
    "clé": "clave",
    "pas encore mesurée": "aún sin medir",
    "clé à créer": "clave por crear",
    "clé refusée": "clave rechazada",
    "vérifie-la": "compruébala",
    "ok": "ok",
    "refusé": "rechazado",
    "limité": "limitado",
    "partiel": "parcial",
    "rien à prendre": "nada nuevo",
    "À revérifier": "Volver a comprobar",
    "Jamais vérifié": "Nunca comprobado",
    "Connecté": "Conectado",
    "Déconnecté": "Desconectado",
    "Bloqué": "Bloqueado",
    "Erreur": "Error",
    "Indéterminé": "Desconocido",
    "site (navigateur)": "sitio (navegador)",
    "plan du site": "mapa del sitio",
    "CV de base": "CV base",
    "Dossiers par offre": "Candidaturas por oferta",
    "prêts": "listos",
    "PDF à refaire": "PDF por rehacer",
    "incomplet": "incompleto",
    "autres : affine la recherche": "más: afina la búsqueda",
    # Dialog boxes
    "Confirmer l'envoi": "Confirmar el envío",
    "As-tu envoyé cette candidature ?": "¿Has enviado esta candidatura?",
    "Supprimer les offres": "Eliminar las ofertas",
    "Supprimer {n} offre(s) cochée(s) de la liste ?\n\n"
    "Une copie est gardée dans Scripts/_corbeille/ — rien n'est perdu.\n"
    "Pour qu'elles ne reviennent pas au prochain scan, préfère\n"
    "« Écarter » : le motif est retenu.": "¿Eliminar {n} oferta(s) marcada(s) de la lista?\n\n"
    "Se guarda una copia en Scripts/_corbeille/ — no se pierde nada.\n"
    "Para que no vuelvan en el próximo escaneo, mejor usa\n"
    "«Descartar»: el motivo se recuerda.",
    "JobHunter — mise à jour": "JobHunter — actualización",
    "La mise à jour n'a pas abouti ; le détail est dans "
    "le journal. Tes données n'ont pas été touchées.": "La actualización no se completó; el "
    "detalle está en el registro. Tus datos no se han tocado.",
    "Version {v} installée. Relancer JobHunter maintenant ?": "Versión {v} instalada. "
    "¿Reiniciar JobHunter ahora?",
    "JobHunter — mise à jour disponible": "JobHunter — actualización disponible",
    "La version {v} est disponible (installée : {installee}).\n\n"
    "L'installer maintenant ? Ton profil, ton CV, tes lettres et ton suivi ne "
    "sont pas touchés, et la version d'avant est sauvegardée.": "La versión {v} está "
    "disponible (instalada: {installee}).\n\n¿Instalarla ahora? Tu perfil, tu CV, tus cartas "
    "y tu seguimiento no se tocan, y la versión anterior se guarda.",
    "pas avant le": "no antes del",
    "offres": "ofertas",
    "offre": "oferta",
    # offer list (counts and placeholders)
    "Sélectionne une offre dans le tableau.": "Selecciona una oferta en la tabla.",
    "Double-clic ou Entrée : fiche complète  ·  clic droit : actions  ·  Suppr : pas intéressé": "Doble clic o Intro: ficha completa  ·  clic derecho: acciones  ·  Supr: no me interesa",
    "aucune offre ne contient « {t} » — Echap ou ✕ pour effacer": "ninguna oferta contiene «{t}» — Esc o ✕ para borrar",
    "aucune offre ne passe les filtres — clique sur ▾ dans une entete pour les lever": "ninguna oferta pasa los filtros — haz clic en ▾ en un encabezado para quitarlos",
    "aucune offre dans la file": "ninguna oferta en la lista",
    "sur {base}": "de {base}",
    "{m} masquée(s) :": "{m} oculta(s):",
    "{n} offre(s)": "{n} oferta(s)",
    "rechercher…": "buscar…",
    "coller un lien d'offre…": "pega el enlace de una oferta…",
}


# App log (langue.journal): a displayed line → its translation; `{a}` keeps the
# variable part of the line as is.
JOURNAL = {
    # ── lignes fixes ──
    "Sélectionne d'abord une offre.": "Selecciona primero una oferta.",
    "Coche d'abord des offres (colonne ☐).": "Marca primero algunas ofertas (columna ☐).",
    "✗ un autre programme écrit suivi.json — réessaie dans un instant.": "✗ otro programa "
    "está escribiendo suivi.json — inténtalo de nuevo en un momento.",
    "Rien à annuler.": "Nada que deshacer.",
    "⏳ suivi.json occupé par un autre programme — réessaie dans un instant.": "⏳ suivi.json "
    "está ocupado por otro programa — inténtalo de nuevo en un momento.",
    "✗ un autre programme modifie la file — réessaie dans un instant.": "✗ otro programa "
    "está modificando la lista — inténtalo de nuevo en un momento.",
    "Bilan de ce que la notation rate : python JobHunter.pyw exclusions": "Lo que la "
    "puntuación no detecta: python JobHunter.pyw exclusions",
    "Le panneau Candidatures est déjà ouvert.": "El panel de candidaturas ya está abierto.",
    "✗ édition réservée aux lettres/.txt — CV : 📂 Ouvrir (Word)": "✗ edición solo para "
    "cartas/.txt — CV: 📂 Abrir (Word)",
    "Sélectionne d'abord un dossier d'offre dans la liste.": "Selecciona primero la carpeta "
    "de una oferta en la lista.",
    "✗ édition intégrée réservée aux lettres/.txt — CV .docx : bouton 📂 Ouvrir (Word)": "✗ "
    "edición integrada solo para cartas/.txt — CV .docx: botón 📂 Abrir (Word)",
    "(clic droit sur l'offre → 🔔 Relance)": "(clic derecho en la oferta → 🔔 Recordatorio)",
    "Prêt. « ▶ TOUT FAIRE » régénère.": "Listo. «▶ HACERLO TODO» regenera.",
    "⏳ tâche en cours.": "⏳ hay una tarea en curso.",
    "⏳ un travail de fond écrit la file (descriptions ou sync docs).": "⏳ un trabajo en "
    "segundo plano escribe la lista (descripciones o sincronización de documentos).",
    "Réessaie dans un instant — il se termine tout seul.": "Inténtalo de nuevo en un momento "
    "— termina solo.",
    "▶ TOUT FAIRE — pipeline complet (6 etapes)": "▶ HACERLO TODO — proceso completo (6 pasos)",
    "⏳ Mise à jour : elle démarre dès que le travail en cours est fini.": "⏳ Actualización: "
    "empieza en cuanto termine el trabajo en curso.",
    "▶ Mise à jour de JobHunter": "▶ Actualizando JobHunter",
    "✅ TOUT FAIRE terminé.": "✅ HACERLO TODO terminado.",
    "(aucune tache en cours)": "(ninguna tarea en curso)",
    "trace complète : Scripts/_logs/app_erreurs.log": "traza completa: "
    "Scripts/_logs/app_erreurs.log",
    "Retour : aucune disposition à rétablir.": "Volver: no hay disposición que restablecer.",
    "✗ pas d'URL http pour récupérer la description": "✗ no hay URL http para obtener la "
    "descripción",
    "✅ description récupérée": "✅ descripción obtenida",
    "✗ description introuvable (page JS/mur login ?)": "✗ descripción no encontrada "
    "(¿página JS o muro de inicio de sesión?)",
    "(pas d'URL → pas de host)": "(sin URL → sin host)",
    "Sélectionne d'abord une source dans la liste.": "Selecciona primero una fuente en la lista.",
    "Selectionne d'abord un site dans la liste.": "Selecciona primero un sitio en la lista.",
    "↪ c'est un site d'offres général → ajoute-le dans « Sites d'offres »": "↪ es un portal "
    "de empleo general → añádelo en «Portales de empleo»",
    "déjà suivi": "ya seguida",
    "Sélectionne d'abord une entreprise dans la liste.": "Selecciona primero una empresa en "
    "la lista.",
    "✗ colle une URL http d'offre.": "✗ pega una URL http de una oferta.",
    "Raccourcis : Echap retour · Alt+Gauche annule agrandir/rétrécir · Ctrl+R recharger · "
    "F5 tout faire · Ctrl+B barre · dans le tableau : Ctrl+Entree postuler, Ctrl+A/D "
    "cocher/decocher, Ctrl+Z annuler · Ctrl+L coller un lien · Ctrl+W arreter · Suppr pas "
    "intéressé": "Atajos: Esc volver · Alt+Izquierda deshace ampliar/reducir · Ctrl+R "
    "recargar · F5 hacerlo todo · Ctrl+B barra · en la tabla: Ctrl+Intro postular, Ctrl+A/D "
    "marcar/desmarcar, Ctrl+Z deshacer · Ctrl+L pegar un enlace · Ctrl+W detener · Supr no "
    "me interesa",
    # ── templates ──
    "📌 statut: {a} → {b}": "📌 estado: {a} → {b}",
    "! écriture suivi.json KO: {a}": "! fallo al escribir suivi.json: {a}",
    "⊖ {a} offre(s) « pas intéressé » — masquées, Ctrl+Z pour annuler.": "⊖ {a} oferta(s) "
    "«no me interesa» — ocultas, Ctrl+Z para deshacer.",
    "✗ annulation impossible pour l'instant ({a}) — réessaie.": "✗ no se puede deshacer "
    "ahora ({a}) — inténtalo de nuevo.",
    "↶ annulé ({a} offre(s)).": "↶ deshecho ({a} oferta(s)).",
    "! écriture sélection KO: {a}": "! fallo al escribir la selección: {a}",
    "ATTENTION : {a}, pas l'offre elle-meme{b}.": "ATENCIÓN: {a}, no la oferta en sí{b}.",
    "🔍 recherche web: {a}": "🔍 búsqueda web: {a}",
    "! exclusions.py introuvable: {a}": "! exclusions.py no encontrado: {a}",
    "! écriture queue KO: {a}": "! fallo al escribir la lista: {a}",
    "✕ {a} offre(s) écartée(s) — « {b} ». {c} nouvelle(s) exclusion(s) ; elles ne "
    "reviendront pas au scan.": "✕ {a} oferta(s) descartada(s) — «{b}». {c} nueva(s) "
    "exclusión(es); no volverán en el escaneo.",
    "! copie de sauvegarde KO ({a}) — suppression ANNULÉE.": "! fallo de la copia de "
    "seguridad ({a}) — eliminación CANCELADA.",
    "🗑 {a} offre(s) supprimée(s) — copie dans Scripts/_corbeille/{b}": "🗑 {a} oferta(s) "
    "eliminada(s) — copia en Scripts/_corbeille/{b}",
    "📮 Candidatures : {a} offre(s), panneau ouvert. Chrome s'ouvre.": "📮 Candidaturas: {a} "
    "oferta(s), panel abierto. Chrome se está abriendo.",
    "💾 enregistré : {a}": "💾 guardado: {a}",
    "! sauvegarde KO: {a}": "! fallo al guardar: {a}",
    "📄 PDF resynchronisé : {a}": "📄 PDF resincronizado: {a}",
    "✗ {a} : pièce manquante ({b})": "✗ {a}: falta un documento ({b})",
    "ℹ {a} description(s) manquante(s) — récupération auto en fond…": "ℹ faltan {a} "
    "descripción(es) — se obtienen automáticamente en segundo plano…",
    "✅ descriptions: +{a} récupérées ({b} restantes, dont Indeed/anti-bot).": "✅ "
    "descripciones: +{a} obtenidas ({b} restantes, incl. Indeed/anti-bot).",
    "🔁 sync docs : {a}": "🔁 sincronización de documentos: {a}",
    "🔎 scan auto : +{a} offre(s). {b}": "🔎 escaneo automático: +{a} oferta(s). {b}",
    "🔎 scan auto : {a}": "🔎 escaneo automático: {a}",
    "🔔 {a} candidature(s) à relancer : {b}": "🔔 {a} candidatura(s) para recordar: {b}",
    "📧 brouillon relance ouvert ({a}) — envoie-le puis passe le statut à « relancé ».": "📧 "
    "borrador de recordatorio abierto ({a}) — envíalo y luego cambia el estado a «relancé».",
    "▶ {a} — fenêtre CONSOLE ouverte. Chrome s'ouvre ; tape Entrée après chaque envoi. "
    "Ferme la console pour arrêter.": "▶ {a} — ventana de CONSOLA abierta. Chrome se abre; "
    "pulsa Intro tras cada envío. Cierra la consola para detener.",
    "! lancement console KO: {a}": "! fallo al abrir la consola: {a}",
    "⏹ arrete (arbre du PID {a}).": "⏹ detenido (árbol del PID {a}).",
    "! arret KO ({a}) — repli sur terminate": "! fallo al detener ({a}) — se recurre a terminate",
    "! panne interne [{a}] — {b}": "! error interno [{a}] — {b}",
    "✗ TOUT FAIRE interrompu à l'étape « {a} ».": "✗ HACERLO TODO interrumpido en el paso «{a}».",
    "－ compte retiré: {a}": "－ cuenta quitada: {a}",
    "Associer un compte ajouté: {a}": "Vínculo de cuenta añadido: {a}",
    "! écriture comptes_sites.json KO: {a}": "! fallo al escribir comptes_sites.json: {a}",
    "💾 suivi enregistré: {a} → {b}": "💾 seguimiento guardado: {a} → {b}",
    "＋ site carrière ajouté, lu par le navigateur : {a}": "＋ página de empleo añadida, "
    "leída por el navegador: {a}",
    "✗ {a} : flux introuvable dans sources_config.json": "✗ {a}: feed no encontrado en "
    "sources_config.json",
    "－ {a} ne sera plus collectée": "－ {a} ya no se recogerá",
    "＋ ajouté : {a}": "＋ añadido: {a}",
    "－ retiré : {a}": "－ quitado: {a}",
    "🔎 analyse de l'offre : {a}": "🔎 analizando la oferta: {a}",
    "＋ flux {a} {b} — lu par API dès la prochaine collecte ({c})": "＋ feed {a} {b} — leído "
    "por API desde la próxima recogida ({c})",
    "＋ flux {a} {b} — lu par API dès la prochaine collecte": "＋ feed {a} {b} — leído por "
    "API desde la próxima recogida",
    "déjà suivi : {a} ({b})": "ya seguida: {a} ({b})",
    "déjà suivi : {a}": "ya seguida: {a}",
}

# The output of the programs the app launches, translated line by line like JOURNAL.
SORTIE = {
    # Collecte (jobhunter.sources)
    "── recherche restreinte à la FRANCE ──": "── búsqueda limitada a FRANCIA ──",
    "── ATS APIs (greenhouse/lever/ashby/recruitee/smartrecruiters) ──": "── API de ATS "
    "(greenhouse/lever/ashby/recruitee/smartrecruiters) ──",
    "── Workday (API publique des grands groupes) ──": "── Workday (API pública de los "
    "grandes grupos) ──",
    "── LinkedIn recherche publique (guest) ──": "── LinkedIn búsqueda pública (invitado) ──",
    "── V.I.E / V.I.A (Business France) ──": "── V.I.E / V.I.A (Business France) ──",
    "── FIR / French SIF (100 % ISR-ESG) ──": "── FIR / French SIF (100 % ISR-ESG) ──",
    "── Talent.com (agrégateur) ──": "── Talent.com (agregador) ──",
    "── Indeed (page 1 des résultats — voir le commentaire de scan_indeed) ──": "── Indeed "
    "(página 1 de resultados — ver el comentario de scan_indeed) ──",
    "── APEC (API publique, annonce entière dans la liste) ──": "── APEC (API pública, "
    "anuncio completo en la lista) ──",
    "── Glassdoor (page 1 de la recherche, France entière) ──": "── Glassdoor (página 1 de "
    "la búsqueda, toda Francia) ──",
    "── eFinancialCareers ({a}, {b} site(s), sitemap public, crawl-delay 10 s) ──": "── "
    "eFinancialCareers ({a}, {b} sitio(s), mapa del sitio público, crawl-delay 10 s) ──",
    "── EURES (portail officiel UE, API publique, crawl-delay 10 s) ──": "── EURES (portal "
    "oficial de la UE, API pública, crawl-delay 10 s) ──",
    "── France Travail (API officielle) ──": "── France Travail (API oficial) ──",
    "── Adzuna (API officielle, France + 7 pays) ──": "── Adzuna (API oficial, Francia + 7 "
    "países) ──",
    "── Jooble (API officielle) ──": "── Jooble (API oficial) ──",
    "── Welcome to the Jungle (sitemap public, débit bridé) ──": "── Welcome to the Jungle "
    "(mapa del sitio público, ritmo limitado) ──",
    "Scan : {a} offres uniques (non ecrit : --dry)": "Escaneo: {a} ofertas únicas (no "
    "escrito: --dry)",
    "Scan : {a} offres uniques (→ {b})": "Escaneo: {a} ofertas únicas (→ {b})",
    "Refus rencontrés (une collecte vide peut venir de là) :": "Rechazos encontrados (una "
    "recogida vacía puede venir de ahí):",
    "Rendement par source :": "Rendimiento por fuente:",
    "{a} ramenées · {b} nouvelles · {c} pertinentes · {d} s": "{a} obtenidas · {b} nuevas · "
    "{c} pertinentes · {d} s",
    "Merge {a}: +{b} nouvelles, {c} enrichies (desc), {d} liens promus (LinkedIn -> vrai "
    "site), {e} hors de France, {f} écartées à la main, {g} déjà rejetées par le tri, {h} "
    "pays écartés, {i} bruits purgés — {j} total": "Fusión {a}: +{b} nuevas, {c} "
    "enriquecidas (desc), {d} enlaces promovidos (LinkedIn -> sitio real), {e} fuera de "
    "Francia, {f} descartadas a mano, {g} ya rechazadas por la clasificación, {h} países "
    "excluidos, {i} ruido eliminado — {j} en total",
    "→ re-score + descriptions manquantes : automatiques au prochain lancement de l'app.": "→ "
    "nueva puntuación + descripciones que faltan: automáticas en el próximo inicio de la app.",
    "Le scan est conserve dans {a} : `jobhunter collect --fusion-seule` le fusionnera.": "El "
    "escaneo se guarda en {a}: `jobhunter collect --fusion-seule` lo fusionará.",
    "! journal de rendement non écrit : {a}": "! registro de rendimiento no escrito: {a}",
    # Descriptions (scrape_desc)
    "Rien à faire : --key ou --all requis.": "Nada que hacer: se requiere --key o --all.",
    "Aucune offre ciblée.": "Ninguna oferta seleccionada.",
    "{a} offre(s) à récupérer…": "{a} oferta(s) por obtener…",
    "── {a}/{b} — {c} ok — {d}s/offre, reste ~{e} min": "── {a}/{b} — {c} ok — "
    "{d}s/oferta, quedan ~{e} min",
    "=== {a}/{b} descriptions enregistrées (API) ===": "=== {a}/{b} descripciones guardadas "
    "(API) ===",
    "=== {a}/{b} descriptions enregistrées dans apply_queue.json ===": "=== {a}/{b} "
    "descripciones guardadas en apply_queue.json ===",
    "✅ {a} car. (via {b})": "✅ {a} caract. (vía {b})",
    "✖ relance navigateur impossible : {a}": "✖ no se pudo reiniciar el navegador: {a}",
    # Re-score (rescore_ats)
    "{a} ATS% + {b} fit re-scorés / {c}": "{a} ATS% + {b} fit recalculados / {c}",
    "Offres exigeant ≥3 ans d'expérience (fit pénalisé) : {a}": "Ofertas que exigen ≥3 años "
    "de experiencia (fit penalizado): {a}",
    "Distribution ATS% : {a}": "Distribución ATS%: {a}",
    # Liens morts (recheck_dead)
    "Aucune offre à revérifier (filtre trop strict ?).": "Ninguna oferta que volver a "
    "comprobar (¿filtro demasiado estricto?).",
    "{a} offre(s) à revérifier en navigateur (status={b})…": "{a} oferta(s) que volver a "
    "comprobar en el navegador (status={b})…",
    "✖ {a} échecs d'affilée — arrêt (relance plus tard, reprise auto)": "✖ {a} fallos "
    "seguidos — parada (vuelve a lanzarlo más tarde, se reanuda solo)",
    "── checkpoint {a}/{b} — {c}s/lien, reste ~{d} min": "── punto de control {a}/{b} — "
    "{c}s/enlace, quedan ~{d} min",
    "=== {a}changements: {b} ===": "=== {a}cambios: {b} ===",
    # Export (export_queue_csv)
    "! apply_queue.json introuvable": "! apply_queue.json no encontrado",
    "(suivi.json illisible : {a} — export sans le suivi)": "(suivi.json ilegible: {a} — "
    "exportación sin el seguimiento)",
    "=== {a} offres -> {b} ({c} Ko) ===": "=== {a} ofertas -> {b} ({c} KB) ===",
    "rotation : {a} supprimé": "rotación: {a} eliminado",
    # Alertes (notify_matches)
    "historique de notification remis à zéro": "historial de notificaciones reiniciado",
    "aucune NOUVELLE offre fit >= {a} (déjà notifiées : {b})": "ninguna oferta NUEVA con fit "
    ">= {a} (ya notificadas: {b})",
    "=== {a} nouvelle(s) offre(s) fit >= {b} ===": "=== {a} oferta(s) nueva(s) con fit >= {b} ===",
    "[dry] pas de notification, historique inchangé": "[dry] sin notificación, historial "
    "sin cambios",
    "notifié — {a} marquée(s), historique {b}": "notificado — {a} marcada(s), historial {b}",
    "non notifié (toast KO) — {a} marquée(s), historique {b}": "no notificado (fallo del "
    "aviso) — {a} marcada(s), historial {b}",
    "! toast échoué : {a}": "! fallo del aviso: {a}",
    "! toast impossible : {a}": "! aviso no disponible: {a}",
    # Update (mise_a_jour)
    "Version installée : {a} · disponible : {b}": "Versión instalada: {a} · disponible: {b}",
    "Version installée : {a} · c'est la plus récente.": "Versión instalada: {a} · es la más "
    "reciente.",
    "Téléchargement de {a} …": "Descargando {a} …",
    "Signature de l'auteur vérifiée.": "Firma del autor verificada.",
    "Signature de l'auteur vérifiée : {a} fichiers de la {b}.": "Firma del autor verificada: "
    "{a} archivos de la {b}.",
    "(Version non signée : empreinte publiée vérifiée.)": "(Versión sin firmar: huella "
    "publicada verificada.)",
    "(Versions non signées : la clé de l'auteur n'est pas encore publiée.)": "(Versiones sin "
    "firmar: la clave del autor aún no se ha publicado.)",
    "! Mise à jour refusée : {a}. Rien n'a été installé.": "! Actualización rechazada: {a}. "
    "No se ha instalado nada.",
    "! Mise à jour refusée : {a}. Rien n'a été modifié.": "! Actualización rechazada: {a}. "
    "No se ha modificado nada.",
    "! Téléchargement impossible ({a}) : la page des versions s'ouvre.": "! No se pudo "
    "descargar ({a}): se abre la página de versiones.",
    "L'installateur s'ouvre : suis ses étapes. Tes données sont gardées.": "Se abre el "
    "instalador: sigue sus pasos. Tus datos se conservan.",
    # Collect every morning (planification)
    "Collecte planifiée chaque jour à {a}, si l'ordinateur est allumé. Journaux : {b}.": "Recogida "
    "programada cada día a las {a}, si el ordenador está encendido. Registros: {b}.",
    "Collecte quotidienne retirée.": "Recogida diaria quitada.",
    "La tâche n'a pas pu être créée : {a}": "No se pudo crear la tarea: {a}",
    "La tâche n'a pas pu être retirée : {a}": "No se pudo quitar la tarea: {a}",
    "Heure invalide : « {a} » (format 08:00).": "Hora no válida: «{a}» (formato 08:00).",
    "Hors Windows : lance ./launchers/schedule.sh depuis le dossier de JobHunter.": "Fuera de "
    "Windows: ejecuta ./launchers/schedule.sh desde la carpeta de JobHunter.",
}
