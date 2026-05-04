#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${MONGO_INITDB_DATABASE:-${MONGODB_DB_NAME:-stocks_app}}"
SNAPSHOT_DIR="${PIPELINE_OUTPUT_DIR:-/seed/pipeline}"

if [[ ! -d "$SNAPSHOT_DIR" ]]; then
  echo "Snapshot directory does not exist: $SNAPSHOT_DIR"
  exit 0
fi

shopt -s nullglob
files=("$SNAPSHOT_DIR"/*.json "$SNAPSHOT_DIR"/*.csv)

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No pipeline snapshot files found in $SNAPSHOT_DIR"
  exit 0
fi

for file in "${files[@]}"; do
  collection="$(basename "$file")"
  collection="${collection%.*}"

  if [[ "$file" == *.json ]]; then
    echo "Importing $file into $DB_NAME.$collection as JSON array"
    mongoimport --uri="mongodb://localhost:27017/$DB_NAME" --collection "$collection" --jsonArray --file "$file" --drop
  else
    echo "Importing $file into $DB_NAME.$collection as CSV"
    mongoimport --uri="mongodb://localhost:27017/$DB_NAME" --collection "$collection" --type csv --headerline --file "$file" --drop
  fi
done
