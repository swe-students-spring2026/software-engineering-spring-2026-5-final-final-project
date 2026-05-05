# scripts/

Small project maintenance scripts.

## Fishing Catalog

`build_fish_catalog.py` is the only Hollan data script. It is the source of
truth for generating the committed 50-species fish catalog metadata:

```bash
python3 scripts/build_fish_catalog.py
```

It verifies that every `data/fish_images/<species_id>.png` exists, then writes
`data/fish_species.json`.

The AI-generated transparent PNG files are committed directly under
`data/fish_images/`. The frontend does not keep a second copy; `game-service`
serves the same files at `/fish_images/<species_id>.png`.

To add fish later:

1. Add the new fish metadata to `FISH` in `build_fish_catalog.py`.
2. Add a matching transparent PNG in `data/fish_images/`.
3. Run `python3 scripts/build_fish_catalog.py`.
4. Run `cd game-service && pipenv run pytest tests/test_fishing.py -v`.

## Coding Problem Datasets

`clean_leetcode_dataset.py` normalizes the first 100 non-premium rows from
`data/leetcode_dataset - lc.csv` into `data/leetcode_clean_100.json`:

```bash
python3 scripts/clean_leetcode_dataset.py
```

`build_judgeable_problem_dataset.py` builds the runtime problem dataset used by
game-service:

```bash
python3 scripts/build_judgeable_problem_dataset.py
```

Only rows with curated overrides are judgeable. The CSV by itself provides
descriptions and metadata, but not executable tests or revealable solutions.
