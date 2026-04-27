from __future__ import annotations

import json
from pathlib import Path

from backend.db import init_db
from backend.repository import upsert_sources


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    init_db()
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    upsert_sources(sources)
    print(f"Database initialized and {len(sources)} sources imported.")


if __name__ == "__main__":
    main()
