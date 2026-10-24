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
    "Two-pots": "vessels-2016-2017", "Brittany": "brittany-gallery-show-2022", "Pots-2024": "sculpture-2022",
    "Cut-Bonnet-Vase": "vessels-2016-2017", "Tea-pottery-1": "blue-and-white-bowls-2018",
    "Painted-Lyric-Bowls-S-S": "bowls-2018", "Tea-pottery": "tea-bowls-2018",
    "Small-Color-Paintings": "paintings-2017",
    "Tall-Sprayed-Vase-and-Handled-Vase": "vessels-2016-2017",
    "Turned-Vase-and-Blue-Globe-Bowl": "vessels-2016-2017",
    "Teabowls": "tea-bowls-2016", "Burned-Mountain-Vase": "vessels-2016-2017",
}

# Projects whose URL changed after launch: old slug -> new slug
RENAMED_PROJECTS = {
    "teabowls": "tea-bowls-2016",
    "tea-pottery": "tea-bowls-2018",
    "tea-pottery-1": "blue-and-white-bowls-2018",
    "brittany": "brittany-gallery-show-2022",
    "tea-bowls-blue-brushwork-2018": "blue-and-white-bowls-2018",
    "tea-bowls-spattered-glazes-2018": "tea-bowls-2018",
    "small-color-paintings": "paintings-2017",
    "teabowls-2016": "tea-bowls-2016",
    "pots-2024": "sculpture-2022",
    "painted-lyric-bowls-s-s": "bowls-2018",
    "two-pots": "vessels-2016-2017",
    "tall-sprayed-vase-and-handled-vase": "vessels-2016-2017",
    "burned-mountain-vase": "vessels-2016-2017",
    "cut-bonnet-vase": "vessels-2016-2017",
    "turned-vase-and-blue-globe-bowl": "vessels-2016-2017",
}

e = html.escape

# Projects with more photos than this show a thumbnail grid instead of one long scroll.
# Each image then needs a "thumb" (and "tw"/"th") entry in site.json.
GRID_GALLERY_MIN = 12

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
    # Clean previously generated folders
    for p in PROJECTS:
        shutil.rmtree(os.path.join(ROOT, p["slug"]), ignore_errors=True)
    for _, href in NAV + NAV2 + [("Shop", "shop/")]:
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

    if SHOP_ON:
        build_shop()
        print(f"Built the shop: {len(SHOP['items'])} pieces" + (" (preview)" if SHOP_PREVIEW else ""))
    else:
        shop_check()  # still validates the data, but publishes nothing

    redirects = [f"/{old} /{new}/ 301" for old, new in {**OLD_PAGES, **OLD_PROJECTS}.items()]
    for old, new in RENAMED_PROJECTS.items():  # earlier URLs of this site, with and without trailing slash
        redirects += [f"/{old} /{new}/ 301", f"/{old}/ /{new}/ 301"]
    write("_redirects", "\n".join(redirects) + "\n")
    print(f"Built {len(PROJECTS)} project pages + {len(NAV) + len(NAV2) + 1} others")


if __name__ == "__main__":
    main()
