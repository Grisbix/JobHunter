"""Statuts de candidature lus dans les courriels (étape G4), en lecture seule.

- `lecture` : les courriels, depuis un export (.mbox de Google Takeout, dossier de .eml)
  ou l'API Gmail en lecture seule (client OAuth créé par l'utilisateur, jamais de mot de
  passe) ;
- `statuts` : pour chaque courriel, la candidature du suivi qu'il concerne et le statut
  qu'il suggère (accusé de réception, entretien, refus).

Rien n'est écrit sans validation, une proposition à la fois (`programmes.statuts_mail`,
ou la fenêtre de l'application). Un courriel est une entrée non fiable : il n'est que
lu et classé, jamais suivi (aucun lien ouvert, aucune pièce jointe lue).
"""
