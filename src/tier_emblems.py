"""
Small ranked tier emblems for the Ranking tab:

    web/public/data/tiers/<Tier>.png   Challenger, Grandmaster, Master

The source is Riot's official ranked emblems zip from the developer docs
(developer.riotgames.com/docs/lol), about 64 MB, downloaded once into
data/ranked_emblems/. Each emblem is 1000 x 1000 with empty space above and
below, so it is cropped to the visible part and shrunk to 96 px wide (sharp
when shown at about 30 px on high-DPI screens).

build_site.py calls make_tier_emblems(); emblems that already exist are skipped.
"""

import io
import zipfile
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ZIP_URL = "https://static.developer.riotgames.com/docs/lol/ranked-emblems-latest.zip"
ZIP_PATH = ROOT / "data" / "ranked_emblems" / "emblems.zip"
TIERS = ["Challenger", "Grandmaster", "Master"]
WIDTH = 96


def download_zip():
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading Riot's ranked emblems (about 64 MB, once)...")
    response = requests.get(ZIP_URL, timeout=120)
    response.raise_for_status()
    ZIP_PATH.write_bytes(response.content)


def make_tier_emblems(out_dir):
    out_dir = Path(out_dir)
    missing = [t for t in TIERS if not (out_dir / f"{t}.png").exists()]
    if not missing:
        return
    if not ZIP_PATH.exists():
        download_zip()
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as z:
        for tier in missing:
            image = Image.open(io.BytesIO(z.read(f"Ranked Emblems Latest/Rank={tier}.png")))
            # getbbox() is the smallest box around the non-transparent pixels
            image = image.crop(image.getbbox())
            height = round(image.height * WIDTH / image.width)
            image.resize((WIDTH, height), Image.LANCZOS).save(out_dir / f"{tier}.png", optimize=True)
            print(f"Wrote {tier}.png ({WIDTH} x {height})")


if __name__ == "__main__":
    make_tier_emblems(ROOT / "web" / "public" / "data" / "tiers")
