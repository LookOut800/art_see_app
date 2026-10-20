# Charles Talbot Studio

Static portfolio site for [charlestalbotart.com](https://www.charlestalbotart.com/), replacing the Cargo template. Plain HTML, CSS and a little JavaScript, with no framework and no server.

## Layout

| Path | What it is |
|---|---|
| `content/site.json` | All the content: projects, titles, dates, text, image order, which section (`recent` / `archives` / `none`) each project appears in |
| `images/<project>/` | Web-sized photos (`01.jpg`, `02.jpg`, ... and `cover.jpg` for the grid) |
| `build.py` | Generates the HTML pages from `site.json` |
| `css/style.css`, `js/main.js` | Styling, mobile menu and image lightbox |
| `_redirects` | Old Cargo URLs mapped to the new ones (read by Cloudflare's static assets) |
| `index.html`, `<project>/index.html`, ... | Generated output; do not edit by hand |

## Editing the site

1. Change `content/site.json`, or drop new photos into `images/<project>/` and list them there.
2. Run `python3 build.py`.
3. Preview locally with `python3 -m http.server 8000` and open http://localhost:8000.

## Hosting

Cloudflare Workers static assets: `wrangler.jsonc` publishes the repo root as the `art-see-app` project
(the name must match the Cloudflare dashboard), and `.assetsignore` keeps the source, content and tools off the
site. To publish by hand: `npx wrangler deploy`. Domain: charlestalbotart.com.

Photos should be JPEGs around 1800px on the long edge, with GPS/location metadata stripped.

## The shop (not live yet)

The shop is built but hidden. Nothing shows on the website until `"enabled": true` is set in `content/shop.json`, and `build.py` refuses to publish it while sample pieces or draft policies remain.

Each piece is one of a kind and has its own SKU in the same three-part shape, `CMT-<year>-<number>`. One running number covers every piece, and the middle part is the year it was made, or `ND` ("no date", as in n.d.) when you do not know:

- `CMT-2018-014` means made in 2018.
- `CMT-ND-015` means no date is known, and the website shows no date unless you set the optional `made` field in `content/shop.json` (`c. 2021`, `2019 to 2021`).

A SKU is never renamed after it is on a piece. If you later learn the year of a `CMT-ND-015`, set `made` on its listing.

Labels: say how many of each year you want, with `ND` for no date and `x9` to repeat:
`python3 tools/make_labels.py --start 1 --years 2026x9,2027x12,NDx9 --out tools/labels/CMT-001-to-030.pdf`
(CMT-2026-001 to 009, CMT-2027-010 to 021, CMT-ND-022 to 030). Or list years one by one: `--years 2018,2018,ND,2021`. Note each printed batch in `tools/labels/LOG.md`, so you know the next free number. No-date labels never go stale, so print those in bulk. Each label has the SKU and a QR code to the piece's page. For a sheet you have partly used, add `--skip 5` to leave the first 5 positions empty. Write the SKU on the piece's foot or back too, so photos, listing and order all match.

Add a piece from 3 or 4 photos:

1. `python3 tools/add_piece.py CMT-2018-014 "Title" 85 small photos/*.jpg` (or `CMT-ND-015 ... --made "c. 2021"` when the year is only a guess)
2. Open `content/shop.json` and fill in dimensions, materials and a short description.
3. Create the Stripe payment link for it and paste the link into `buy_url`.
4. `python3 build.py`, check it, then publish as usual.

When a piece sells, change its `status` to `sold` and rebuild. It stays on the site in the Sold section.

Preview the shop with its sample pieces: `SHOP_PREVIEW=1 python3 build.py`, then rebuild normally with `python3 build.py` before committing so the preview pages are removed.
