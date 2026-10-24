# Stripe Checkout: remaining setup

The shop is its own site in [shop/](shop/), meant for **shop.charlestalbotart.com**, separate from the portfolio. It runs sales (a group of pieces with an opening and closing time); buyers add pieces to a bag and pay for all of them in one Stripe-hosted Checkout. The pages are static files; a small Cloudflare Worker handles `/api/*`, holds pieces while someone checks out, and marks them sold when Stripe reports the payment. The portfolio only gets one "Shop" link in its menu, once `"enabled": true` is set in `content/shop.json`.

Everything below was tested locally with a placeholder key: pages, the bag, holds (a second buyer is turned away), a failed checkout releasing its holds, and a signed webhook marking pieces sold. **A real Checkout page has not been opened yet**: that needs your Stripe test key (Setup, step 3).

**Test mode on the live shop:** pieces marked `"sample": true` (or in a sample sale) check out only with `STRIPE_TEST_SECRET_KEY`, never the live key, and the webhook accepts both the live and the test endpoint's signing secret (`STRIPE_WEBHOOK_SECRET`, `STRIPE_TEST_WEBHOOK_SECRET`). So the sample sale can stay up for trying checkout with test cards while real sales use the live key. A bag can't mix sample and real pieces.

## Values to Replace

The following values are placeholders and must be updated before going live.

**Files containing placeholders:**
- [content/shop.json](content/shop.json)
- [shop/wrangler.jsonc](shop/wrangler.jsonc)

| Field | Current Value | What to Set |
|-------|--------------|-------------|
| mode | payment | Set to "payment" for one-time charges or "subscription" for recurring billing. Every piece is a one-time sale, so "payment" is right unless you add something recurring. |
| success_url | `${SITE_URL}/thanks/?session_id={CHECKOUT_SESSION_ID}` | Already points at the shop's thank-you page. Change only if you want a different page; keep the {CHECKOUT_SESSION_ID} template. |
| cancel_url | `${SITE_URL}/bag/?released=<hold>` | Already sends the buyer back to their bag and lets their pieces go. Nothing to change. |
| line_items | built from `content/shop.json` (`price_data`: each piece's title, SKU, price and photo) | No Stripe Price IDs are needed. Replace the **sample sale and sample pieces** in `content/shop.json` with real ones. |
| database_id | REPLACE_WITH_D1_DATABASE_ID (in `shop/wrangler.jsonc`) | The id printed by `npx wrangler d1 create charlestalbot-shop` (Setup, step 4). |
| SITE_URL | https://shop.charlestalbotart.com (`shop/wrangler.jsonc`), http://localhost:8787 (`shop/.dev.vars`) | The shop's address; Checkout sends buyers back here. |
| policies | `"policies_draft": true` in `content/shop.json` | Read and edit the shipping and returns text, then set it to false. |

## Configured Parameters

These parameters were configured in Checkout Studio and are already set correctly.

**Files containing these parameters:**
- [shop/worker.js](shop/worker.js)

| Parameter | Value |
|-----------|-------|
| ui_mode | hosted_page |
| billing_address_collection | auto |
| phone_number_collection | `{ enabled: false }` |
| automatic_tax | `{ enabled: false }` |
| allow_promotion_codes | false |
| submit_type | auto |
| integration_identifier | hosted_web_0001 |
| origin_context | web |
| payment_method_collection | always (only sent when mode is "subscription", so not sent now) |

`ui_mode` is `hosted_page` because the installed Stripe SDK is version 22.6.2 (see [shop/package.json](shop/package.json)); SDK versions below 21.0.0 would need `hosted`.

Added for this shop (not from Checkout Studio): `shipping_address_collection` (US only), `shipping_options` (one insured rate per order: the largest piece's rate plus `additional_item` for each extra piece, and free local pickup when every piece allows it), `expires_at` (30 minutes, the time pieces are held), and `metadata` (the hold and the SKUs, read by the webhook).

**Sales tax:** `automatic_tax` is off, as configured. Whether you need to collect sales tax depends on your state and how much you sell; check before the first sale rather than guess.

## Setup

All commands run from the repo root unless they start with `cd shop`.

1. **Install the Worker's packages:** `cd shop && npm install` (`node_modules/` is not committed).
2. **Build the pages:** `.venv/bin/python shop/build.py` writes `shop/dist/` and `shop/catalog.json` (the prices the Worker trusts). Run it again after every change to `content/shop.json`. `--release` refuses to build while sample pieces or draft policies remain.
3. **Try it locally with Stripe test mode:**
   - `cp shop/.dev.vars.example shop/.dev.vars` and put your **test** secret key (`sk_test_...`, from https://dashboard.stripe.com/test/apikeys) in it. `.dev.vars` is git-ignored.
   - `cd shop && npx wrangler d1 migrations apply charlestalbot-shop --local` (once), then `npx wrangler dev`, and open http://localhost:8787.
   - To have Stripe's webhook reach your machine: install the Stripe CLI, run `stripe listen --forward-to localhost:8787/api/webhook`, and put the `whsec_...` it prints in `.dev.vars` as `STRIPE_WEBHOOK_SECRET`.
4. **Go live** (Cloudflare account steps; the domain's DNS is already on Cloudflare):
   - `cd shop && npx wrangler d1 create charlestalbot-shop` and paste the `database_id` into `shop/wrangler.jsonc`, then `npx wrangler d1 migrations apply charlestalbot-shop --remote`.
   - `npx wrangler secret put STRIPE_SECRET_KEY` (the **live** key) and `npx wrangler secret put STRIPE_WEBHOOK_SECRET`. For the sample sale: `STRIPE_TEST_SECRET_KEY` (`sk_test_...`) and `STRIPE_TEST_WEBHOOK_SECRET` (from a webhook destination made in test mode, same URL).
   - In the Stripe Dashboard, add a webhook endpoint `https://shop.charlestalbotart.com/api/webhook` for the events `checkout.session.completed` and `checkout.session.expired`; its signing secret is the `STRIPE_WEBHOOK_SECRET` above.
   - `.venv/bin/python shop/build.py --release && cd shop && npx wrangler deploy`.
   - `shop.charlestalbotart.com` is a Custom Domain in `shop/wrangler.jsonc` (`routes`); deploying sets up its DNS record and certificate.
   - Set `"enabled": true` in `content/shop.json` and rebuild the portfolio (`.venv/bin/python build.py`) to show its "Shop" link.

## Project structure

```
content/shop.json              sales (title, opens, closes, intro, pieces) and pieces (title, price, size, photos, details)
shop/build.py                  builds shop/dist/ (pages, card photos) and shop/catalog.json
shop/static/shop.css, shop.js  the shop's look; the bag, countdowns and sold badges
shop/worker.js                 /api/stock, /api/checkout, /api/release, /api/webhook
shop/migrations/0001_stock.sql the stock table: which pieces are held or sold
shop/stock.py                  mark a piece sold (or available again) by hand, e.g. after a studio sale
shop/wrangler.jsonc            the Worker, its static files, the D1 database, SITE_URL
shop/.dev.vars.example         local secrets for wrangler dev (copy to .dev.vars)
```

## How it works

1. A sale page shows its pieces with an "Add to bag" button that only works while the sale is open; before it opens the page counts down. The bag is kept in the buyer's browser.
2. **Check out** sends the SKUs to `/api/checkout`. The Worker checks each sale is open, then holds every piece in one step: if any is already held or sold, nothing is held and the buyer is told which piece is gone.
3. The Worker creates a Checkout Session (prices from `catalog.json`, never from the browser) and the buyer pays on Stripe's page. Pieces stay held for the 30 minutes the session lasts.
4. Stripe calls `/api/webhook`: `checkout.session.completed` marks the pieces **sold**; `checkout.session.expired` lets them go. Backing out of checkout releases them right away.
5. Every page asks `/api/stock` as it loads and shows Sold or "In someone's checkout" live, without rebuilding the site. Past sales stay up as an archive.

## Testing

Use test mode (an `sk_test_...` key) and Stripe's test cards, with any future expiry date and any CVC:

- `4242 4242 4242 4242`: payment succeeds
- `4000 0025 0000 3155`: asks for 3D Secure authentication
- `4000 0000 0000 9995`: declined (insufficient funds)

Worth trying: two browsers adding the same piece and checking out at once (the second is turned away), backing out of checkout (the piece is available again), and a sale whose opening time is in the future (buttons stay off until then).

More: https://docs.stripe.com/testing

## Next steps

- **A real sale:** replace the sample sale and pieces in `content/shop.json` (photos can be any files in the repo, for example the portfolio's).
- **Fulfillment:** paid orders, with shipping addresses, are in the Stripe Dashboard (https://dashboard.stripe.com/payments); turn on Stripe's customer receipt emails there.
- **Sales in person:** `python3 shop/stock.py sold CMT-2026-004 "sold at the studio"`.
- **Optional later:** an email when something sells (beyond Stripe's own notifications), and a "tell me about the next sale" sign-up.

## Resources

- https://support.stripe.com
- https://docs.stripe.com/mcp
