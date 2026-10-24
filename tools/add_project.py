#!/usr/bin/env python3
"""Add a project (a page of photos) to the site, or replace one, from a folder of photos.

    .venv/bin/python tools/add_project.py sculpture-2022 "Sculpture, 2022" 2022 recent inbox/new/*.HEIC
    .venv/bin/python tools/add_project.py paintings-2022 "Paintings, 2022" 2022 recent --kind painting photos/*

Arguments: slug (the URL, e.g. sculpture-2022), title, date shown on the page, section (recent,
archives or none), then the photos in the order they should appear.

New photos are cleaned up by tools/process_photos.py (--kind pot by default) and written to
images/<slug>/01.jpg, 02.jpg, ... Photos already on the site (anything under images/) are
copied as they are, so earlier projects can be merged into a new one without editing them twice.
A 4:5 cover is cut from --cover-from (default: the first photo), and grid thumbnails are made
when the project has more photos than build.py shows in one column. A before/after sheet is
written to inbox/sheets/<slug>.jpg. Each photo's entry in site.json keeps the name of the
original ("source") and the date it was taken ("taken"); neither is shown on the site. The project goes first on the home page unless --after
names the slug it should follow. Check the sheet, then run python3 build.py.
"""
import argparse
import json
import os
import shutil
import sys

from PIL import Image, ImageOps

import process_photos

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_PATH = os.path.join(ROOT, "content", "site.json")
GRID_GALLERY_MIN = 12  # same as build.py
COVER = (600, 750)


def thumbnail(im, dst, longest=640, quality=80):
    im = im.copy()
    im.thumbnail((longest, longest), Image.LANCZOS)
    return process_photos.save(im, dst, quality)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("title")
    ap.add_argument("date")
    ap.add_argument("section", choices=("recent", "archives", "none"))
    ap.add_argument("photos", nargs="+")
    ap.add_argument("--kind", choices=("pot", "painting", "drawing", "none"), default="pot",
                    help="how to clean up new photos (see tools/process_photos.py)")
    ap.add_argument("--cover-from", type=int, default=1, help="number of the photo to cut the cover from")
    ap.add_argument("--description", default="")
    ap.add_argument("--after", help="slug of the project this one follows on the home page")
    args = ap.parse_args()

    site = json.load(open(SITE_PATH, encoding="utf8"))
    projects = site["projects"]
    old = next((p for p in projects if p["slug"] == args.slug), None)
    if args.after and not any(p["slug"] == args.after for p in projects):
        sys.exit(f"no project {args.after}")

    folder = f"images/{args.slug}"
    staging = os.path.join(ROOT, folder + ".new")  # sources may live in the folder being replaced
    shutil.rmtree(staging, ignore_errors=True)
    big = len(args.photos) > GRID_GALLERY_MIN
    on_site = {im["file"]: im for p in projects for im in p["images"]}
    images, rows, cover_src = [], [], None
    for n, src in enumerate(args.photos, 1):
        name = f"{n:02d}.jpg"
        copied = None
        if os.path.abspath(src).startswith(os.path.join(ROOT, "images") + os.sep):
            copied = on_site.get(os.path.relpath(os.path.abspath(src), ROOT).replace(os.sep, "/"), {})
            im = Image.open(src).convert("RGB")
            os.makedirs(staging, exist_ok=True)
            shutil.copyfile(src, os.path.join(staging, name))
            w, h = im.size
            rows.append((f"{os.path.relpath(src, ROOT)} -> {folder}/{name}", im, im, ["already on the site: copied"]))
        else:
            im, before, notes = process_photos.process(src, args.kind)
            w, h = process_photos.save(im, os.path.join(staging, name))
            rows.append((f"{os.path.basename(src)} -> {folder}/{name}", before, im, notes))
        entry = {"file": f"{folder}/{name}", "w": w, "h": h, "alt": f"{args.title}, photo {n}"}
        if copied is not None:  # keep what was known about it on its earlier page
            entry.update({k: copied[k] for k in ("source", "taken") if copied.get(k)})
        else:
            entry["source"], entry["taken"] = os.path.basename(src), process_photos.date_taken(src)
        if big:
            entry["tw"], entry["th"] = thumbnail(im, os.path.join(staging, "thumbs", name))
            entry["thumb"] = f"{folder}/thumbs/{name}"
        images.append(entry)
        if n == args.cover_from:
            cover_src = im
    if cover_src is None:
        sys.exit(f"--cover-from {args.cover_from}: there are only {len(args.photos)} photos")
    cover = ImageOps.fit(cover_src, COVER, Image.LANCZOS)
    process_photos.save(cover, os.path.join(staging, "cover.jpg"), quality=80)

    shutil.rmtree(os.path.join(ROOT, folder), ignore_errors=True)
    os.rename(staging, os.path.join(ROOT, folder))
    sheet = os.path.join(ROOT, "inbox", "sheets", f"{args.slug}.jpg")
    os.makedirs(os.path.dirname(sheet), exist_ok=True)
    process_photos.contact_sheet(rows, sheet)

    project = {
        "slug": args.slug, "title": args.title, "section": args.section, "date": args.date,
        "cover": {"file": f"{folder}/cover.jpg", "w": COVER[0], "h": COVER[1]},
        "images": images,
        "description": args.description or (old or {}).get("description", ""),
        "details": (old or {}).get("details", {}),
    }
    if old:
        projects.remove(old)
    at = 0 if not args.after else next(i for i, p in enumerate(projects) if p["slug"] == args.after) + 1
    projects.insert(at, project)
    with open(SITE_PATH, "w", encoding="utf8") as f:
        json.dump(site, f, indent=2, ensure_ascii=False)
    print(f"{'Replaced' if old else 'Added'} {args.slug} with {len(images)} photos. "
          f"Check {os.path.relpath(sheet, ROOT)}, then run python3 build.py")


if __name__ == "__main__":
    main()
