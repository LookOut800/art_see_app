#!/usr/bin/env python3
"""Build the shop (shop.charlestalbotart.com) from content/shop.json into shop/dist/.

    .venv/bin/python shop/build.py            preview build, samples and draft policies allowed
    .venv/bin/python shop/build.py --release  refuses while sample pieces or draft policies remain
    cd shop && npx wrangler dev               try it at http://localhost:8787 (see STRIPE_INTEGRATION_TODO.md)

The shop is its own site, separate from the portfolio. It is organized in sales: a sale is a group
of pieces with a time it opens and closes. Buyers add pieces to a bag and check out once. Pages are
static; which pieces are held or sold comes from /api/stock (shop/worker.js) as the page loads.
Also writes shop/catalog.json, the prices and sale times the Worker trusts (the browser's are ignored).
"""
import datetime
import html
import json
import os
import re
import shutil
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(HERE, "dist")
SHOP = json.load(open(os.path.join(ROOT, "content", "shop.json"), encoding="utf8"))
SKU_RE = r"^CMT-(\d{4}|ND)-\d{3,5}$"  # CMT-2018-014 (year made) or CMT-ND-014 (no date known)
THUMB = 720  # px, long edge of the card photos
e = html.escape


def money(v):
    return f"${v:,.0f}" if float(v).is_integer() else f"${v:,.2f}"


def paragraphs(text):
    return "\n".join("<p>" + e(b.strip()).replace("\n", "<br>") + "</p>" for b in text.split("\n\n") if b.strip())


def when(iso):
    """'Sat, Oct 31, 10 am ET' in the sale's own time zone (Eastern if the offset is -4 or -5)."""
    t = datetime.datetime.fromisoformat(iso)
    off = t.utcoffset().total_seconds() / 3600
    zone = "ET" if off in (-4, -5) else f"UTC{off:+g}"
    hour = t.strftime("%I").lstrip("0") + (t.strftime(":%M") if t.minute else "") + (" am" if t.hour < 12 else " pm")
    return f'{t.strftime("%a, %b")} {t.day}, {hour} {zone}'


def check(release):
    items = {it["sku"]: it for it in SHOP["items"]}
    problems, in_sale = [], {}
    for it in SHOP["items"]:
        sku = it["sku"]
        if not re.match(SKU_RE, sku):
            problems.append(f"{sku}: SKU must look like CMT-2018-014 or CMT-ND-014")
        if it["size"] not in SHOP["shipping"]:
            problems.append(f'{sku}: size must be one of {", ".join(SHOP["shipping"])}')
        if not it["photos"]:
            problems.append(f"{sku}: needs at least one photo")
        for f in it["photos"]:
            if not os.path.exists(os.path.join(ROOT, f)):
                problems.append(f"{sku}: {f} does not exist")
    if len(items) != len(SHOP["items"]):
        problems.append("a SKU is listed twice in items")
    for s in SHOP["sales"]:
        if datetime.datetime.fromisoformat(s["opens"]) >= datetime.datetime.fromisoformat(s["closes"]):
            problems.append(f'sale {s["slug"]}: opens must be before closes')
        for sku in s["items"]:
            if sku not in items:
                problems.append(f'sale {s["slug"]}: no item {sku}')
            elif sku in in_sale:
                problems.append(f'{sku} is in two sales ({in_sale[sku]}, {s["slug"]}); take it out of the old one')
            in_sale[sku] = s["slug"]
    if release:
        if SHOP.get("policies_draft"):
            problems.append("the policies are still marked as a draft (policies_draft)")
        if any(i.get("sample") for i in SHOP["items"]) or any(s.get("sample") for s in SHOP["sales"]):
            problems.append("sample pieces or a sample sale are still listed")
    if problems:
        raise SystemExit("content/shop.json problems:\n  " + "\n  ".join(problems))
    return items, in_sale


def layout(depth, title, body, description="", body_class=""):
    root = "../" * depth
    full = f"{title} — Charles Talbot Shop" if title else "Charles Talbot Shop"
    desc = description or "Sales of one-of-a-kind pottery, sculpture and paintings by Charles Talbot."
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{root}shop.css">
</head>
<body class="{body_class}" data-root="{root}">
<header class="top">
  <a class="mark" href="{root}">Charles Talbot <span>Shop</span></a>
  <nav aria-label="Shop">
    <a href="{root}">Sales</a>
    <a href="{root}shipping-returns/">Shipping &amp; returns</a>
    <a href="{e(SHOP["portfolio_url"])}">Portfolio</a>
    <a class="bag-link" href="{root}bag/">Bag <span class="bag-count" aria-label="pieces in your bag">0</span></a>
  </nav>
</header>
<main id="main">
{body}
</main>
<footer class="foot"><p>Questions? <a href="mailto:{e(SHOP["contact_email"])}">{e(SHOP["contact_email"])}</a></p></footer>
<script src="{root}shop.js" defer></script>
</body>
</html>
"""


def write(rel, content):
    full = os.path.join(DIST, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf8") as f:
        f.write(content)


def photo(rel):
    """Copy a photo into dist/ (same path as in the repo) and return (path, w, h)."""
    dst = os.path.join(DIST, rel)
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), dst)
    w, h = Image.open(dst).size
    return rel, w, h


def card_photo(it):
    rel = f'cards/{it["sku"].lower()}.jpg'
    im = Image.open(os.path.join(ROOT, it["photos"][0])).convert("RGB")
    im.thumbnail((THUMB, THUMB), Image.LANCZOS)
    os.makedirs(os.path.join(DIST, "cards"), exist_ok=True)
    im.save(os.path.join(DIST, rel), "JPEG", quality=82, optimize=True, progressive=True)
    return rel, im.width, im.height


def sale_state(s):
    """Text for before the page's script runs; shop.js keeps it current with a countdown."""
    return (f'<p class="sale-when" data-opens="{e(s["opens"])}" data-closes="{e(s["closes"])}">'
            f'<span class="sale-state">{e(when(s["opens"]))} to {e(when(s["closes"]))}</span></p>')


def made(it):
    """The made field, else the year in the SKU (CMT-2018-014), else nothing."""
    m = re.match(r"^CMT-(\d{4})-", it["sku"])
    return it.get("made") or (m.group(1) if m else "")


def item_bits(it):
    return [x for x in (made(it), it.get("materials"), it.get("dimensions")) if x]


def add_button(it, sale):
    return (f'<button type="button" class="add" data-sku="{e(it["sku"])}" data-sale="{e(sale["slug"])}" '
            f'data-opens="{e(sale["opens"])}" data-closes="{e(sale["closes"])}">Add to bag</button>')


def build():
    release = "--release" in sys.argv
    items, in_sale = check(release)
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)
    for f in ("shop.css", "shop.js"):
        shutil.copyfile(os.path.join(HERE, "static", f), os.path.join(DIST, f))
    shutil.copyfile(os.path.join(ROOT, "favicon.svg"), os.path.join(DIST, "favicon.svg"))

    cards, public = {}, {}
    for it in SHOP["items"]:
        cards[it["sku"]] = card_photo(it)
    sales = sorted(SHOP["sales"], key=lambda s: s["opens"], reverse=True)
    now = datetime.datetime.now(datetime.timezone.utc)

    for s in sales:
        tiles = []
        for sku in s["items"]:
            it = items[sku]
            c, w, h = cards[sku]
            url = f'{s["slug"]}/{sku.lower()}/'
            public[sku] = {"title": it["title"], "price": it["price"], "image": c, "url": url, "sale": s["slug"],
                           "opens": s["opens"], "closes": s["closes"]}
            tiles.append(
                f'<article class="card" data-sku="{e(sku)}"><a class="card-img" href="{sku.lower()}/">'
                f'<img src="../{c}" width="{w}" height="{h}" alt="{e(it["title"])}" loading="lazy" decoding="async">'
                f'<span class="badge"></span></a>'
                f'<div class="card-text"><h2><a href="{sku.lower()}/">{e(it["title"])}</a></h2>'
                f'<p class="card-meta">{" · ".join(e(b) for b in item_bits(it))}</p>'
                f'<p class="card-buy"><span class="price">{money(it["price"])}</span>{add_button(it, s)}</p></div></article>')
            item_page(it, s)
        sample = '<p class="note">Sample sale: these pieces and prices are placeholders.</p>' if s.get("sample") else ""
        body = (f'<section class="sale-head"><h1>{e(s["title"])}</h1>{sale_state(s)}{sample}'
                f'<div class="intro">{paragraphs(s.get("intro", ""))}</div></section>'
                f'<div class="cards">{"".join(tiles)}</div>')
        write(f'{s["slug"]}/index.html', layout(1, s["title"], body, description=s.get("intro", "")[:160]))

    # Home: sales that have not closed yet up top, earlier ones below as an archive
    def sale_tile(s):
        c, w, h = cards[s["items"][0]]
        return (f'<a class="sale-tile" href="{s["slug"]}/"><img src="{c}" width="{w}" height="{h}" alt="" loading="lazy">'
                f'<span><b>{e(s["title"])}</b>{sale_state(s)}<small>{len(s["items"])} pieces</small></span></a>')
    current = [s for s in sales if datetime.datetime.fromisoformat(s["closes"]) > now]
    past = [s for s in sales if s not in current]
    body = ""
    if current:
        body += '<h1 class="page-h">Sales</h1><div class="sales">' + "".join(sale_tile(s) for s in reversed(current)) + "</div>"
    else:
        body += ('<h1 class="page-h">No sale right now</h1><p class="lede">New work is released a few times a year. '
                 f'To hear about the next sale, write to <a href="mailto:{e(SHOP["contact_email"])}">{e(SHOP["contact_email"])}</a>.</p>')
    if past:
        body += '<h2 class="sub-h">Past sales</h2><div class="sales sales-past">' + "".join(sale_tile(s) for s in past) + "</div>"
    write("index.html", layout(0, "", body, body_class="home"))

    write("bag/index.html", layout(1, "Your bag", '<h1 class="page-h">Your bag</h1><div id="bag"><p class="lede">Loading…</p></div>'
                                   f'<script type="application/json" id="catalog">{json.dumps(public).replace("</", "<\\/")}</script>',
                                   body_class="bag-page"))
    write("thanks/index.html", layout(1, "Thank you", '<h1 class="page-h">Thank you</h1><p class="lede">Your order is in. '
                                      'A receipt is on its way by email, and you will hear from me when your pieces ship '
                                      f'(within {e(SHOP["ships_within"])}).</p><p><a href="../">Back to the shop</a></p>',
                                      body_class="thanks-page"))
    policies(SHOP)

    # What the Worker trusts: prices, sizes and sale times from this file, not from the browser
    catalog = {
        "currency": SHOP["currency"], "shipping": SHOP["shipping"], "additional_item": SHOP["additional_item"],
        "pickup": SHOP["pickup"],
        "sales": {s["slug"]: {"opens": s["opens"], "closes": s["closes"]} for s in SHOP["sales"]},
        "items": {sku: {"title": it["title"], "price": it["price"], "size": it["size"], "pickup": it.get("pickup", True),
                        "sale": in_sale[sku], "image": cards[sku][0]} for sku, it in items.items() if sku in in_sale},
    }
    json.dump(catalog, open(os.path.join(HERE, "catalog.json"), "w", encoding="utf8"), indent=1, ensure_ascii=False)
    print(f'Built the shop: {len(sales)} sales, {len(in_sale)} pieces' + ("" if release else " (preview: samples allowed)"))


def item_page(it, s):
    figs = []
    for n, f in enumerate(it["photos"]):
        rel, w, h = photo(f)
        figs.append(f'<img src="../../{rel}" width="{w}" height="{h}" alt="{e(it["title"])}, photo {n + 1}" '
                    f'loading="{"eager" if n == 0 else "lazy"}" decoding="async">')
    thumbs = "".join(f'<button type="button" data-i="{n}" aria-label="Photo {n + 1}"><img src="../../{photo(f)[0]}" alt=""></button>'
                     for n, f in enumerate(it["photos"])) if len(it["photos"]) > 1 else ""
    specs = "".join(f"<dt>{k}</dt><dd>{e(str(v))}</dd>" for k, v in (
        ("Made", made(it)), ("Materials", it.get("materials")), ("Dimensions", it.get("dimensions"))) if v)
    ship = SHOP["shipping"][it["size"]]
    pickup = " Free local pickup is available at checkout." if SHOP["pickup"].get("offered") and it.get("pickup", True) else ""
    sample = '<p class="note">Sample listing: details are placeholders.</p>' if it.get("sample") else ""
    body = (f'<p class="crumb"><a href="../">← {e(s["title"])}</a></p>'
            f'<article class="item" data-sku="{e(it["sku"])}"><div class="photos"><div class="photo-main">{figs[0]}'
            f'<span class="badge"></span></div>'
            f'<div class="photo-thumbs">{thumbs}</div>'
            f'<template id="photo-list">{"".join(figs)}</template></div>'
            f'<div class="details"><p class="sku">{e(it["sku"])}</p><h1>{e(it["title"])}</h1>{sample}'
            f'<p class="price big">{money(it["price"])}</p>{add_button(it, s)}'
            f'<p class="small">You receive the exact piece pictured. Insured shipping in the US from {money(ship["price"])} '
            f'for the whole order, ships within {e(SHOP["ships_within"])}.{pickup}</p>'
            f'{paragraphs(it.get("description", ""))}'
            f'{f"<dl>{specs}</dl>" if specs else ""}'
            f'{sale_state(s)}</div></article>')
    write(f'{s["slug"]}/{it["sku"].lower()}/index.html', layout(2, it["title"], body,
          description=f'{it["title"]}, one of a kind, by Charles Talbot.'))


def policies(shop):
    tiers = "".join(f'<tr><td>{e(t["label"])}</td><td>{e(t["hint"])}</td><td>{money(t["price"])}</td></tr>'
                    for t in shop["shipping"].values())
    draft = '<p class="note">Draft policies: review and edit before the first sale.</p>' if shop.get("policies_draft") else ""
    secs = "".join(f'<h2 class="sub-h">{e(p["heading"])}</h2>{paragraphs(p["body"])}' for p in shop.get("policies", []))
    body = (f'<article class="prose"><h1 class="page-h">Shipping and returns</h1>{draft}{secs}'
            f'<h2 class="sub-h">Shipping rates (US)</h2><p>One insured rate per order: the rate for the largest piece, '
            f'plus {money(shop["additional_item"])} for each additional piece.</p>'
            f'<table><tr><th>Size</th><th>Examples</th><th>Rate</th></tr>{tiers}</table></article>')
    write("shipping-returns/index.html", layout(1, "Shipping and returns", body))


if __name__ == "__main__":
    build()
