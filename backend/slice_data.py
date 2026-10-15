# Creates a smaller sample size from the original 500k rows dataset
# Only keeps recipes that have a photo in food.com's image sitemap
# (cached by backend/fetch_images.py), skipping duplicate ids

import csv, json, sys
from pathlib import Path

SAMPLE_SIZE = 5000

here = Path(__file__).resolve().parent
dataset_dir = here.parent / 'dataset'
src_path = dataset_dir / 'recipes_ingredients (1).csv'
dst_path = dataset_dir / 'recipes_sample.csv'
image_map_path = here / '.cache' / 'food_com_image_map.json'

csv.field_size_limit(sys.maxsize)
with_photo = set(json.loads(image_map_path.read_text()))
seen = set()

with open(src_path, newline='', encoding='utf-8') as src, \
     open(dst_path, 'w', newline='', encoding='utf-8') as dst:
    r, w = csv.reader(src), csv.writer(dst)
    header = next(r)
    w.writerow(header)
    id_col = header.index('id')
    for row in r:
        recipe_id = row[id_col]
        if recipe_id in with_photo and recipe_id not in seen:
            seen.add(recipe_id)
            w.writerow(row)
            if len(seen) == SAMPLE_SIZE:
                break

print(f"Wrote {len(seen)} recipes to {dst_path.name}")
