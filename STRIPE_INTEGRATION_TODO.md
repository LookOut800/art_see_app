# Stripe Checkout: remaining setup

The site now has one server route, `POST /api/create-checkout-session`, which creates a Stripe Checkout Session and redirects the buyer to the Stripe-hosted payment page. It runs as a Cloudflare Worker that only handles `/api/*`; every other page is still a static file built by `python3 build.py`.

Nothing on the site calls this route yet. The shop's "Buy this piece" buttons still use each piece's Stripe Payment Link (`buy_url` in `content/shop.json`), which keeps working as before.

## Values to Replace

The following values are placeholders and must be updated before going live.

**Files containing placeholders:**
- [worker/index.js](worker/index.js)
- [wrangler.jsonc](wrangler.jsonc)

| Field | Current Value | What to Set |
|-------|--------------|-------------|
| mode | payment | Set to "payment" for one-time charges or "subscription" for recurring billing. Each piece is a one-time sale, so "payment" is likely right. |
| success_url | `${DOMAIN}/success?session_id={CHECKOUT_SESSION_ID}` | Your actual post-payment success page URL. Keep the {CHECKOUT_SESSION_ID} template. There is no `/success/` page on the site yet. |
| cancel_url | `${DOMAIN}` | Your actual cancel/return page URL, e.g. the piece's shop page (`/shop/<sku>/`). |
| line_items[].price | price_... | Your actual Stripe Price ID from the Dashboard (https://dashboard.stripe.com/prices) or API. Every piece has its own price, so the route needs to look the price up from the piece being bought (for example a form field with the SKU, mapped to a Price ID). |
| DOMAIN | https://charlestalbotart.com (in `wrangler.jsonc`), http://localhost:8787 (in `.dev.vars`) | The site's address, which success_url and cancel_url are built from. |

## Configured Parameters

These parameters were configured in Checkout Studio and are already set correctly.

**Files containing these parameters:**
- [worker/index.js](worker/index.js)

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

`ui_mode` is `hosted_page` because the installed Stripe SDK is version 22.6.2 (see [package.json](package.json)); SDK versions below 21.0.0 would need `hosted`.

## Setup

1. Install the Stripe SDK: `npm install` (in the repo root; `node_modules/` is not committed or published).
2. Local testing:
   - `cp .dev.vars.example .dev.vars` and put your **test** secret key (`sk_test_...`, from https://dashboard.stripe.com/test/apikeys) in it. `.dev.vars` is git-ignored.
   - `python3 build.py`, then `npx wrangler dev`, and open http://localhost:8787.
3. Production:
   - `npx wrangler secret put STRIPE_SECRET_KEY` and paste the **live** secret key. Never put keys in code or in `wrangler.jsonc`.
   - Check `DOMAIN` in `wrangler.jsonc`, then deploy as usual (`npx wrangler deploy`).

## New files

```
worker/index.js        the Worker: POST /api/create-checkout-session, everything else -> static files
package.json           the Stripe SDK (stripe 22.6.2), only used by the Worker
package-lock.json
.dev.vars.example      local settings for wrangler dev (copy to .dev.vars)
wrangler.jsonc         now has "main", the ASSETS binding, run_worker_first for /api/*, and DOMAIN
```

`.assetsignore` keeps all of these out of the published site.

## How it works

1. A buyer submits a form that POSTs to `/api/create-checkout-session` (not built yet, see Next steps).
2. The Worker creates a Checkout Session with the parameters above and answers with a 303 redirect to `session.url`.
3. The buyer pays on the Stripe-hosted page and is sent to `success_url`, or to `cancel_url` if they go back.

## Testing

Use test mode (a `sk_test_...` key) and Stripe's test cards, any future expiry date and any CVC:

- `4242 4242 4242 4242`: payment succeeds
- `4000 0025 0000 3155`: asks for 3D Secure authentication
- `4000 0000 0000 9995`: declined (insufficient funds)

More: https://docs.stripe.com/testing

## Next steps

- **Per-piece prices:** create a Price for each piece in Stripe (or switch `line_items` to `price_data` built from `content/shop.json`) and pick it from the SKU sent by the buy button.
- **Buy buttons:** to use this route instead of Payment Links, change the button in `build.py` (`shop_item_page`) to a `<form method="post" action="/api/create-checkout-session">` with a hidden SKU field.
- **Success page:** add a `/success/` page (a thank-you note) and point `success_url` at it.
- **Fulfillment and one-of-a-kind stock:** add a webhook for `checkout.session.completed` (with `STRIPE_WEBHOOK_SECRET`) so you are told about each sale, then mark the piece `"sold"` in `content/shop.json` and rebuild. Nothing stops a second buyer from paying for the same piece until then.
- **Order tracking:** orders are in the Stripe Dashboard (https://dashboard.stripe.com/payments).

## Resources

- https://support.stripe.com
- https://docs.stripe.com/mcp
