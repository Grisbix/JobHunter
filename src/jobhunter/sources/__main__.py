"""`python -m jobhunter.sources ...` : la collecte (meme interface que Scripts/job_sources.py)."""

import sys

from jobhunter.sources.cli import main

sys.exit(main())
