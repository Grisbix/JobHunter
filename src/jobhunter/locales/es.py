"""Spanish interface texts, indexed by the displayed French text.

Read by the web window (it was the desktop window's texts_es until 3.29). A text missing from
here is displayed in English, then in French. The keys are those of `en.TEXTES`,
`JOURNAL` and `SORTIE`.
"""

NOM = "Español"
RELANCER = "Reinicia JobHunter para usar la interfaz en español."

TEXTES: dict[str, str] = {
    # 3.15: indicators, history, kept posting, answers
    "offres en file": "ofertas en la lista",
    "candidatures envoyées": "candidaturas enviadas",
    "▶ Candidatures envoyées": "▶ Candidaturas enviadas",
    "entretiens": "entrevistas",
    "sans réponse depuis 30 jours": "sin respuesta desde hace 30 días",
    "sur {n} réponse(s) datée(s)": "sobre {n} respuesta(s) fechada(s)",
    "{r} réponse(s), {e} entretien(s) · {p}": "{r} respuesta(s), {e} entrevista(s) · {p}",
    # navigation and header
    "JOBHUNTER": "JOBHUNTER",
    "Mes CV": "Mis CV",
    "Entreprises": "Empresas",
    "Accès": "Acceso",
    "ACTIONS": "ACCIONES",
    "Actualiser les offres": "Actualizar ofertas",
    "↶ Retour": "↶ Volver",
    "Retour": "Volver",
    # offers table
    "Chercher": "Buscar",
    "Postuler": "Postular",
    "Suivi et note ▸": "Seguimiento y nota ▸",
    "Fit": "Fit",
    "Lien": "Enlace",
    "Note": "Nota",
    "Garder": "Mantener",
    "Exclure": "Excluir",
    "Tout": "Todo",
    # card and tracking
    "Envoi confirmé": "Envío confirmado",
    # base CV (drag-and-drop, CV panel)
    "Remplacer mon CV de base…": "Reemplazar mi CV base…",
    "Choisis ton nouveau CV de base": "Elige tu nuevo CV base",
    # offer card: provenance and changes, queue watched
    "Canal": "Canal",
    "Action": "Acción",
    "État lien": "Estado del enlace",
    "Pourquoi": "Por qué",
    "Process": "Proceso",
    "URL": "URL",
    "Aussi à": "También en",
    "Dossier à revoir": "Expediente por revisar",
    "collecte {a}": "recogida {a}",
    "poste": "puesto",
    "salaire": "salario",
    "contrat": "contrato",
    "localisation": "ubicación",
    "Appels d'API aujourd'hui (tous profils) : ": "Llamadas a la API hoy (todos los perfiles): ",
    "{nom} : connexion vérifiée, la clé fonctionne.": "{nom}: conexión verificada, la clave funciona.",
    "{nom} : aucune clé enregistrée (Saisir la clé).": "{nom}: ninguna clave guardada (Introducir la clave).",
    "{nom} : clé refusée par le service — vérifie-la ou crée-en une nouvelle.": "{nom}: clave rechazada por el servicio — revísala o crea una nueva.",
    "{nom} : quota atteint — la clé est bonne, réessaie demain.": "{nom}: cuota alcanzada — la clave es correcta, inténtalo mañana.",
    "{nom} : le service répond mais en erreur — réessaie plus tard.": "{nom}: el servicio responde con un error — inténtalo más tarde.",
    "{nom} : pas de réponse (hors ligne ?).": "{nom}: sin respuesta (¿sin conexión?).",
    "description": "descripción",
    "re-score": "nueva puntuación",
    "Mots-clés de recherche": "Palabras clave de búsqueda",
    "Intitulés à garder": "Títulos que se conservan",
    "Rien n'est enregistré :": "No se ha guardado nada:",
    "Suggestions depuis mon CV…": "Sugerencias desde mi CV…",
    "Annuler les modifications": "Deshacer los cambios",
    "Suggestions depuis ton CV": "Sugerencias desde tu CV",
    "Compétence": "Competencia",
    # profiles
    "Renommer « {nom} »…": "Renombrar «{nom}»…",
    "Archiver ce profil ? Son dossier est rangé dans profiles/_archives (rien n'est supprimé) et JobHunter redémarre sur le profil principal.": "¿Archivar este perfil? Su carpeta se mueve a profiles/_archives (no se borra nada) y JobHunter se reinicia con el perfil principal.",
    "Une collecte tourne pour ce profil : réessaie quand elle aura fini.": "Hay una recopilación en curso para este perfil: inténtalo de nuevo cuando termine.",
    "Profils…": "Perfiles…",
    "Recettes de nettoyage…": "Recetas de limpieza…",
    "Recettes de nettoyage": "Recetas de limpieza",
    "Lancer la collecte du matin": "Lanzar la recogida matinal",
    "Collecte du matin : {a} ✓": "Recogida matinal: {a} ✓",
    " · en erreur : {a}": " · con error: {a}",
    "Collecte en cours depuis {a}": "Recogida en curso desde {a}",
    "Collecte interrompue ({a}) — {b}": "Recogida interrumpida ({a}) — {b}",
    "Collecte arrêtée ({a} : {b}) — {c}": "Recogida detenida ({a}: {b}) — {c}",
    "Aucune collecte du matin enregistrée": "Ninguna recogida matinal registrada",
    "Pas de collecte depuis {a}": "Sin recogida desde {a}",
    "dernière réussie : {a}": "última correcta: {a}",
    "aucune réussie": "ninguna correcta",
    "aujourd'hui {a}": "hoy {a}",
    "hier {a}": "ayer {a}",
    "Enregistrer la vue actuelle…": "Guardar la vista actual…",
    "Supprimer la vue « {a} » ?": "¿Eliminar la vista «{a}»?",
    "Enregistrer les changements de « {a} » ?": "¿Guardar los cambios de «{a}»?",
    "ouvert dans Word": "abierto en Word",
    "Une règle par ligne : champ | valeur à remplacer | nouvelle valeur. Une valeur doit correspondre au champ entier (majuscules et espaces ignorés) ; « re: » introduit un motif. Rejouer les mêmes recettes ne change rien la deuxième fois. Une offre à laquelle tu as postulé n'est jamais renommée.": "Una regla por línea: campo | valor a reemplazar | valor nuevo. Un valor debe coincidir con el campo entero (mayúsculas y espacios ignorados); «re:» introduce un patrón. Volver a aplicar las mismas recetas no cambia nada la segunda vez. Una oferta a la que postulaste nunca se renombra.",
    "Champ": "Campo",
    "Avant": "Antes",
    "Après": "Después",
    "Remarque": "Nota",
    "candidature : gardé": "postulada: se mantiene",
    "doublon : gardé": "duplicado: se mantiene",
    "{a} changement(s), {b} écarté(s). Rien n'est écrit.": "{a} cambio(s), {b} descartado(s). No se escribe nada.",
    "Recettes enregistrées : rien à changer dans la file.": "Recetas guardadas: nada que cambiar en la cola.",
    "Enregistrer et appliquer": "Guardar y aplicar",
    "entreprise": "empresa",
    "Documents à comparer…": "Documentos para comparar…",
    "Documents à comparer": "Documentos para comparar",
    "Tu as retouché ces documents à la main ; une version plus récente a été générée à côté. Rouge : seulement dans ta version. Vert : seulement dans la nouvelle. La version que tu ne gardes pas est mise de côté dans _a_comparer/_anciennes/, jamais supprimée.": "Retocaste estos documentos a mano; se generó una versión más reciente al lado. Rojo: solo en tu versión. Verde: solo en la nueva. La versión que no conserves se aparta en _a_comparer/_anciennes/, nunca se borra.",
    "Aucun document en attente de comparaison.": "Ningún documento pendiente de comparar.",
    "Lecture impossible : {a}": "No se puede leer: {a}",
    "Impossible pour l'instant ({a}) : le document est-il ouvert dans Word ?": "No es posible por ahora ({a}): ¿está el documento abierto en Word?",
    "Version mise de côté : {a}": "Versión apartada: {a}",
    "Prendre la nouvelle version": "Tomar la versión nueva",
    "Garder ma version": "Conservar mi versión",
    "Dernière collecte": "Última recogida",
    "suspendue": "suspendida",
    "Un site lu par le navigateur ne se suspend pas : retire-le.": "Un sitio leído por el navegador no se suspende: quítalo.",
    "⏸ {a} suspendue": "⏸ {a} suspendida",
    "▶ {a} reprise": "▶ {a} reanudada",
    "Principal": "Principal",
    "Nouveau profil depuis ce CV": "Nuevo perfil a partir de este CV",
    "Nouveau profil « {nom} » : vérifie et complète ce que JobHunter a lu dans le CV.": "Nuevo perfil «{nom}»: revisa y completa lo que JobHunter ha leído en el CV.",
    "Une tâche tourne sur ce profil : attends qu'elle finisse (ou « Arrêter »), puis change de profil.": "Hay una tarea en curso en este perfil: espera a que termine (o «Detener») y luego cambia de perfil.",
    "Le profil n'a pas été créé (les questions n'ont pas été terminées).": "El perfil no se ha creado (las preguntas no se terminaron).",
    "Profil créé. L'ouvrir maintenant ? (JobHunter redémarre)": "Perfil creado. ¿Abrirlo ahora? (JobHunter se reinicia)",
    "Voir CV": "Ver CV",
    "Voir lettre": "Ver carta",
    "Description": "Descripción",
    "CV": "CV",
    "ou une autre raison :": "u otro motivo:",
    # application
    "Ouverture de Chrome…": "Abriendo Chrome…",
    # Mes CV
    "Chercher une offre (entreprise, poste)": "Buscar una oferta (empresa, puesto)",
    "↑ Haut": "↑ Arriba",
    "↓ Bas": "↓ Abajo",
    # Access
    "Rafraîchir": "Refrescar",
    "Connexions pour candidater": "Inicios de sesión para postular",
    "État de la dernière collecte de chaque source. Un refus n'est pas "
    "réessayé avant 30 jours. Double-clic sur une source à clé : saisir sa clé.": "Estado de "
    "la última recogida de cada fuente. Un rechazo no se reintenta antes de 30 días. Doble "
    "clic en una fuente con clave: introducir su clave.",
    "Saisir la clé": "Introducir la clave",
    "saisis d'abord sa clé.": "introduce primero su clave.",
    "Tu te connectes toi-même ; les mots de passe restent dans Chrome.": "Inicias sesión tú "
    "mismo; las contraseñas se quedan en Chrome.",
    "Clé": "Clave",
    "Une clé est déjà posée : un champ laissé vide la garde.": "Ya hay una clave: un campo "
    "vacío la conserva.",
    "Afficher la saisie": "Mostrar lo escrito",
    "Obtenir une clé": "Obtener una clave",
    "Filtrer : entreprise, outil ou adresse": "Filtrar: empresa, herramienta o dirección",
    "Adresse de sa page carrière, ou nom de l'entreprise (annuaire)": "Dirección de su página "
    "de empleo, o nombre de la empresa (directorio)",
    "Entreprises de mes offres : flux publics": "Empresas de mis ofertas: feeds públicos",
    "Annuaire": "Directorio",
    "Annuaire des entreprises": "Directorio de empresas",
    "3 600 entreprises lues par l'API publique de Lever, Ashby ou Greenhouse. "
    "Double-clic ou Entrée : suivre.": "3.600 empresas leídas mediante la API pública de "
    "Lever, Ashby o Greenhouse. Doble clic o Intro: seguir.",
    "Identifiant": "Identificador",
    "Outil": "Herramienta",
    "Ouvrir la connexion": "Abrir el inicio de sesión",
    "Vérifier les sessions": "Comprobar sesiones",
    "Dernier état": "Último estado",
    "Collecte du": "Recogida del",
    "Site": "Sitio",
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
    "Chaque entreprise est lue par son outil de recrutement (API publique) "
    "ou, à défaut, par son site carrière. Double-clic : ouvrir sa page. "
    "Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres ».": "Cada empresa "
    "se lee mediante su herramienta de selección (API pública) o, si no, su página de "
    "empleo. Doble clic: abrir su página. Los portales generales (LinkedIn, WTJ…) están en "
    "«Portales de empleo».",
    "Lue par": "Leída por",
    "Dernière": "Última",
    "Page": "Página",
    "Ne plus suivre": "Dejar de seguir",
    "Lire les sites carrière": "Leer las páginas de empleo",
    # Job sites
    "Ajouter": "Añadir",
    # Statistiques
    "Liens OK": "Enlaces válidos",
    "Nb": "Núm.",
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
    "Alerte matchs": "Alerta de coincidencias",
    "Clés France Travail": "Claves de France Travail",
    "Fermer Chrome": "Cerrar Chrome",
    "Tester accès aux sites": "Probar el acceso a los sitios",
    "Tests live (lent, ouvre un navigateur)": "Pruebas en vivo (lento, abre un navegador)",
    "Sources & offres": "Fuentes y ofertas",
    "Hygiène de la file": "Limpieza de la lista",
    "Accès & diagnostic": "Acceso y diagnóstico",
    "CV/lettres…": "CV/cartas…",
    "Homepages": "Páginas de inicio",
    "Statuts depuis mes courriels…": "Estados desde mis correos…",
    "Statuts depuis mes courriels": "Estados desde mis correos",
    "Lecture seule : les courriels sont lus et classés (refus, entretien, accusé de "
    "réception), jamais modifiés. Chaque statut proposé attend ton accord.": "Solo lectura: "
    "los correos se leen y se clasifican (rechazo, entrevista, acuse de recibo), nunca se "
    "modifican. Cada estado propuesto espera tu aprobación.",
    "Candidature": "Candidatura",
    "{a} courriel(s) lus, {b} statut(s) à proposer.": "{a} correo(s) leído(s), {b} estado(s) "
    "por proponer.",
    "Lecture des courriels…": "Leyendo los correos…",
    'Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".': "Lectura de Gmail: "
    'ejecuta primero pip install "jobhunter[gmail]".',
    "Fichier .mbox": "Archivo .mbox",
    "Fichier .mbox…": "Archivo .mbox…",
    "Dossier .eml…": "Carpeta .eml…",
    "Gmail (lecture seule)": "Gmail (solo lectura)",
    "Ignorer": "Ignorar",
    "La collecte quotidienne est déjà planifiée. La retirer ?": "La recogida diaria ya está "
    "programada. ¿Quitarla?",
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
    "site (navigateur)": "sitio (navegador)",
    "plan du site": "mapa del sitio",
    "CV de base": "CV base",
    "prêts": "listos",
    "PDF à refaire": "PDF por rehacer",
    "incomplet": "incompleto",
    # Dialog boxes
    "Confirmer l'envoi": "Confirmar el envío",
    "As-tu envoyé cette candidature ?": "¿Has enviado esta candidatura?",
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
    "Version installée : {installee}": "Versión instalada: {installee}",
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
    "aucune offre ne passe les filtres — clique sur ▾ dans une entete pour les lever": "ninguna oferta pasa los filtros — haz clic en ▾ en un encabezado para quitarlos",
    "aucune offre pour l'instant : clique « Actualiser les offres » à gauche": "aún no hay ofertas: haz clic en « Actualizar ofertas » a la izquierda",
    "sur {base}": "de {base}",
    "{n} offre(s)": "{n} oferta(s)",
    # 3.18: the Profil panel (profiles, fit weights, skills)
    "Poids des axes": "Peso de los ejes",
    "Combien compte chaque axe du profil quand l'annonce cite ses compétences.": "Cuánto cuenta cada eje del perfil cuando la oferta cita sus competencias.",
    "Score qui vaut 10": "Puntuación que vale 10",
    "La somme pondérée des axes qui donne 10. Plus bas : les notes montent.": "La suma ponderada de los ejes que da 10. Más baja: las notas suben.",
    "Intitulé": "Título",
    "Ajouté ou retiré selon les mots du titre de l'offre.": "Se suma o se resta según las palabras del título de la oferta.",
    "Relire la file": "Releer la lista",
    "Expérience demandée": "Experiencia pedida",
    "Retiré quand l'annonce demande au moins ce nombre d'années.": "Se resta cuando la oferta pide al menos estos años.",
    "Recalculer maintenant le fit enregistré de chaque offre de ta file ? Le tableau et le tri l'utilisent.": "¿Recalcular ahora el fit guardado de cada oferta de tu lista? La tabla y la clasificación lo usan.",
    "Lecture des offres de ta file… (une trentaine de secondes)": "Leyendo las ofertas de tu lista… (unos treinta segundos)",
    "Aucune offre choisie": "Ninguna oferta elegida",
    "Rien à enregistrer : les poids sont ceux du profil.": "Nada que guardar: los pesos son los del perfil.",
    "Lecture impossible": "Lectura imposible",
    "profil actif": "perfil activo",
    "profil principal": "perfil principal",
    "Compte pour les axes": "Cuenta para los ejes",
    "Nouvelle": "Nueva",
    "Compétences enregistrées (profil d'avant : {bak}).": "Competencias guardadas (perfil anterior: {bak}).",
    "Un profil = une recherche complète : sa file d'offres, ses candidatures, ses CV et lettres, ses réglages. Ouvrir un autre profil redémarre JobHunter dessus ; un profil archivé est rangé, jamais supprimé.": "Un perfil = una búsqueda completa: su lista de ofertas, sus candidaturas, sus CV y cartas, sus ajustes. Abrir otro perfil reinicia JobHunter en él; un perfil archivado se guarda aparte, nunca se borra.",
    "Nouveau profil : choisis le CV (.docx ou .pdf) dont il partira": "Perfil nuevo: elige el CV (.docx o .pdf) del que partirá",
    "Donne un nom à la compétence.": "Dale un nombre a la competencia.",
    "Rien à enregistrer.": "Nada que guardar.",
    "{n} compétences dans le profil actif.": "{n} competencias en el perfil activo.",
    # 3.19: statuses, contracts, statistics, settings
    "à postuler": "por postular",
    "postulé": "postulado",
    "relancé": "seguimiento hecho",
    "entretien": "entrevista",
    "refus": "rechazo",
    "mauvaise": "no adecuada",
    "expiré": "caducada",
    "CDI": "Indefinido",
    "CDD": "Temporal",
    "Interim": "ETT",
    "Freelance": "Autónomo",
    "V.I.E": "V.I.E",
    "Bénévolat": "Voluntariado",
    "Saisonnier": "Temporada",
    "Temps partiel": "Media jornada",
    "Ne plus suivre « {nom} » ? Son adresse de flux sera retirée ; « Suspendre / Reprendre » la garde.": "¿Dejar de seguir «{nom}»? Se eliminará la dirección de su feed; «Suspender / Reanudar» la conserva.",
    # Statistics: the default domain and the channel values.
    "Autre": "Otro",
    "manuel": "manual",
    "auto": "automático",
    "le {d}": "el {d}",
    "{n} j": "{n} d",
    "▶ Sur les offres à fit ≥ 8": "▶ Ofertas con fit ≥ 8",
    "{n} muette(s) depuis {j} j": "{n} sin novedades desde hace {j} d",
    "Paramètres": "Ajustes",
    "Langue de l'interface": "Idioma de la interfaz",
    "Version": "Versión",
    "Vérifier les mises à jour": "Buscar actualizaciones",
    # 3.19.1: the ⚙ menu
    "Vérifier les offres en ligne": "Ofertas aún en línea",
    # 3.19.1: the ⚑ column explained
    "⚑ Alerte — vide quand tout va bien": "⚑ Alerta — vacía si todo va bien",
    "⚠ condition éliminatoire (permis, nationalité, droit de travail, habilitation)": "⚠ condición eliminatoria (carné, nacionalidad, permiso de trabajo, habilitación)",
    # 3.20.0: progress, the ☰ button, the Outils menu, the daily collection in Paramètres
    "Collecte automatique": "Recogida automática",
    "Chaque jour à l'heure choisie, l'ordinateur collecte les offres de tous tes profils, même si JobHunter est fermé.": "Cada día a la hora elegida, el ordenador recoge las ofertas de todos tus perfiles, aunque JobHunter esté cerrado.",
    "Pas planifiée.": "No programada.",
    "☰ Menu": "☰ Menú",
    "{a}/{b} sources": "{a}/{b} fuentes",
    "~{d} restantes": "~{d} restantes",
    "Vérification {a}/{b}": "Comprobación {a}/{b}",
    "Vérification des offres": "Comprobación de ofertas",
    # 3.21.0: places in « Ma recherche »
    "Où tu veux travailler": "Dónde quieres trabajar",
    "Zones des offres mises à jour": "Zonas de las ofertas actualizadas",
    # 3.26: progress legend
    "✓ a répondu": "✓ respondió",
    "… en cours": "… en curso",
    "Retirées de la file et bloquées au prochain scan. Le motif sert à corriger la notation.": "Retiradas de la lista y bloqueadas en el próximo escaneo. El motivo sirve para corregir la puntuación.",
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
    "site), {e} hors zone, {f} écartées à la main, {g} déjà rejetées par le tri, {h} "
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
    "(Version {a} non signée : la clé de l'auteur n'est pas encore publiée.)": "(Versión {a} sin "
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

# The lines of the fit explanation (scoring.fit.expliquer): language.explication.
FIT = {
    "{axe} {pct} (x{poids}) : {mots}": "{axe} {pct} (x{poids}): {mots}",
    "vocabulaire : {v}/10": "vocabulario: {v}/10",
    "intitulé du métier visé en second (finance)": "título del segundo puesto buscado (finanzas)",
    "intitulé du cœur de cible : plafond 10": "título en el núcleo del objetivo: tope 10",
    "plafond {cap} (cœur {c}, complément {k})": "tope {cap} (núcleo {c}, complemento {k})",
    "intitulé HSE : plafond {cap}": "título HSE: tope {cap}",
    "métier hors cible dans l'intitulé : plafond {cap}": "puesto fuera del objetivo en el título: tope {cap}",
    "intitulé junior « {mot} » : +{b}": "título junior «{mot}»: +{b}",
    "intitulé senior : -{m}": "título sénior: -{m}",
    "intitulé écarté « {mot} » : -2": "título descartado «{mot}»: -2",
    "annonce redigee en {lg} : plafond {p}": "oferta redactada en {lg}: tope {p}",
    "annonce exige {x} : plafond {p}": "la oferta exige {x}: tope {p}",
    "{n} an(s) d'expérience demandés : -{m}": "{n} año(s) de experiencia requeridos: -{m}",
}
