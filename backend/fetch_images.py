"""Fill in recipe.image from food.com's image sitemap.

food.com/robots.txt points crawlers at https://www.food.com/sitemap.xml, an
index of ~24 gzipped sub-sitemaps. Each <url> entry pairs a recipe URL (id at
the end of the slug) with its photo (<image:loc>). Reading those files gives an
id -> photo URL map for the whole site in a couple dozen requests, instead of
one request per recipe page (which gets the IP blocked).

The map is cached to .cache/food_com_image_map.json, so later runs make no
requests at all. Recipes missing from the map have no photo and keep image = null,
which the frontend shows as a placeholder.

Usage:
    python fetch_images.py            # use the cache if present
    python fetch_images.py --refresh  # re-download the sitemaps
"""
import argparse
import gzip
import json
import re
import time
from pathlib import Path

import httpx

from db import connect

SITEMAP_INDEX_URL = "https://www.food.com/sitemap.xml"
USER_AGENT = "MicroBites/1.0 (personal project; sitemap lookup)"
BETWEEN_FILES_SECONDS = 0.5
CACHE_PATH = Path(__file__).resolve().parent / ".cache" / "food_com_image_map.json"

SUB_SITEMAP_RE = re.compile(r"<loc>(https://www\.food\.com/sitemap-\d+\.xml\.gz)</loc>")
RECIPE_ID_RE = re.compile(r"/recipe/[a-z0-9-]+-(\d+)<")
IMAGE_LOC_RE = re.compile(r"<image:loc>([^<]+)</image:loc>")


def parse_sitemap(xml_text):
    found = {}
    for block in xml_text.split("<url>")[1:]:
        id_match = RECIPE_ID_RE.search(block)
        image_match = IMAGE_LOC_RE.search(block)
        if id_match and image_match:
            found[int(id_match.group(1))] = image_match.group(1)
    return found


def download_image_map():
    image_map = {}
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        response = client.get(SITEMAP_INDEX_URL)
        response.raise_for_status()
        sub_sitemaps = SUB_SITEMAP_RE.findall(response.text)
        if not sub_sitemaps:
            raise RuntimeError(f"No sub-sitemaps found at {SITEMAP_INDEX_URL}")

        for i, url in enumerate(sub_sitemaps, 1):
            try:
                response = client.get(url)
                response.raise_for_status()
                image_map.update(parse_sitemap(gzip.decompress(response.content).decode("utf-8", "replace")))
            except (httpx.HTTPError, OSError) as exc:
                print(f"  {url} failed ({exc}), skipping")
            print(f"  {i}/{len(sub_sitemaps)} sitemaps read, {len(image_map)} photos so far")
            time.sleep(BETWEEN_FILES_SECONDS)
    return image_map


def load_image_map(refresh):
    if not refresh and CACHE_PATH.exists():
        print(f"Using cached image map at {CACHE_PATH}")
        return {int(k): v for k, v in json.loads(CACHE_PATH.read_text()).items()}

    image_map = download_image_map()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(image_map))
    return image_map


def resized(url):
    # Sitemap URLs point at the full-size original; ask the image CDN for a 640px rendition
    return url.replace("/upload/v1/", "/upload/q_80,fl_progressive,w_640,c_scale/v1/", 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="re-download the sitemaps")
    args = parser.parse_args()

    image_map = load_image_map(args.refresh)

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select id from recipe")
    ids = [row[0] for row in cursor.fetchall()]
    updates = [(resized(image_map[i]) if i in image_map else None, i) for i in ids]
    cursor.executemany("update recipe set image = %s where id = %s", updates)
    conn.commit()
    conn.close()

    found = sum(image is not None for image, _ in updates)
    print(f"{found} of {len(ids)} recipes have a photo")


if __name__ == "__main__":
    main()
