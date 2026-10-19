# 0009 — La preuve d'envoi est distincte de la déclaration

**Statut** : accepté le 2026-10-19 (JobHunter 2.2.0).

## Contexte

Jusqu'à la 2.1, une candidature passait à « postulé » quand l'utilisateur le disait : une
touche dans la console du programme de candidature, puis, une seconde fois, une
confirmation dans l'application. Rien ne gardait la trace de ce que le site avait affiché.
Or un envoi peut échouer sans bruit : champ obligatoire oublié, session expirée, bouton
cliqué deux fois. « J'ai cliqué Envoyer » et « le site a reçu ma candidature » sont deux
faits différents.

## Décision

- Le clic d'envoi reste celui de l'utilisateur ([0005](0005-aucune-soumission-automatique.md)) ;
  il le **déclare** ensuite (bouton « J'ai envoyé » de l'application, ou touche en mode
  terminal).
- Après la déclaration, le programme **observe** la page sans rien cliquer ni saisir, et
  écrit dans le suivi, en une seule fois : `s: "postulé"`, `envoi` et `preuve`.
  - `envoi: "confirmé"` seulement si la page montre une phrase de confirmation
    (« Merci pour votre candidature », « Application submitted »…) ou une adresse de
    confirmation, **et** que le formulaire a disparu.
  - `envoi: "incertain"` dans tous les autres cas : formulaire encore là, message
    d'erreur, page muette.
  - `envoi: "déclaré"` quand l'utilisateur confirme à la main, sans observation.
  - `preuve` : l'extrait vu, l'adresse, la date et une capture de la page
    (`Scripts/_preuves/`, données locales).
- Le statut reste « postulé » dans les trois cas : relances et métriques n'en dépendent pas.
- « Incertain » ne relance **jamais** un envoi : c'est un signal à vérifier, pas une erreur
  à réparer.
- Un formulaire rempli mais non envoyé (« préparé ») n'est pas une candidature : il reste
  dans le journal du programme (`apply_runner_done.json`), pas dans le suivi.

## Conséquences

Le suivi dit ce qui a été observé, pas seulement ce qui a été dit. La détection est
volontairement prudente : une page de confirmation inhabituelle donnera « incertain »,
jamais l'inverse. Les motifs vivent dans `jobhunter/navigation/confirmation.py` et
s'enrichissent avec les pages réellement rencontrées.
