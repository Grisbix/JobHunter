# 0004 — Une limite de débit s'attend, un refus d'entrée s'arrête

**Statut** : accepté (2026-10-03 ; LinkedIn le 2026-10-17).

## Contexte

Une collecte vide a deux causes opposées : rien à prendre, ou refus d'entrée. Les relancer
de la même façon est exactement ce qu'il ne faut pas faire face à un quota.

## Décision

- **429** (« reviens plus tard ») : pause (`Retry-After`, sinon une attente croissante), puis
  la même page est redemandée ; l'état est gardé pour reprendre d'une exécution à l'autre.
  Durée de passe bornée (LinkedIn : 45 min).
- **403, 999, CAPTCHA** : refus. La source s'arrête, sans boucle, et ne réessaie pas avant
  30 jours.
- `INCIDENTS` compte les refus ; la collecte les affiche, pour qu'un scan bridé ne
  ressemble pas à une journée calme.
- Jamais de contournement : ni rotation d'IP, ni empreinte TLS imitée, ni résolution de
  CAPTCHA, ni moteur « furtif ».

## Conséquences

Moins d'offres certains jours, mais aucun blocage durable et aucun compte sanctionné.
