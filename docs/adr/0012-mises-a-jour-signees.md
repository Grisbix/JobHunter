# 0012 — Mises à jour signées par l'auteur, hors de GitHub

**Statut** : accepté le 2026-10-19 (étape E2 de la feuille de route, JobHunter 2.18.0).
Actif dès que l'auteur a publié sa clé publique (`signature.CLE_PUBLIQUE`).

## Contexte

La mise à jour télécharge du code exécutable : le ZIP d'une étiquette (installation depuis
les sources) ou `JobHunterSetup.exe` (application installée). HTTPS prouve que les octets
viennent de GitHub, pas qu'ils viennent de l'auteur. Un compte GitHub volé, un jeton de
workflow détourné ou une action compromise publieraient une version piégée que chaque
installation prendrait au lancement suivant.

L'attestation de provenance Sigstore (2.10.1) prouve qu'un exécutable sort du workflow du
dépôt ; elle ne protège pas d'un dépôt compromis, et l'application ne la vérifie pas.

Pistes écartées :
- **tufup** : sa purge du dossier de destination est incompatible avec un dossier qui
  contient des données de l'utilisateur, et il apporte un format de dépôt TUF à héberger ;
- **WinSparkle** : Windows seulement, et sa signature DSA/EdDSA est la même idée avec une
  bibliothèque C en plus ;
- **signature Authenticode** : certificat payant, et ne couvre pas le ZIP des sources ;
- **signature faite par la CI** : la clé serait un secret du dépôt, donc à la portée de
  qui compromet le dépôt — exactement le cas à couvrir.

## Décision

- **Ed25519 en Python pur** (`jobhunter.signature`, RFC 8032 section 6, vecteurs de la RFC
  en test) : aucune dépendance nouvelle, ni dans le paquet ni dans l'installateur.
- **La clé privée ne quitte jamais l'ordinateur de l'auteur** (`~/.jobhunter/cle_signature`,
  créée par `outils/signature.py cle`). La clé publique est écrite dans le code.
- **On signe un manifeste**, pas une archive : la version, l'empreinte SHA-256 de chaque
  fichier du ZIP de l'étiquette, et celle de `JobHunterSetup.exe`. Les ZIP que GitHub
  fabrique ne sont pas garantis identiques octet pour octet ; leur contenu, si. Le manifeste
  signé est attaché à la release (`signature.json`), après la CI de l'installateur.
- **À l'installation** :
  - sources : le ZIP de l'étiquette de la version annoncée ; chaque fichier doit avoir son
    empreinte signée, aucun ne doit manquer ni s'ajouter ; sinon rien n'est écrit ;
  - application : l'installateur doit avoir l'empreinte signée ; sinon il n'est pas ouvert.
    Vérifié, il est ouvert normalement : l'utilisateur le fait avancer.
- **Pas de retour en arrière** : le manifeste porte sa version, qui doit être celle
  annoncée ; une ancienne signature valide ne fait pas réinstaller une vieille version.
- **Transition** : tant que `CLE_PUBLIQUE` est vide, la mise à jour se fait comme avant et le
  dit ; l'application contrôle au moins l'empreinte publiée de l'installateur. La première
  version qui porte la clé est installée sans signature (elle n'en a pas encore) ; toutes
  les suivantes l'exigent.

## Conséquences

- Publier une version demande une étape de plus, chez l'auteur :
  `uv run python outils/signature.py signer X.Y.Z --publier`, une fois la CI finie.
  Une release sans `signature.json` est refusée par les installations qui ont la clé.
- **Perdre la clé privée** empêche toute mise à jour automatique : chaque installation
  devra reprendre l'installateur à la main. L'auteur la sauvegarde hors de l'ordinateur.
- Un dépôt cloné avec git (développeur) n'est pas concerné : `git pull` suit le dépôt.
