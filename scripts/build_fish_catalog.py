"""Build the committed CatCh fish catalog from curated PNG image assets.

This script is the source of truth for the playable fish dataset. It writes:

  data/fish_species.json

It expects project-owned transparent PNG assets to exist at:

  data/fish_images/<species_id>.png

This curated catalog and the committed PNG assets are what teammates can rely
on without external credentials or generated local artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DATA_IMAGES_DIR = DATA_DIR / "fish_images"
SPECIES_JSON_PATH = DATA_DIR / "fish_species.json"
IMAGE_EXT = ".png"

RARITY_BUCKET_PROBABILITY = {
    "common": 60.0,
    "uncommon": 25.0,
    "rare": 10.0,
    "epic": 4.0,
    "legendary": 1.0,
}

FISH = [
    {
        "id": "pond_minnow",
        "name": "Pond Minnow",
        "species": "Pimephales promelas",
        "rarity": "common",
        "sell_value": 5,
        "typical_size_cm": 8.0,
        "description": "A tiny schooling fish found near the surface of calm beginner ponds.",
    },
    {
        "id": "bluegill",
        "name": "Bluegill",
        "species": "Lepomis macrochirus",
        "rarity": "common",
        "sell_value": 6,
        "typical_size_cm": 18.0,
        "description": "A hardy pond fish with a blue cheek flash and an easygoing bite.",
    },
    {
        "id": "golden_shiner",
        "name": "Golden Shiner",
        "species": "Notemigonus crysoleucas",
        "rarity": "common",
        "sell_value": 6,
        "typical_size_cm": 12.0,
        "description": "A bright little fish that flickers like a coin in shallow water.",
    },
    {
        "id": "creek_chub",
        "name": "Creek Chub",
        "species": "Semotilus atromaculatus",
        "rarity": "common",
        "sell_value": 7,
        "typical_size_cm": 15.0,
        "description": "A quick creek fish that rewards steady practice and patient casts.",
    },
    {
        "id": "yellow_perch",
        "name": "Yellow Perch",
        "species": "Perca flavescens",
        "rarity": "common",
        "sell_value": 8,
        "typical_size_cm": 22.0,
        "description": "A striped freshwater fish often caught by careful first-time anglers.",
    },
    {
        "id": "sardine",
        "name": "Sardine",
        "species": "Sardina pilchardus",
        "rarity": "common",
        "sell_value": 5,
        "typical_size_cm": 16.0,
        "description": "A silver schooling fish that keeps the early collection growing fast.",
    },
    {
        "id": "anchovy",
        "name": "Anchovy",
        "species": "Engraulis encrasicolus",
        "rarity": "common",
        "sell_value": 5,
        "typical_size_cm": 13.0,
        "description": "A small ocean fish with a quick darting swim and modest token value.",
    },
    {
        "id": "black_sea_sprat",
        "name": "Black Sea Sprat",
        "species": "Sprattus sprattus",
        "rarity": "common",
        "sell_value": 6,
        "typical_size_cm": 11.0,
        "description": "A compact silver fish adapted from the raw fish image dataset.",
    },
    {
        "id": "horse_mackerel",
        "name": "Horse Mackerel",
        "species": "Trachurus trachurus",
        "rarity": "common",
        "sell_value": 9,
        "typical_size_cm": 25.0,
        "description": "A streamlined fish that appears often enough to anchor early trading.",
    },
    {
        "id": "redbelly_tilapia",
        "name": "Redbelly Tilapia",
        "species": "Coptodon zillii",
        "rarity": "common",
        "sell_value": 8,
        "typical_size_cm": 24.0,
        "description": "A sturdy warm-water fish with a soft red belly and dependable value.",
    },
    {
        "id": "mud_carp",
        "name": "Mud Carp",
        "species": "Cirrhinus molitorella",
        "rarity": "common",
        "sell_value": 9,
        "typical_size_cm": 28.0,
        "description": "A bottom-feeding pond fish that turns ordinary casts into progress.",
    },
    {
        "id": "rainbow_trout",
        "name": "Rainbow Trout",
        "species": "Oncorhynchus mykiss",
        "rarity": "uncommon",
        "sell_value": 20,
        "typical_size_cm": 35.0,
        "description": "A colorful trout with a bright lateral stripe and a lively fight.",
    },
    {
        "id": "red_mullet",
        "name": "Red Mullet",
        "species": "Mullus barbatus",
        "rarity": "uncommon",
        "sell_value": 22,
        "typical_size_cm": 28.0,
        "description": "A warm-toned reef fish with delicate fins and a higher market hint.",
    },
    {
        "id": "sea_bass",
        "name": "Sea Bass",
        "species": "Dicentrarchus labrax",
        "rarity": "uncommon",
        "sell_value": 24,
        "typical_size_cm": 45.0,
        "description": "A sleek coastal fish prized by kittens building a balanced aquarium.",
    },
    {
        "id": "koi",
        "name": "Koi",
        "species": "Cyprinus rubrofuscus",
        "rarity": "uncommon",
        "sell_value": 26,
        "typical_size_cm": 50.0,
        "description": "A decorative pond fish that feels at home in aquarium displays.",
    },
    {
        "id": "clownfish",
        "name": "Clownfish",
        "species": "Amphiprion ocellaris",
        "rarity": "uncommon",
        "sell_value": 23,
        "typical_size_cm": 9.0,
        "description": "A small reef fish with bold bands and playful aquarium energy.",
    },
    {
        "id": "flying_fish",
        "name": "Flying Fish",
        "species": "Exocoetus volitans",
        "rarity": "uncommon",
        "sell_value": 25,
        "typical_size_cm": 30.0,
        "description": "A gliding fish that seems to leap between coding streaks.",
    },
    {
        "id": "channel_catfish",
        "name": "Channel Catfish",
        "species": "Ictalurus punctatus",
        "rarity": "uncommon",
        "sell_value": 24,
        "typical_size_cm": 48.0,
        "description": "A whiskered river fish with steady value and a strong pull.",
    },
    {
        "id": "pufferfish",
        "name": "Pufferfish",
        "species": "Tetraodontidae",
        "rarity": "uncommon",
        "sell_value": 28,
        "typical_size_cm": 20.0,
        "description": "A round defensive fish that adds personality to any collection.",
    },
    {
        "id": "lionfish",
        "name": "Lionfish",
        "species": "Pterois volitans",
        "rarity": "rare",
        "sell_value": 60,
        "typical_size_cm": 33.0,
        "description": "A dramatic striped fish with fan-like fins and strong trade appeal.",
    },
    {
        "id": "anglerfish",
        "name": "Anglerfish",
        "species": "Lophiiformes",
        "rarity": "rare",
        "sell_value": 65,
        "typical_size_cm": 70.0,
        "description": "A deep-water fish with a glowing lure for patient problem solvers.",
    },
    {
        "id": "mandarinfish",
        "name": "Mandarinfish",
        "species": "Synchiropus splendidus",
        "rarity": "rare",
        "sell_value": 70,
        "typical_size_cm": 7.0,
        "description": "A tiny reef jewel covered in vivid patterns and collector demand.",
    },
    {
        "id": "electric_eel",
        "name": "Electric Eel",
        "species": "Electrophorus electricus",
        "rarity": "rare",
        "sell_value": 68,
        "typical_size_cm": 120.0,
        "description": "A shocking river catch that lights up aquarium progress.",
    },
    {
        "id": "mahi_mahi",
        "name": "Mahi-mahi",
        "species": "Coryphaena hippurus",
        "rarity": "rare",
        "sell_value": 72,
        "typical_size_cm": 100.0,
        "description": "A fast ocean fish with bright colors and a high suggested price.",
    },
    {
        "id": "lake_sturgeon",
        "name": "Lake Sturgeon",
        "species": "Acipenser fulvescens",
        "rarity": "rare",
        "sell_value": 75,
        "typical_size_cm": 150.0,
        "description": "An ancient armored fish that makes a collection feel established.",
    },
    {
        "id": "swordfish",
        "name": "Swordfish",
        "species": "Xiphias gladius",
        "rarity": "epic",
        "sell_value": 120,
        "typical_size_cm": 220.0,
        "description": "A powerful open-ocean fish marked by its long blade-like bill.",
    },
    {
        "id": "giant_grouper",
        "name": "Giant Grouper",
        "species": "Epinephelus lanceolatus",
        "rarity": "epic",
        "sell_value": 135,
        "typical_size_cm": 180.0,
        "description": "A massive reef fish whose size makes it a centerpiece catch.",
    },
    {
        "id": "arapaima",
        "name": "Arapaima",
        "species": "Arapaima gigas",
        "rarity": "epic",
        "sell_value": 140,
        "typical_size_cm": 200.0,
        "description": "A giant air-breathing river fish that rewards long-term play.",
    },
    {
        "id": "sailfish",
        "name": "Sailfish",
        "species": "Istiophorus platypterus",
        "rarity": "epic",
        "sell_value": 145,
        "typical_size_cm": 240.0,
        "description": "A swift fish with a huge dorsal sail and premium marketplace value.",
    },
    {
        "id": "bluefin_tuna",
        "name": "Bluefin Tuna",
        "species": "Thunnus thynnus",
        "rarity": "legendary",
        "sell_value": 250,
        "typical_size_cm": 250.0,
        "description": "A legendary migratory tuna and one of the most coveted catches.",
    },
    {
        "id": "coelacanth",
        "name": "Coelacanth",
        "species": "Latimeria chalumnae",
        "rarity": "legendary",
        "sell_value": 300,
        "typical_size_cm": 180.0,
        "description": "A living fossil whose appearance can reshape any aquarium ranking.",
    },
    {
        "id": "guppy",
        "name": "Guppy",
        "species": "Poecilia reticulata",
        "rarity": "common",
        "sell_value": 5,
        "typical_size_cm": 5.0,
        "description": "A small colorful fish that helps new kittens fill the first aquarium rows.",
    },
    {
        "id": "zebra_danio",
        "name": "Zebra Danio",
        "species": "Danio rerio",
        "rarity": "common",
        "sell_value": 6,
        "typical_size_cm": 4.0,
        "description": "A quick striped fish that appears often during steady practice sessions.",
    },
    {
        "id": "rosy_barb",
        "name": "Rosy Barb",
        "species": "Pethia conchonius",
        "rarity": "common",
        "sell_value": 7,
        "typical_size_cm": 10.0,
        "description": "A cheerful pinkish pond fish with reliable direct-sale value.",
    },
    {
        "id": "white_cloud_minnow",
        "name": "White Cloud Minnow",
        "species": "Tanichthys albonubes",
        "rarity": "common",
        "sell_value": 6,
        "typical_size_cm": 4.0,
        "description": "A cool-water minnow that brightens early aquarium progress.",
    },
    {
        "id": "silver_molly",
        "name": "Silver Molly",
        "species": "Poecilia sphenops",
        "rarity": "common",
        "sell_value": 7,
        "typical_size_cm": 9.0,
        "description": "A calm silver fish that makes repeated catches feel useful.",
    },
    {
        "id": "sunset_platy",
        "name": "Sunset Platy",
        "species": "Xiphophorus maculatus",
        "rarity": "common",
        "sell_value": 7,
        "typical_size_cm": 6.0,
        "description": "A warm-toned aquarium fish with approachable rarity and value.",
    },
    {
        "id": "neon_tetra",
        "name": "Neon Tetra",
        "species": "Paracheirodon innesi",
        "rarity": "common",
        "sell_value": 8,
        "typical_size_cm": 4.0,
        "description": "A glowing blue-red fish that makes the collection screen sparkle.",
    },
    {
        "id": "peppered_cory",
        "name": "Peppered Cory",
        "species": "Corydoras paleatus",
        "rarity": "common",
        "sell_value": 8,
        "typical_size_cm": 7.0,
        "description": "A gentle bottom-dweller that keeps the pond floor busy.",
    },
    {
        "id": "green_swordtail",
        "name": "Green Swordtail",
        "species": "Xiphophorus hellerii",
        "rarity": "common",
        "sell_value": 9,
        "typical_size_cm": 12.0,
        "description": "A common fish with a sharp tail silhouette and clean aquarium presence.",
    },
    {
        "id": "betta",
        "name": "Betta",
        "species": "Betta splendens",
        "rarity": "uncommon",
        "sell_value": 30,
        "typical_size_cm": 7.0,
        "description": "A flowing-finned fish that feels expressive in an interactive aquarium.",
    },
    {
        "id": "dwarf_gourami",
        "name": "Dwarf Gourami",
        "species": "Trichogaster lalius",
        "rarity": "uncommon",
        "sell_value": 28,
        "typical_size_cm": 9.0,
        "description": "A patterned fish with gentle movement and a mid-tier collection role.",
    },
    {
        "id": "glass_catfish",
        "name": "Glass Catfish",
        "species": "Kryptopterus vitreolus",
        "rarity": "uncommon",
        "sell_value": 32,
        "typical_size_cm": 10.0,
        "description": "A translucent fish that looks mysterious without becoming too rare.",
    },
    {
        "id": "cherry_barb",
        "name": "Cherry Barb",
        "species": "Puntius titteya",
        "rarity": "uncommon",
        "sell_value": 27,
        "typical_size_cm": 5.0,
        "description": "A small red fish that gives kittens another satisfying mid-tier catch.",
    },
    {
        "id": "opaline_gourami",
        "name": "Opaline Gourami",
        "species": "Trichopodus trichopterus",
        "rarity": "uncommon",
        "sell_value": 34,
        "typical_size_cm": 13.0,
        "description": "A blue patterned fish suited for aquarium display and modest trading.",
    },
    {
        "id": "discus",
        "name": "Discus",
        "species": "Symphysodon aequifasciatus",
        "rarity": "rare",
        "sell_value": 85,
        "typical_size_cm": 15.0,
        "description": "A round, elegant fish that rare collectors like to show off.",
    },
    {
        "id": "lined_seahorse",
        "name": "Lined Seahorse",
        "species": "Hippocampus erectus",
        "rarity": "rare",
        "sell_value": 90,
        "typical_size_cm": 14.0,
        "description": "A curled coastal fish that adds variety beyond ordinary swimming shapes.",
    },
    {
        "id": "green_moray",
        "name": "Green Moray",
        "species": "Gymnothorax funebris",
        "rarity": "rare",
        "sell_value": 95,
        "typical_size_cm": 150.0,
        "description": "A long reef predator that belongs in marketplace-level collections.",
    },
    {
        "id": "manta_ray",
        "name": "Manta Ray",
        "species": "Mobula birostris",
        "rarity": "epic",
        "sell_value": 160,
        "typical_size_cm": 450.0,
        "description": "A huge gliding ray that makes aquarium interaction feel more alive.",
    },
    {
        "id": "oarfish",
        "name": "Oarfish",
        "species": "Regalecus glesne",
        "rarity": "legendary",
        "sell_value": 320,
        "typical_size_cm": 600.0,
        "description": "A ribbon-like deep-sea legend that only the luckiest kittens catch.",
    },
]

def main() -> None:
    counts = {
        rarity: sum(1 for fish in FISH if fish["rarity"] == rarity)
        for rarity in RARITY_BUCKET_PROBABILITY
    }

    records = []
    missing_images = []
    for fish in FISH:
        rarity = fish["rarity"]
        probability = RARITY_BUCKET_PROBABILITY[rarity] / counts[rarity]
        image_url = f"/fish_images/{fish['id']}{IMAGE_EXT}"
        if not (DATA_IMAGES_DIR / f"{fish['id']}{IMAGE_EXT}").exists():
            missing_images.append(f"{fish['id']}{IMAGE_EXT}")
        record = {
            **fish,
            "species_id": fish["id"],
            "catch_probability": round(probability, 6),
            "image_url": image_url,
            "image_path": image_url,
            "animation_url": None,
            "base_price": fish["sell_value"],
            "sell_value_tokens": fish["sell_value"],
            "image_pool": [image_url],
            "marketplace_eligible": rarity in {"rare", "epic", "legendary"},
        }
        records.append(record)

    if missing_images:
        missing = "\n  ".join(missing_images)
        raise SystemExit(
            "Missing fish image assets in data/fish_images:\n  "
            f"{missing}\nGenerate or copy PNG assets before rebuilding."
        )

    SPECIES_JSON_PATH.write_text(
        json.dumps(records, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    total_probability = sum(item["catch_probability"] for item in records)
    print(f"Wrote {len(records)} fish to {SPECIES_JSON_PATH}")
    print(f"Total catch_probability: {total_probability:.6f}")
    print(f"Verified PNGs in {DATA_IMAGES_DIR}")


if __name__ == "__main__":
    main()
