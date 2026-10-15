# Charles Talbot Studio

Static portfolio site for [charlestalbotart.com](https://www.charlestalbotart.com/), replacing the Cargo template. Plain HTML, CSS and a little JavaScript, with no framework and no server.

## Layout

| Path | What it is |
|---|---|
| `content/site.json` | All the content: projects, titles, dates, text, image order, which section (`recent` / `archives` / `none`) each project appears in |
| `images/<project>/` | Web-sized photos (`01.jpg`, `02.jpg`, ... and `cover.jpg` for the grid) |
| `build.py` | Generates the HTML pages from `site.json` |
| `css/style.css`, `js/main.js` | Styling, mobile menu and image lightbox |
| `_redirects` | Old Cargo URLs mapped to the new ones (Netlify / Cloudflare Pages) |
| `index.html`, `<project>/index.html`, ... | Generated output; do not edit by hand |

## Editing the site

1. Change `content/site.json`, or drop new photos into `images/<project>/` and list them there.
2. Run `python3 build.py`.
3. Preview locally with `python3 -m http.server 8000` and open http://localhost:8000.

Photos should be JPEGs around 1800px on the long edge, with GPS/location metadata stripped.

## The shop (not live yet)

The shop is built but hidden. Nothing shows on the website until `"enabled": true` is set in `content/shop.json`, and `build.py` refuses to publish it while sample pieces or draft policies remain.

Each piece is one of a kind and has its own SKU, a plain number such as `CMT-014` (your signature initials plus a running number). A SKU carries no date, so a label never goes stale and an old pot is not mislabelled. When you know when a piece was made, put it in the optional `made` field (`2021`, `c. 2021`, `2019 to 2021`) or leave it empty to show no date.

Labels: `python3 tools/make_labels.py --start 1 --count 30 --out tools/labels/CMT-001-to-030.pdf` makes a sheet for Avery 5160-style labels, each with the SKU, a QR code to the piece's page, and a blank "made ____" line to fill in by hand. For a sheet you have partly used, add `--skip 5` to leave the first 5 positions empty. Write the SKU on the piece's foot or back too, so photos, listing and order all match.

Add a piece from 3 or 4 photos:

1. `python3 tools/add_piece.py CMT-014 "Title" 85 small photos/*.jpg --made "c. 2021"`
2. Open `content/shop.json` and fill in dimensions, materials and a short description.
3. Create the Stripe payment link for it and paste the link into `buy_url`.
4. `python3 build.py`, check it, then publish as usual.

When a piece sells, change its `status` to `sold` and rebuild. It stays on the site in the Sold section.

Preview the shop with its sample pieces: `SHOP_PREVIEW=1 python3 build.py`, then rebuild normally with `python3 build.py` before committing so the preview pages are removed.
