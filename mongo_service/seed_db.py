"""Import pipeline snapshot data into MongoDB.

This script expects real pipeline exports such as `tickers.json`, `sessions.json`,
or `prices.csv` inside `PIPELINE_OUTPUT_DIR`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mongo_service.client import get_client, import_snapshot_dir


def main() -> None:
    mongo_uri = (
        os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "mongodb://mongo:27017"
    )
    db_name = os.getenv("MONGODB_DB_NAME") or os.getenv("MONGO_DB") or "stocks_app"
    snapshot_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "pipeline/output"))

    try:
        client = get_client(mongo_uri)
        client.server_info()
        imported = import_snapshot_dir(
            client, db_name=db_name, snapshot_dir=snapshot_dir
        )
    except Exception as exc:
        print(
            f"Failed to import snapshot data from {snapshot_dir} into MongoDB at {mongo_uri}: {exc}"
        )
        sys.exit(2)

    print(
        f"Imported {len(imported)} collection(s) into '{db_name}' at {mongo_uri}: {', '.join(imported)}"
    )


if __name__ == "__main__":
    main()
