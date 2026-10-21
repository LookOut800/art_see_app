#!/usr/bin/env python3
"""Add a piece to the shop from a handful of photos.

    python3 tools/add_piece.py CMT-ND-014 "Blue Brushwork Tea Bowl No. 14" 85 small photos/*.jpg --made "c. 2021"

Arguments: SKU, title, price in dollars, shipping size (small, medium or large), then 1 to 6 photos.
--made is optional and free text ("2021", "c. 2021", "2019 to 2021"); leave it out if you do not know,
and no date is shown. A SKU like CMT-2018-014 says the piece was made in 2018; CMT-ND-014 means no date is known (ND, as in "n.d.").
The photos are cleaned up by tools/process_photos.py (--kind pot, the default: white balance
and exposure from the backdrop, cropped to the piece; --kind painting: canvas squared and
cropped; --kind none: only resized), at most 1800px on the long edge with location data
removed. A grid thumbnail is made from the first one, a before/after sheet is written to
inbox/sheets/<SKU>.jpg, and a new entry is added to content/shop.json. Check the sheet, then
fill in dimensions, materials and a short description and run `python3 build.py`.
Needs the packages in tools/requirements.txt.
"""
import argparse
import json
import os
import re
import sys

from PIL import Image

import process_photos

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP_PATH = os.path.join(ROOT, "content", "shop.json")


def thumbnail(im, dst, longest=640, quality=80):
    im = im.copy()
    im.thumbnail((longest, longest), Image.LANCZOS)
    return process_photos.save(im, dst, quality)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sku")
    ap.add_argument("title")
    ap.add_argument("price", type=float)
    ap.add_argument("size")
    ap.add_argument("photos", nargs="+")
    ap.add_argument("--made", default="", help='when it was made, e.g. "c. 2021" (optional)')
    ap.add_argument("--kind", choices=("pot", "painting", "none"), default="pot",
                    help="how to clean up the photos (see tools/process_photos.py)")
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
    photos, rows = [], []
    for n, src in enumerate(args.photos, 1):
        rel = f"{folder}/{n:02d}.jpg"
        im, before, notes = process_photos.process(src, args.kind)
        w, h = process_photos.save(im, os.path.join(ROOT, rel))
        photos.append({"file": rel, "w": w, "h": h, "alt": f"{args.title}, photo {n}"})
        rows.append((f"{os.path.basename(src)} -> {rel}", before, im, notes))
        if n == 1:
            thumb_rel = f"{folder}/thumb.jpg"
            tw, th = thumbnail(im, os.path.join(ROOT, thumb_rel))
    sheet = os.path.join(ROOT, "inbox", "sheets", f"{args.sku}.jpg")
    os.makedirs(os.path.dirname(sheet), exist_ok=True)
    process_photos.contact_sheet(rows, sheet)

    shop["items"].append({
        "sku": args.sku, "title": args.title, "made": args.made,
        "price": args.price, "status": "available", "size": args.size,
        "dimensions": "", "materials": "", "weight_oz": 0, "pickup": True, "series": "",
        "description": "", "buy_url": "",
        "thumb": {"file": thumb_rel, "w": tw, "h": th}, "photos": photos,
    })
    with open(SHOP_PATH, "w", encoding="utf8") as f:
        json.dump(shop, f, indent=2, ensure_ascii=False)
    print(f"Added {args.sku} with {len(photos)} photos. Check the before/after sheet {os.path.relpath(sheet, ROOT)}, then fill in dimensions, materials and description in "
          "content/shop.json, paste the Stripe link into buy_url, then run python3 build.py")


if __name__ == "__main__":
    main()
