#!/usr/bin/env python3
"""Generate the static site from content/site.json.

    python3 build.py

Writes index.html plus one folder per page (e.g. brittany/index.html) at the
repo root. Edit content/site.json (titles, text, image order, which section a
project lives in) and re-run; do not edit the generated HTML by hand.
"""
import html
import json
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = json.load(open(os.path.join(ROOT, "content", "site.json"), encoding="utf8"))
PROJECTS = SITE["projects"]
SITE_TITLE = SITE["title"]
DESCRIPTION = ("Charles Talbot is a visual artist and ceramicist based in New England: "
               "functional pottery, sculptural clay work and painting.")
NAV = [
    ("Recent Work", "recent-work/"),
    ("Archives", "archives/"),
]
NAV2 = [
    ("About", "about/"),
    ("Artist Statement", "artist-statement/"),
]
EXTERNAL = [
    ("Instagram", "https://www.instagram.com/blonderrr/"),
    ("Toshiko Takaezu Foundation", "https://www.toshikotakaezufoundation.org/"),
]
# Old Cargo URLs -> new URLs (for _redirects on Netlify / Cloudflare Pages)
OLD_PAGES = {"Recent-Work": "recent-work", "Archives": "archives", "About": "about",
             "Artist-Statement": "artist-statement"}
OLD_PROJECTS = {
    "Two-pots": "two-pots", "Brittany": "brittany", "Pots-2024": "pots-2024",
    "Cut-Bonnet-Vase": "cut-bonnet-vase", "Tea-pottery-1": "tea-bowls-blue-brushwork-2018",
    "Painted-Lyric-Bowls-S-S": "painted-lyric-bowls-s-s", "Tea-pottery": "tea-bowls-spattered-glazes-2018",
    "Small-Color-Paintings": "small-color-paintings",
    "Tall-Sprayed-Vase-and-Handled-Vase": "tall-sprayed-vase-and-handled-vase",
    "Turned-Vase-and-Blue-Globe-Bowl": "turned-vase-and-blue-globe-bowl",
    "Teabowls": "teabowls-2016", "Burned-Mountain-Vase": "burned-mountain-vase",
}

# Projects whose URL changed after launch: old slug -> new slug
RENAMED_PROJECTS = {
    "teabowls": "teabowls-2016",
    "tea-pottery": "tea-bowls-spattered-glazes-2018",
    "tea-pottery-1": "tea-bowls-blue-brushwork-2018",
}

e = html.escape

# Projects with more photos than this show a thumbnail grid instead of one long scroll.
# Each image then needs a "thumb" (and "tw"/"th") entry in site.json.
GRID_GALLERY_MIN = 12


def paragraphs(text, raw=False):
    out = []
    for block in [b for b in text.split("\n\n") if b.strip()]:
        body = block.strip() if raw else e(block.strip())
        out.append("<p>" + body.replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def layout(depth, title, body, active="", description=DESCRIPTION, og_image=None, body_class=""):
    root = "../" * depth
    nav = "".join(
        f'<li><a href="{root}{href}"{" aria-current=\"page\"" if href == active else ""}>{e(label)}</a></li>'
        for label, href in NAV)
    nav2 = "".join(
        f'<li><a href="{root}{href}"{" aria-current=\"page\"" if href == active else ""}>{e(label)}</a></li>'
        for label, href in NAV2)
    ext = "".join(f'<li><a href="{u}" target="_blank" rel="noopener">{e(l)}</a></li>' for l, u in EXTERNAL)
    full_title = SITE_TITLE if not title else f"{title} — {SITE_TITLE}"
    og = f'<meta property="og:image" content="{e(og_image)}">' if og_image else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="website">
{og}
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{root}favicon.ico" sizes="48x48">
<link rel="apple-touch-icon" href="{root}apple-touch-icon.png">
<link rel="stylesheet" href="{root}css/style.css">
</head>
<body class="{body_class}">
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <a class="site-title" href="{root}">Charles Talbot Studio</a>
  <button class="nav-toggle" aria-expanded="false" aria-controls="site-nav">Menu</button>
  <nav id="site-nav" aria-label="Main">
    <ul class="nav-main">{nav}</ul>
    <ul class="nav-sub">{nav2}{ext}</ul>
  </nav>
</header>
<main id="main">
{body}
</main>
<script src="{root}js/main.js" defer></script>
</body>
</html>
"""


def grid(projects, depth):
    root = "../" * depth
    items = []
    for p in projects:
        c = p["cover"]
        items.append(
            f'<a class="tile" href="{root}{p["slug"]}/">'
            f'<img src="{root}{c["file"]}" width="{c["w"]}" height="{c["h"]}" '
            f'alt="{e(p["title"])}" loading="lazy" decoding="async">'
            f'<span class="tile-title">{e(p["title"])}</span></a>')
    return '<div class="grid">' + "\n".join(items) + "</div>"


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full) or ROOT, exist_ok=True)
    with open(full, "w", encoding="utf8") as f:
        f.write(content)


def main():
    # Clean previously generated folders
    for p in PROJECTS:
        shutil.rmtree(os.path.join(ROOT, p["slug"]), ignore_errors=True)
    for _, href in NAV + NAV2:
        shutil.rmtree(os.path.join(ROOT, href.strip("/")), ignore_errors=True)

    og = PROJECTS[0]["cover"]["file"]
    write("index.html", layout(0, "", grid(PROJECTS, 0), og_image=og, body_class="home"))

    for label, href in NAV:
        key = {"recent-work/": "recent", "archives/": "archives"}[href]
        subset = [p for p in PROJECTS if p["section"] == key]
        body = f"<h1 class=\"page-title\">{e(label)}</h1>\n" + grid(subset, 1)
        write(href + "index.html", layout(1, label, body, active=href))

    for key, href in (("about", "about/"), ("artist-statement", "artist-statement/")):
        page = SITE["pages"][key]
        label = dict((v, k) for k, v in NAV2)[href]
        body = f'<article class="prose"><h1 class="page-title">{e(label)}</h1>\n{paragraphs(page["body"], raw=True)}</article>'
        write(href + "index.html", layout(1, label, body, active=href))

    for i, p in enumerate(PROJECTS):
        big = len(p["images"]) > GRID_GALLERY_MIN
        figs = "\n".join(
            f'<figure><a class="zoom" href="../{im["file"]}">'
            f'<img src="../{im.get("thumb", im["file"]) if big else im["file"]}" '
            f'width="{im.get("tw", im["w"]) if big else im["w"]}" '
            f'height="{im.get("th", im["h"]) if big else im["h"]}" alt="{e(im["alt"])}" '
            f'loading="{"eager" if n == 0 else "lazy"}" decoding="async"></a></figure>'
            for n, im in enumerate(p["images"]))
        meta = []
        if p["date"]:
            meta.append(e(p["date"]))
        d = p.get("details", {})
        if d.get("title"):
            meta.append(f'“{e(d["title"])}”')
        if d.get("materials"):
            meta.append(e(d["materials"]))
        if d.get("dimensions"):
            meta.append(e(d["dimensions"]) + " in.")
        meta_html = f'<p class="meta">{" · ".join(meta)}</p>' if meta else ""
        desc = paragraphs(p["description"]) if p["description"] else ""
        prev_p, next_p = PROJECTS[i - 1], PROJECTS[(i + 1) % len(PROJECTS)]
        pager = (f'<nav class="pager" aria-label="Projects">'
                 f'<a href="../{prev_p["slug"]}/" rel="prev">← {e(prev_p["title"])}</a>'
                 f'<a href="../">All work</a>'
                 f'<a href="../{next_p["slug"]}/" rel="next">{e(next_p["title"])} →</a></nav>')
        body = (f'<article class="project"><h1 class="page-title">{e(p["title"])}</h1>{meta_html}{desc}'
                f'<div class="gallery{" gallery-grid" if big else ""}">{figs}</div></article>{pager}')
        write(p["slug"] + "/index.html",
              layout(1, p["title"], body, description=f'{p["title"]} — work by Charles Talbot.',
                     og_image=p["cover"]["file"]))

    redirects = [f"/{old} /{new}/ 301" for old, new in {**OLD_PAGES, **OLD_PROJECTS}.items()]
    for old, new in RENAMED_PROJECTS.items():  # earlier URLs of this site, with and without trailing slash
        redirects += [f"/{old} /{new}/ 301", f"/{old}/ /{new}/ 301"]
    write("_redirects", "\n".join(redirects) + "\n")
    print(f"Built {len(PROJECTS)} project pages + {len(NAV) + len(NAV2) + 1} others")


if __name__ == "__main__":
    main()
