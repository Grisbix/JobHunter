# Architecture decisions (ADR)

One decision per file: context, decision, consequences. The code keeps a line or two
and points here. Overview: [`../architecture.md`](../architecture.md).

| No. | Decision |
|---|---|
| [0001](0001-facades-alias.md) | The old modules become aliases of the package |
| [0002](0002-trois-fichiers-trois-contrats.md) | Three data files, three access contracts |
| [0003](0003-verrou-fichier-code-3.md) | File lock, and exit code 3 |
| [0004](0004-429-attendre-403-arreter.md) | A rate limit is waited out, a refusal of entry is a stop |
| [0005](0005-aucune-soumission-automatique.md) | No automatic submission, no password handled |
| [0006](0006-banc-de-non-regression.md) | A non-regression bench before any overhaul |
| [0007](0007-valeurs-du-profil-paresseuses.md) | What comes from the profile is computed on first read |
| [0008](0008-programmes-dans-le-paquet.md) | All the code in the package; `JobHunter.pyw` launches without installation |
| [0009](0009-preuve-distincte-de-la-declaration.md) | Proof of sending is distinct from the declaration |
| [0010](0010-identite-entreprise-poste.md) | An offer's identity stays "entreprise\|poste"; we repair what it loses |
| [0011](0011-application-autonome.md) | A standalone application for the user, the source code for whoever modifies it |
| [0012](0012-mises-a-jour-signees.md) | Updates signed by the author, outside GitHub |

New decision: `NNNN-short-title.md`, next number, status and date at the top.
