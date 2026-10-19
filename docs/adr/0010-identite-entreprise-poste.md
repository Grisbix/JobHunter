# 0010 — L'identité d'une offre reste « entreprise|poste » ; on répare ce qu'elle perd

**Statut** : accepté le 2026-10-19 (étude C2 de la feuille de route, JobHunter 2.6.0).

## Contexte

L'identité d'une offre est `entreprise|poste` (`queue_io.oid`). C'est aussi la clé de
`suivi.json`, la donnée la moins reconstituable du projet : une candidature perdue ne
revient pas. Codex proposait d'étudier une identité plus robuste ; l'étude a mesuré ce que
la clé actuelle fait réellement perdre.

1. **Même poste dans plusieurs villes.** Sur 86 offres tirées de vraies réponses rejouées
   (`tests/reponses/`), **12 partagent leur clé** avec une autre de lieu différent. Par
   exemple : Forvis Mazars à Düsseldorf, Mannheim, Hambourg et Francfort, ou Alan à Dakar
   et Abidjan. Le dédoublonnage du scan gardait la première vue, au hasard de l'ordre : la
   ville voulue pouvait être perdue au profit d'une autre que le filtre de lieu écartait
   ensuite.
2. **Même annonce sous deux clés.** Dans une file réelle de 12 169 offres, 9 URL d'annonce
   portent 2 ou 3 clés. Les causes :
   - un employeur qui retouche son intitulé (Qonto : trois titres pour une seule annonce
     Lever) ;
   - un flux renommé (« PwC France », puis « PwC », même lien Workday).

   La fusion rattache déjà par URL les offres qu'elle reçoit (vérifié) : ce sont des
   doublons anciens, que rien ne réunissait.

Aucun cas n'oblige à changer la clé, et la changer migrerait le suivi pour un gain non
démontré.

## Décision

- **La clé reste `entreprise|poste`.** Pas de migration du suivi.
- **Plusieurs villes** : le dédoublonnage du scan (`sources.cli.dedoublonner`) garde
  l'exemplaire de la meilleure zone du profil. L'ordre est prioritaire, secondaire, reste
  de la France, international, puis inconnu ; à égalité, le premier vu l'emporte, comme
  avant. Les autres villes vont dans `autres_lieux`, affiché par la fiche (« Aussi à : »).
- **Même URL d'annonce** : `doublons` réunit les offres qui partagent une URL désignant
  une annonce, c'est-à-dire avec un identifiant numérique, un UUID ou un chemin d'offre.
  Une page carrière générique n'unit jamais deux postes. Le tri retire les doublons
  chaque jour.
  - Il garde l'offre suivie (jamais retirée), puis la meilleure source, la langue, et
    **la version que la source sert encore** (`vu_le`), donc l'intitulé actuel.

## Conséquences

Le poste à Paris n'est plus perdu derrière son jumeau de Berlin, et les intitulés
retouchés ne s'accumulent plus. Deux cas restent hors d'atteinte, sans dommage pour le
suivi :
- deux postes **réellement distincts** de même intitulé et de même ville, que la clé
  confond. Aucun n'a été observé ;
- une annonce republiée sous une **nouvelle URL** et un nouvel intitulé.
