#!/usr/bin/env python3
"""Add a piece to the shop from a handful of photos.

    python3 tools/add_piece.py CMT-ND-014 "Blue Brushwork Tea Bowl No. 14" 85 small photos/*.jpg --made "c. 2021"

Arguments: SKU, title, price in dollars, shipping size (small, medium or large), then 1 to 6 photos.
--made is optional and free text ("2021", "c. 2021", "2019 to 2021"); leave it out if you do not know,
and no date is shown. A SKU like CMT-2018-014 says the piece was made in 2018; CMT-ND-014 means no date is known (ND, as in "n.d.").
The photos are resized (at most 1800px on the long edge, location data removed), a grid
thumbnail is made from the first one, and a new entry is added to content/shop.json. Open
that file to fill in dimensions, materials and a short description, then run `python3 build.py`.
Needs Pillow (pip install pillow).
"""
import argparse
import json
import os
import re
import sys

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP_PATH = os.path.join(ROOT, "content", "shop.json")


def save(src, dst, longest, quality):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")  # no EXIF is written back
    im.thumbnail((longest, longest), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
    return im.size


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sku")
    ap.add_argument("title")
    ap.add_argument("price", type=float)
    ap.add_argument("size")
    ap.add_argument("photos", nargs="+")
    ap.add_argument("--made", default="", help='when it was made, e.g. "c. 2021" (optional)')
    args = ap.parse_args()

    if not re.match(r"^CMT-(\d{4}|ND)-\d{3,5}$", args.sku):
        sys.exit("SKU must look like CMT-2018-014 (year made) or CMT-ND-014 (no date known)")
    shop = json.load(open(SHOP_PATH, encoding="utf8"))
    if args.size not in shop["shipping"]:
        sys.exit("size must be one of: " + ", ".join(shop["shipping"]))
    if any(i["sku"] == args.sku for i in shop["items"]):
        sys.exit(f"{args.sku} is already in the shop")
    if not 1 <= len(args.photos) <= 6:
        sys.exit("give 1 to 6 photos")

    folder = f"images/shop/{args.sku}"
    photos = []
    for n, src in enumerate(args.photos, 1):
        rel = f"{folder}/{n:02d}.jpg"
        w, h = save(src, os.path.join(ROOT, rel), 1800, 82)
        photos.append({"file": rel, "w": w, "h": h, "alt": f"{args.title}, photo {n}"})
    thumb_rel = f"{folder}/thumb.jpg"
    tw, th = save(args.photos[0], os.path.join(ROOT, thumb_rel), 640, 80)

    shop["items"].append({
        "sku": args.sku, "title": args.title, "made": args.made,
        "price": args.price, "status": "available", "size": args.size,
        "dimensions": "", "materials": "", "weight_oz": 0, "pickup": True, "series": "",
        "description": "", "buy_url": "",
        "thumb": {"file": thumb_rel, "w": tw, "h": th}, "photos": photos,
    })
    with open(SHOP_PATH, "w", encoding="utf8") as f:
        json.dump(shop, f, indent=2, ensure_ascii=False)
    print(f"Added {args.sku} with {len(photos)} photos. Next: fill in dimensions, materials and description in "
          "content/shop.json, paste the Stripe link into buy_url, then run python3 build.py")


if __name__ == "__main__":
    main()
