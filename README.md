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

## Legacy

The old 2015 `app/` front end and its Grunt/Bower files are still in the repo and can be deleted.
