"""``python -m waymaker_ai.dataset`` runs the dataset validator (same as ``-m waymaker_ai.dataset.validate``)."""
from __future__ import annotations

from waymaker_ai.dataset.validate import main

if __name__ == "__main__":
    raise SystemExit(main())
