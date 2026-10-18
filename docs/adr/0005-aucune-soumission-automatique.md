# 0005 — Aucune soumission automatique, aucun mot de passe manipulé

**Statut** : accepté depuis le début du projet ; ne se rediscute pas au détour d'une tâche.

## Contexte

Remplir un formulaire de candidature fait gagner du temps ; l'envoyer à la place de la
personne engage sa candidature sans relecture, et l'expose aux erreurs de l'automate.
Les mots de passe des sites d'emploi donnent accès à des données personnelles.

## Décision

- La navigation remplit, dépose les documents et **surligne** le bouton d'envoi ; le clic
  final est toujours humain. Aucun drapeau `--auto` / `--submit`, ni commande d'envoi dans
  la CLI (testé).
- `login_flow` ne tape jamais de mot de passe, quel que soit son argument (testé) ; le
  profil de formulaire n'en contient jamais.
- Pas de création de compte automatique ; un code reçu par courriel est collé, le bouton
  « Vérifier » surligné, l'humain clique.

## Conséquences

Chaque candidature passe sous les yeux de son auteur. Le temps gagné reste l'essentiel :
la saisie.
