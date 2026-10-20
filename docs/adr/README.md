# Architecture decisions (ADR)

One decision per file: context, decision, consequences. The code keeps a line or two
and points here. Overview: [`../architecture.md`](../architecture.md).

| No. | Decision |
|---|---|
| [0001](0001-facade-aliases.md) | The old modules become aliases of the package |
| [0002](0002-three-files-three-contracts.md) | Three data files, three access contracts |
| [0003](0003-file-lock-exit-code-3.md) | File lock, and exit code 3 |
| [0004](0004-429-wait-403-stop.md) | A rate limit is waited out, a refusal of entry is a stop |
| [0005](0005-no-automatic-submission.md) | No automatic submission, no password handled |
| [0006](0006-non-regression-bench.md) | A non-regression bench before any overhaul |
| [0007](0007-lazy-profile-values.md) | What comes from the profile is computed on first read |
| [0008](0008-programs-in-the-package.md) | All the code in the package; `JobHunter.pyw` launches without installation |
| [0009](0009-proof-distinct-from-declaration.md) | Proof of sending is distinct from the declaration |
| [0010](0010-offer-identity-company-job.md) | An offer's identity stays "entreprise\|poste"; we repair what it loses |
| [0011](0011-standalone-application.md) | A standalone application for the user, the source code for whoever modifies it |
| [0012](0012-signed-updates.md) | Updates signed by the author, outside GitHub |
| [0013](0013-one-workspace-per-profile.md) | Several profiles: one complete workspace each, switching restarts the app |

New decision: `NNNN-short-title.md`, next number, status and date at the top.
