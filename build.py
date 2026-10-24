#!/usr/bin/env python3
"""Generate the static site from content/site.json.

    python3 build.py

Writes index.html plus one folder per page (e.g. drawings/index.html) at the
repo root. Edit content/site.json (titles, text, image order, which section a
project lives in) and re-run; do not edit the generated HTML by hand.
"""
import html
import json
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = json.load(open(os.path.join(ROOT, "content", "site.json"), encoding="utf8"))
SITE_TITLE = SITE["title"]
THEMES = SITE["themes"]   # groupings of pieces that can span years, each with a short text
VIEWS = SITE["views"]     # photo pages of work in a place (a show, the house), not single pieces
DESCRIPTION = ("Charles Talbot is a visual artist and ceramicist based in New England: "
               "functional pottery, sculptural clay work and painting.")
NAV = [
    ("Work", "work/"),
    ("Themes", "themes/"),
]
NAV2 = [
    ("About", "about/"),
    ("Artist Statement", "artist-statement/"),
]
EXTERNAL = [
    ("Instagram", "https://www.instagram.com/blonderrr/"),
    ("Toshiko Takaezu Foundation", "https://www.toshikotakaezufoundation.org/"),
]
# The wall is shown one kind of work at a time: /work/<slug>/ shows pieces whose kind is in the set.
# The first is the default, shown on the home page and at /work/; /work/all/ shows everything.
KINDS = [("pottery", "Pottery", {"pottery"}), ("sculpture", "Sculpture", {"sculpture"}),
         ("painting", "Painting", {"painting"}), ("drawing", "Drawing", {"drawing"})]
KIND_LABEL = {"sculpture": "Sculpture", "pottery": "Pottery", "painting": "Painting", "drawing": "Drawing"}

# Earlier URLs (the old Cargo site, then project pages of this one) -> where that work is now.
# Written to _redirects for Cloudflare.
_OLD = {
    "two-pots": "/work/2016-03/", "pots-2024": "/themes/towers/", "cut-bonnet-vase": "/work/nd-02/",
    "tea-bowls-blue-brushwork-2018": "/themes/blue-brushwork/", "painted-lyric-bowls-s-s": "/work/pottery/",
    "tea-bowls-spattered-glazes-2018": "/themes/tea-bowls/", "small-color-paintings": "/work/painting/",
    "tall-sprayed-vase-and-handled-vase": "/work/2016-01/", "turned-vase-and-blue-globe-bowl": "/work/2017-01/",
    "teabowls-2016": "/themes/tea-bowls/", "burned-mountain-vase": "/work/nd-01/",
    "brittany": "/brittany-gallery-show-2022/", "recent-work": "/work/", "archives": "/work/",
    "teabowls": "/themes/tea-bowls/", "tea-pottery": "/themes/tea-bowls/", "tea-pottery-1": "/themes/blue-brushwork/",
}
REDIRECTS = {f"/{old}": new for old, new in _OLD.items()}
REDIRECTS.update({f"/{old}/": new for old, new in _OLD.items()})
REDIRECTS.update({"/Recent-Work": "/work/", "/Archives": "/work/", "/About": "/about/",
                  "/Artist-Statement": "/artist-statement/", "/Two-pots": _OLD["two-pots"],
                  "/Brittany": _OLD["brittany"], "/Pots-2024": _OLD["pots-2024"],
                  "/Cut-Bonnet-Vase": _OLD["cut-bonnet-vase"], "/Tea-pottery-1": _OLD["tea-pottery-1"],
                  "/Painted-Lyric-Bowls-S-S": _OLD["painted-lyric-bowls-s-s"], "/Tea-pottery": _OLD["tea-pottery"],
                  "/Small-Color-Paintings": _OLD["small-color-paintings"],
                  "/Tall-Sprayed-Vase-and-Handled-Vase": _OLD["tall-sprayed-vase-and-handled-vase"],
                  "/Turned-Vase-and-Blue-Globe-Bowl": _OLD["turned-vase-and-blue-globe-bowl"],
                  "/Teabowls": _OLD["teabowls"], "/Burned-Mountain-Vase": _OLD["burned-mountain-vase"]})

e = html.escape

# Pages with more photos than this show a thumbnail grid instead of one long scroll.
GRID_GALLERY_MIN = 12
WALL_THUMB = 480  # px, long edge of the wall thumbnails in images/work/

SITE_URL = "https://charlestalbotart.com"

# Shop: content/shop.json. The shop is hidden (no pages, no nav link) until "enabled" is true.
# SHOP_PREVIEW=1 python3 build.py builds it anyway, for local previews with sample pieces.
SHOP_PATH = os.path.join(ROOT, "content", "shop.json")
SHOP = json.load(open(SHOP_PATH, encoding="utf8")) if os.path.exists(SHOP_PATH) else {"enabled": False, "items": []}
SHOP_PREVIEW = bool(os.environ.get("SHOP_PREVIEW"))
SHOP_ON = bool(SHOP.get("enabled")) or SHOP_PREVIEW
SHOP_NAV = [("Shop", "shop/")] if SHOP_ON else []
SKU_RE = r"^CMT-(\d{4}|ND)-\d{3,5}$"  # CMT-2018-014 (year made) or CMT-ND-014 (no date known)
STATUSES = ("available", "reserved", "sold")


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
        for label, href in NAV + SHOP_NAV)
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


def load_pieces():
    """content/pieces.csv: one row per piece, newest first on the wall. The first photo is the one
    shown on the wall. Year, title, materials and dimensions are optional; an empty one is not shown."""
    import csv
    rows = list(csv.DictReader(open(os.path.join(ROOT, "content", "pieces.csv"), encoding="utf8", newline="")))
    themes = {t["slug"] for t in THEMES}
    problems, seen, seen_photos = [], set(), set()
    for r in rows:
        r["photos"] = r["photos"].split()
        r["themes"] = r["themes"].split()
        pid = r["id"]
        if not pid or pid in seen:
            problems.append(f"{pid or '(no id)'}: id missing or used twice")
        seen.add(pid)
        if r["kind"] not in KIND_LABEL:
            problems.append(f"{pid}: kind must be one of {', '.join(KIND_LABEL)}")
        for t in r["themes"]:
            if t not in themes:
                problems.append(f"{pid}: no theme {t} in content/site.json")
        if not r["photos"]:
            problems.append(f"{pid}: needs at least one photo")
        for f in r["photos"]:
            if not os.path.exists(os.path.join(ROOT, f)):
                problems.append(f"{pid}: {f} does not exist")
            if f in seen_photos:
                problems.append(f"{pid}: {f} is already used by another piece")
            seen_photos.add(f)
    if problems:
        raise SystemExit("content/pieces.csv problems:\n  " + "\n  ".join(problems))
    rows.sort(key=lambda r: r["year"] or "0", reverse=True)  # stable: keeps the file's order within a year
    return rows


def size_of(path, _cache={}):
    if path not in _cache:
        from PIL import Image
        _cache[path] = Image.open(os.path.join(ROOT, path)).size
    return _cache[path]


def wall_thumb(piece):
    """images/work/<id>.jpg from the piece's first photo, remade when that photo changes."""
    src = piece["photos"][0]
    rel = f'images/work/{piece["id"]}.jpg'
    full, src_full = os.path.join(ROOT, rel), os.path.join(ROOT, src)
    if not os.path.exists(full) or os.path.getmtime(full) < os.path.getmtime(src_full):
        from PIL import Image
        im = Image.open(src_full).convert("RGB")
        im.thumbnail((WALL_THUMB, WALL_THUMB), Image.LANCZOS)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        im.save(full, "JPEG", quality=80, optimize=True, progressive=True)
    return rel


def piece_name(p):
    """The title, or what it is and when ("Sculpture, 2023") for the many pieces without one."""
    if p["title"]:
        return p["title"]
    return KIND_LABEL[p["kind"]] + (f', {p["year"]}' if p["year"] else "")


def piece_tile(p, root):
    t = p["thumb"]
    w, h = size_of(t)
    return (f'<a class="tile" href="{root}work/{p["id"]}/">'
            f'<img src="{root}{t}" width="{w}" height="{h}" alt="{e(piece_name(p))}" loading="lazy" decoding="async">'
            f'<span class="tile-title">{e(piece_name(p))}</span></a>')


def wall(pieces, root, by_year=True):
    """Every piece, newest first, in one section per year (with a row of year links on top)."""
    if not by_year:
        return '<div class="grid">' + "\n".join(piece_tile(p, root) for p in pieces) + "</div>"
    years = []
    for p in pieces:
        y = p["year"] or "Undated"
        if not years or years[-1][0] != y:
            years.append((y, []))
        years[-1][1].append(p)
    jump = '<nav class="years" aria-label="Years">' + "".join(
        f'<a href="#y{y}">{e(y)}</a>' for y, _ in years) + "</nav>"
    return jump + "\n".join(
        f'<section class="year" id="y{y}"><h2 class="year-h">{e(y)}</h2><div class="grid">'
        + "\n".join(piece_tile(p, root) for p in ps) + "</div></section>" for y, ps in years)


def filters(root, active):
    links = [(label, f"work/{slug}/") for slug, label, _ in KINDS] + [("All", "work/all/")]
    return '<nav class="filters" aria-label="Kinds of work">' + "".join(
        f'<a href="{root}{href}"{" aria-current=\"page\"" if href == active else ""}>{e(label)}</a>'
        for label, href in links) + "</nav>"


def slider(images, root, alt):
    """A piece's photos side by side, one at a time with arrows and small previews (on a phone they
    stack, as on other pages). js/main.js wires up the buttons; without it the row still scrolls."""
    figs = "\n".join(
        f'<figure><a class="zoom" href="{root}{f}"><img src="{root}{f}" width="{w}" height="{h}" '
        f'alt="{e(alt)}, photo {n + 1}" loading="{"eager" if n < 2 else "lazy"}" decoding="async"></a></figure>'
        for n, (f, w, h) in enumerate(images))
    if len(images) == 1:
        return f'<div class="gallery">{figs}</div>'
    thumbs = "".join(
        f'<button type="button" data-i="{n}" aria-label="Photo {n + 1}"><img src="{root}{f}" alt="" loading="lazy"></button>'
        for n, (f, w, h) in enumerate(images))
    return (f'<div class="slider"><div class="gallery gallery-slider" tabindex="0" aria-label="Photos">{figs}</div>'
            f'<div class="slider-ui"><button type="button" class="sl-prev" aria-label="Previous photo">‹</button>'
            f'<span class="sl-count">1 / {len(images)}</span>'
            f'<button type="button" class="sl-next" aria-label="Next photo">›</button></div>'
            f'<div class="slider-thumbs">{thumbs}</div></div>')


def gallery(images, root, alt):
    """images: (file, w, h). Big sets show as a grid of the wall thumbnails' size."""
    big = len(images) > GRID_GALLERY_MIN
    figs = "\n".join(
        f'<figure><a class="zoom" href="{root}{f}"><img src="{root}{f}" width="{w}" height="{h}" '
        f'alt="{e(alt)}, photo {n + 1}" loading="{"eager" if n == 0 else "lazy"}" decoding="async"></a></figure>'
        for n, (f, w, h) in enumerate(images))
    return f'<div class="gallery{" gallery-grid" if big else ""}">{figs}</div>'


def piece_page(p, prev_p, next_p):
    root = "../../"
    name = piece_name(p)
    meta = [x for x in (p["year"] and p["title"] and p["year"], KIND_LABEL[p["kind"]] if p["title"] else "",
                        p["materials"], p["dimensions"]) if x]
    meta_html = f'<p class="meta">{" · ".join(e(m) for m in meta)}</p>' if meta else ""
    themes = [t for t in THEMES if t["slug"] in p["themes"]]
    theme_html = ('<p class="meta">Part of ' + ", ".join(
        f'<a href="{root}themes/{t["slug"]}/">{e(t["title"])}</a>' for t in themes) + "</p>") if themes else ""
    notes = paragraphs(p["notes"]) if p["notes"] else ""
    images = [(f, *size_of(f)) for f in p["photos"]]
    pager = (f'<nav class="pager" aria-label="Pieces">'
             f'<a href="{root}work/{prev_p["id"]}/" rel="prev">← Previous</a>'
             f'<a href="{root}work/">All work</a>'
             f'<a href="{root}work/{next_p["id"]}/" rel="next">Next →</a></nav>')
    body = (f'<article class="project"><h1 class="page-title">{e(name)}</h1>{meta_html}{theme_html}{notes}'
            f'{slider(images, root, name)}</article>{pager}')
    write(f'work/{p["id"]}/index.html', layout(2, name, body, active="work/",
          description=f"{name} — work by Charles Talbot.", og_image=p["photos"][0]))


def money(v):
    return f"${v:,.0f}" if float(v).is_integer() else f"${v:,.2f}"


def sku_year(sku):
    """The year inside a SKU like CMT-2018-014 (the year the piece was made), or "" for CMT-ND-014."""
    import re
    m = re.match(r"^CMT-(\d{4})-\d+$", sku)
    return m.group(1) if m else ""


def shop_check():
    """Stop a half-finished shop from being published. Always validates the data shape."""
    import re
    seen, problems = set(), []
    for it in SHOP["items"]:
        if not re.match(SKU_RE, it["sku"]):
            problems.append(f'{it["sku"]}: SKU must look like CMT-2018-014 or CMT-ND-014')
        yr = sku_year(it["sku"])
        if yr and it.get("made") and re.search(r"\b(19|20)\d{2}\b", it["made"]) and yr not in it["made"]:
            problems.append(f'{it["sku"]}: the year in the SKU ({yr}) does not match made ("{it["made"]}")')
        if it["sku"] in seen:
            problems.append(f'{it["sku"]}: duplicate SKU')
        seen.add(it["sku"])
        if it["status"] not in STATUSES:
            problems.append(f'{it["sku"]}: status must be one of {", ".join(STATUSES)}')
        if it["size"] not in SHOP["shipping"]:
            problems.append(f'{it["sku"]}: size must be one of {", ".join(SHOP["shipping"])}')
        if not it["photos"]:
            problems.append(f'{it["sku"]}: needs at least one photo')
    if problems:
        raise SystemExit("Shop data problems:\n  " + "\n  ".join(problems))
    if SHOP.get("enabled") and not SHOP_PREVIEW:
        blockers = []
        if SHOP.get("policies_draft"):
            blockers.append("the policies are still marked as a draft")
        if any(i.get("sample") for i in SHOP["items"]):
            blockers.append("sample pieces are still listed")
        if any(i["status"] == "available" and not i.get("buy_url") and not i.get("sample") for i in SHOP["items"]):
            blockers.append("an available piece has no buy_url")
        if blockers:
            raise SystemExit("Refusing to publish the shop: " + "; ".join(blockers) + ".")


def shop_tile(it, root):
    t = it.get("thumb") or it["photos"][0]
    badge = ""
    if it["status"] == "sold":
        badge += '<span class="badge badge-sold">Sold</span>'
    elif it["status"] == "reserved":
        badge += '<span class="badge badge-reserved">Reserved</span>'
    if it.get("sample"):
        badge += '<span class="badge badge-sample">Sample</span>'
    price = "" if it["status"] == "sold" else money(it["price"])
    return (f'<a class="tile shop-tile{" is-sold" if it["status"] == "sold" else ""}" '
            f'href="{root}shop/{it["sku"].lower()}/">'
            f'<span class="shop-img"><img src="{root}{t["file"]}" width="{t["w"]}" height="{t["h"]}" '
            f'alt="{e(it["title"])}" loading="lazy" decoding="async">{badge}</span>'
            f'<span class="shop-cap"><span class="shop-name">{e(it["title"])}</span>'
            f'<span class="shop-price">{price}</span></span>'
            f'<span class="shop-sku">{e(it["sku"])}</span></a>')


def shop_item_page(it):
    root = "../../"
    mail = SHOP.get("contact_email", "")
    ship = SHOP["shipping"][it["size"]]
    pickup = SHOP.get("pickup", {})
    figs = "\n".join(
        f'<figure><a class="zoom" href="{root}{p["file"]}">'
        f'<img src="{root}{p["file"]}" width="{p["w"]}" height="{p["h"]}" alt="{e(p["alt"])}" '
        f'loading="{"eager" if n == 0 else "lazy"}" decoding="async"></a></figure>'
        for n, p in enumerate(it["photos"]))
    specs = []
    for label, key in (("Dimensions", "dimensions"), ("Materials", "materials"), ("Made", "made")):
        value = it.get(key) or (sku_year(it["sku"]) if key == "made" else "")
        if value:
            specs.append(f"<dt>{label}</dt><dd>{e(str(value))}</dd>")
    specs_html = f'<dl class="specs">{"".join(specs)}</dl>' if specs else ""

    if it["status"] == "available":
        if it.get("buy_url"):
            action = f'<a class="btn" href="{e(it["buy_url"])}" rel="noopener">Buy this piece</a>'
        else:
            action = '<a class="btn" aria-disabled="true" href="#">Checkout is not set up yet</a>'
        status_html = ('<p class="exact">You will receive the exact piece pictured.</p>' + action +
                       f'<p class="delivery"><b>Shipping:</b> {money(ship["price"])} flat rate in the US, insured, ships within '
                       f'{e(SHOP.get("ships_within", "a few days"))}.')
        if pickup.get("offered") and it.get("pickup", True):
            area = f' ({e(pickup["area"])})' if pickup.get("area") else ""
            status_html += f'<br><b>Local pickup:</b> free{area}. Choose it at checkout.'
        status_html += f'</p><p class="delivery"><a href="{root}shop/shipping-returns/">Shipping and returns</a></p>'
    elif it["status"] == "reserved":
        status_html = '<p class="exact">Someone is checking out with this piece right now. If it is not completed, it becomes available again shortly.</p>'
    else:
        status_html = (f'<p class="exact">This piece has found a home.</p>'
                       f'<a class="btn btn-quiet" href="{root}shop/">See what is available</a>'
                       f'<p class="delivery"><a href="mailto:{e(mail)}?subject={e("Something like " + it["sku"])}">Ask about something similar</a></p>')
    price = "" if it["status"] == "sold" else f'<div class="price">{money(it["price"])}</div>'
    sample = '<p class="sample-note">Sample listing. These details are placeholders.</p>' if it.get("sample") else ""
    desc = paragraphs(it["description"]) if it.get("description") else ""
    ask = f'<p class="delivery"><a href="mailto:{e(mail)}?subject={e("Question about " + it["sku"])}">Ask a question about this piece</a></p>' if mail and it["status"] != "sold" else ""
    body = (f'<article class="item"><div class="item-head"><p class="sku">{e(it["sku"])}</p>'
            f'<h1 class="page-title">{e(it["title"])}</h1>{sample}{price}</div>'
            f'<div class="gallery">{figs}</div>'
            f'<aside class="buybox">{desc}{specs_html}{status_html}{ask}</aside></article>'
            f'<nav class="pager" aria-label="Shop"><a href="{root}shop/">← All pieces</a></nav>')
    ld = ""
    if not it.get("sample"):
        product = {
            "@context": "https://schema.org", "@type": "Product", "name": it["title"], "sku": it["sku"],
            "image": [f"{SITE_URL}/{p['file']}" for p in it["photos"]],
            "description": it.get("description", ""),
            "brand": {"@type": "Brand", "name": "Charles Talbot Studio"},
            "offers": {"@type": "Offer", "price": f'{it["price"]:.2f}', "priceCurrency": SHOP.get("currency", "USD"),
                       "url": f'{SITE_URL}/shop/{it["sku"].lower()}/',
                       "availability": "https://schema.org/InStock" if it["status"] == "available" else "https://schema.org/OutOfStock"},
        }
        ld = '<script type="application/ld+json">' + json.dumps(product).replace("</", "<\\/") + "</script>"
    page = layout(2, f'{it["title"]} ({it["sku"]})', body, active="shop/",
                  description=f'{it["title"]}, a one-of-a-kind piece by Charles Talbot.', og_image=it["photos"][0]["file"])
    write(f'shop/{it["sku"].lower()}/index.html', page.replace("</head>", ld + "\n</head>", 1) if ld else page)


def build_shop():
    shop_check()
    items = SHOP["items"]
    avail = [i for i in items if i["status"] != "sold"]
    sold = [i for i in items if i["status"] == "sold"]
    body = '<h1 class="page-title">Shop</h1>'
    body += f'<p class="shop-intro">{e(SHOP.get("intro", ""))}</p>'
    if avail:
        body += '<h2 class="shop-h">Available</h2><div class="grid">' + "\n".join(shop_tile(i, "../") for i in avail) + "</div>"
    else:
        body += '<p class="shop-empty">Nothing is available right now. New pieces are added after each firing, so check back soon.</p>'
    if sold:
        body += '<h2 class="shop-h">Sold</h2><div class="grid">' + "\n".join(shop_tile(i, "../") for i in sold) + "</div>"
    write("shop/index.html", layout(1, "Shop", body, active="shop/",
          description="One-of-a-kind pottery, sculpture and paintings by Charles Talbot.",
          og_image=(avail or sold or [{"photos": [{"file": "favicon.svg"}]}])[0]["photos"][0]["file"]))
    for it in items:
        shop_item_page(it)
    # Policies
    tiers = "".join(f'<tr><td>{e(t["label"])}</td><td>{e(t["hint"])}</td><td>{money(t["price"])}</td></tr>'
                    for t in SHOP["shipping"].values())
    banner = ('<div class="callout"><p>Draft policies. Review and edit before the shop opens.</p></div>'
              if SHOP.get("policies_draft") else "")
    secs = "".join(f'<h2 class="shop-h">{e(s["heading"])}</h2>{paragraphs(s["body"])}' for s in SHOP.get("policies", []))
    page = (f'<article class="prose"><h1 class="page-title">Shipping and returns</h1>{banner}{secs}'
            f'<h2 class="shop-h">Shipping rates (US)</h2><div class="scroll"><table><tr><th>Size</th><th>Examples</th><th>Flat rate</th></tr>{tiers}</table></div></article>')
    write("shop/shipping-returns/index.html", layout(2, "Shipping and returns", page, active="shop/"))


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full) or ROOT, exist_ok=True)
    with open(full, "w", encoding="utf8") as f:
        f.write(content)


def main():
    pieces = load_pieces()
    for p in pieces:
        p["thumb"] = wall_thumb(p)

    # Clean previously generated folders
    for v in VIEWS:
        shutil.rmtree(os.path.join(ROOT, v["slug"]), ignore_errors=True)
    for _, href in NAV + NAV2 + [("Shop", "shop/")]:
        shutil.rmtree(os.path.join(ROOT, href.strip("/")), ignore_errors=True)

    og = pieces[0]["photos"][0]
    for slug, label, kinds in KINDS + [("all", "All work", set(KIND_LABEL))]:
        subset = [p for p in pieces if p["kind"] in kinds]
        body = f'<h1 class="page-title">{e(label)}</h1>' + filters("../../", f"work/{slug}/") + wall(subset, "../../")
        write(f"work/{slug}/index.html", layout(2, label, body, active="work/", og_image=subset[0]["photos"][0]))
    default, label, kinds = KINDS[0]
    subset = [p for p in pieces if p["kind"] in kinds]
    write("index.html", layout(0, "", filters("", f"work/{default}/") + wall(subset, ""), og_image=og, body_class="home"))
    write("work/index.html", layout(1, label, f'<h1 class="page-title">{e(label)}</h1>' + filters("../", f"work/{default}/")
                                    + wall(subset, "../"), active="work/", og_image=og))
    for i, p in enumerate(pieces):
        piece_page(p, pieces[i - 1], pieces[(i + 1) % len(pieces)])

    tiles = []
    for t in THEMES:
        members = [p for p in pieces if t["slug"] in p["themes"]]
        t["cover"] = members[0]["thumb"] if members else None
        body = (f'<h1 class="page-title">{e(t["title"])}</h1>'
                + (f'<div class="prose">{paragraphs(t["description"])}</div>' if t["description"] else "")
                + wall(members, "../../", by_year=False))
        write(f'themes/{t["slug"]}/index.html', layout(2, t["title"], body, active="themes/",
              description=t["description"] or f'{t["title"]} — work by Charles Talbot.', og_image=t["cover"]))
        if t["cover"]:
            w, h = size_of(t["cover"])
            tiles.append(f'<a class="tile tile-labeled" href="{t["slug"]}/"><img src="../{t["cover"]}" width="{w}" height="{h}" '
                         f'alt="{e(t["title"])}" loading="lazy" decoding="async"><span class="tile-title">{e(t["title"])}</span></a>')
    view_tiles = []
    for v in VIEWS:
        c = v["cover"]
        view_tiles.append(f'<a class="tile tile-labeled" href="../{v["slug"]}/"><img src="../{c["file"]}" width="{c["w"]}" height="{c["h"]}" '
                          f'alt="{e(v["title"])}" loading="lazy" decoding="async"><span class="tile-title">{e(v["title"])}</span></a>')
    body = ('<h1 class="page-title">Themes</h1><div class="grid">' + "\n".join(tiles) + "</div>"
            '<h2 class="year-h">Shows and installations</h2><div class="grid">' + "\n".join(view_tiles) + "</div>")
    write("themes/index.html", layout(1, "Themes", body, active="themes/"))

    for key, href in (("about", "about/"), ("artist-statement", "artist-statement/")):
        page = SITE["pages"][key]
        label = dict((v, k) for k, v in NAV2)[href]
        body = f'<article class="prose"><h1 class="page-title">{e(label)}</h1>\n{paragraphs(page["body"], raw=True)}</article>'
        write(href + "index.html", layout(1, label, body, active=href))

    for i, v in enumerate(VIEWS):
        images = [(im["file"], im["w"], im["h"]) for im in v["images"]]
        desc = paragraphs(v["description"]) if v["description"] else ""
        meta_html = f'<p class="meta">{e(v["date"])}</p>' if v["date"] else ""
        pager = (f'<nav class="pager" aria-label="Shows and installations">'
                 f'<a href="../themes/">← Themes</a></nav>')
        body = (f'<article class="project"><h1 class="page-title">{e(v["title"])}</h1>{meta_html}{desc}'
                f'{gallery(images, "../", v["title"])}</article>{pager}')
        write(v["slug"] + "/index.html", layout(1, v["title"], body, description=f'{v["title"]} — work by Charles Talbot.',
                                               og_image=v["cover"]["file"]))

    if SHOP_ON:
        build_shop()
        print(f"Built the shop: {len(SHOP['items'])} pieces" + (" (preview)" if SHOP_PREVIEW else ""))
    else:
        shop_check()  # still validates the data, but publishes nothing

    write("_redirects", "".join(f"{old} {new} 301\n" for old, new in REDIRECTS.items()))
    print(f"Built {len(pieces)} pieces, {len(KINDS) + 3} wall pages, {len(THEMES)} themes, {len(VIEWS)} views + {len(NAV2)} others")


if __name__ == "__main__":
    main()
