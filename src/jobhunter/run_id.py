"""The identifier of the run that produced a result: which collection found this offer?

A morning pipeline runs several programs one after the other (five collection passes,
descriptions, scoring…). They share ONE identifier, `20261021-080012-a3f9`: the first
program that asks for it creates it and puts it in the environment, so every program it
starts inherits it. A program started alone gets its own.

It is stamped where a result is written:

- `execution` on an offer added to the queue (sources.merge) — the run that found it;
- `execution` on each entry of `changements` and `historique_fit`;
- `execution` on each line of the yield log (`_rendement.jsonl`).

`jobhunter yield --execution <id>` then says what that run brought back. Nothing personal
in it: a date, a time and four random characters.
"""

import os
import secrets
import time

ENV = "JOBHUNTER_EXECUTION"


def courant() -> str:
    """This run's identifier: inherited from the environment, otherwise created there."""
    ident = os.environ.get(ENV, "").strip()
    if not ident:
        ident = f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
        os.environ[ENV] = ident  # the programs this one starts share it
    return ident
