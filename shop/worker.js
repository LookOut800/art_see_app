// The shop's Worker: shop.charlestalbotart.com/api/*. Everything else is a static page from dist/.
//
//   GET  /api/stock      which pieces are held or sold, for the sale pages and the bag
//   POST /api/checkout   {skus: [...]} -> holds those pieces, returns {url} of a Stripe-hosted Checkout page
//                        (409 {unavailable: [...]} if any is already held or sold, or its sale is not open)
//   POST /api/release    {hold} -> lets go of a checkout the buyer backed out of
//   POST /api/webhook    from Stripe: a paid checkout marks its pieces sold, an expired one lets them go
//
// Prices, titles and sale dates come from catalog.json, which shop/build.py writes from content/shop.json,
// so nothing the browser sends can change a price. Which pieces are held or sold is in D1 (env.DB).
// Secrets come from the environment: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET; SITE_URL is a var.
// Sample pieces ("test" in catalog.json) check out only in Stripe's test mode, with STRIPE_TEST_SECRET_KEY
// and STRIPE_TEST_WEBHOOK_SECRET, so a sample sale on the live shop can never take real money.
import Stripe from "stripe";
import catalog from "./catalog.json";

const CHECKOUT_MINUTES = 30; // the shortest a Stripe Checkout Session can last
const HOLD_SECONDS = (CHECKOUT_MINUTES + 2) * 60; // a little longer, so a hold never ends before its checkout

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
const now = () => Math.floor(Date.now() / 1000);

function saleOpen(slug, t = Date.now()) {
  const s = catalog.sales[slug];
  return Boolean(s) && Date.parse(s.opens) <= t && t < Date.parse(s.closes);
}

async function stock(env) {
  const { results } = await env.DB.prepare(
    "SELECT sku, status, hold_until FROM stock WHERE status != 'available'"
  ).all();
  const out = {};
  for (const r of results) {
    if (r.status === "sold") out[r.sku] = "sold";
    else if (r.hold_until > now()) out[r.sku] = "held";
  }
  return out;
}

async function release(env, hold) {
  await env.DB.prepare("UPDATE stock SET status = 'available', hold = NULL, hold_until = NULL WHERE hold = ? AND status = 'held'")
    .bind(hold)
    .run();
}

function shippingOptions(items) {
  // One flat, insured rate for the whole bag: the largest piece's rate, plus a little for each extra piece
  const rates = items.map((it) => catalog.shipping[it.size].price);
  const amount = Math.max(...rates) + catalog.additional_item * (items.length - 1);
  const options = [
    {
      shipping_rate_data: {
        type: "fixed_amount",
        display_name: "Insured shipping (US)",
        fixed_amount: { amount: Math.round(amount * 100), currency: catalog.currency.toLowerCase() },
      },
    },
  ];
  if (catalog.pickup.offered && items.every((it) => it.pickup)) {
    options.push({
      shipping_rate_data: {
        type: "fixed_amount",
        display_name: "Local pickup" + (catalog.pickup.area ? ` (${catalog.pickup.area})` : ""),
        fixed_amount: { amount: 0, currency: catalog.currency.toLowerCase() },
      },
    });
  }
  return options;
}

async function checkout(request, env) {
  let skus;
  try {
    skus = [...new Set((await request.json()).skus)];
  } catch {
    return json({ error: "Send {skus: [...]}" }, 400);
  }
  if (!skus.length || skus.length > 20) return json({ error: "Bag is empty or too big" }, 400);
  const items = skus.map((sku) => catalog.items[sku]);
  const closed = skus.filter((sku, i) => !items[i] || !saleOpen(items[i].sale));
  if (closed.length) return json({ unavailable: closed, reason: "not on sale" }, 409);
  const test = items.some((it) => it.test);
  if (test && !items.every((it) => it.test)) {
    return json({ error: "Sample pieces and real pieces can't be checked out together. Remove the samples." }, 400);
  }
  const key = test ? env.STRIPE_TEST_SECRET_KEY : env.STRIPE_SECRET_KEY;
  if (!key || (test && !/^(sk|rk)_test_/.test(key))) {
    console.log(test ? "No Stripe test key (STRIPE_TEST_SECRET_KEY) for sample pieces" : "No STRIPE_SECRET_KEY");
    return json({ error: "Checkout is not available right now. Please try again." }, 502);
  }

  // Hold every piece in the bag, or none: a piece can be held only if it is available or its hold ran out
  const hold = crypto.randomUUID();
  const t = now();
  const results = await env.DB.batch([
    ...skus.map((sku) => env.DB.prepare("INSERT OR IGNORE INTO stock (sku) VALUES (?)").bind(sku)),
    ...skus.map((sku) =>
      env.DB.prepare(
        "UPDATE stock SET status = 'held', hold = ?, hold_until = ?, session_id = NULL " +
          "WHERE sku = ? AND (status = 'available' OR (status = 'held' AND hold_until < ?))"
      ).bind(hold, t + HOLD_SECONDS, sku, t)
    ),
  ]);
  const unavailable = skus.filter((sku, i) => results[skus.length + i].meta.changes !== 1);
  if (unavailable.length) {
    await release(env, hold);
    return json({ unavailable, reason: "taken" }, 409);
  }

  const stripe = new Stripe(key);
  const mode = "payment"; // each piece is a one-time sale
  const sessionParams = {
    // Configured in Checkout Studio
    ui_mode: "hosted_page",
    billing_address_collection: "auto",
    phone_number_collection: { enabled: false },
    automatic_tax: { enabled: false },
    allow_promotion_codes: false,
    submit_type: "auto",
    integration_identifier: "hosted_web_0001",
    origin_context: "web",
    // This shop
    mode,
    line_items: items.map((it, i) => ({
      quantity: 1,
      price_data: {
        currency: catalog.currency.toLowerCase(),
        unit_amount: Math.round(it.price * 100),
        product_data: {
          name: `${it.title} (${skus[i]})`,
          images: [`${env.SITE_URL}/${it.image}`],
          metadata: { sku: skus[i] },
        },
      },
    })),
    shipping_address_collection: { allowed_countries: ["US"] },
    shipping_options: shippingOptions(items),
    expires_at: t + CHECKOUT_MINUTES * 60,
    metadata: { hold, skus: skus.join(",") },
    success_url: `${env.SITE_URL}/thanks/?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${env.SITE_URL}/bag/?released=${hold}`,
  };
  if (mode === "subscription") {
    sessionParams.payment_method_collection = "always";
  }
  let session;
  try {
    session = await stripe.checkout.sessions.create(sessionParams);
  } catch (err) {
    await release(env, hold);
    console.log("Checkout Session failed:", err.message);
    return json({ error: "Checkout is not available right now. Please try again." }, 502);
  }
  await env.DB.prepare("UPDATE stock SET session_id = ? WHERE hold = ?").bind(session.id, hold).run();
  return json({ url: session.url });
}

async function webhook(request, env) {
  // Live and test mode each sign with their own endpoint secret; accept either
  const stripe = new Stripe(env.STRIPE_SECRET_KEY || env.STRIPE_TEST_SECRET_KEY);
  const body = await request.text();
  const signature = request.headers.get("stripe-signature");
  let event;
  for (const secret of [env.STRIPE_WEBHOOK_SECRET, env.STRIPE_TEST_WEBHOOK_SECRET].filter(Boolean)) {
    try {
      event = await stripe.webhooks.constructEventAsync(body, signature, secret, undefined, Stripe.createSubtleCryptoProvider());
      break;
    } catch (err) {
      // try the other secret
    }
  }
  if (!event) {
    console.log("Webhook signature verification failed.");
    return new Response("Bad signature", { status: 400 });
  }
  const session = event.data.object;
  const hold = session.metadata && session.metadata.hold;
  if (event.type === "checkout.session.completed" && hold) {
    await env.DB.prepare(
      "UPDATE stock SET status = 'sold', sold_at = ?, session_id = ?, hold_until = NULL WHERE hold = ?"
    )
      .bind(now(), session.id, hold)
      .run();
    console.log("Sold:", session.metadata.skus, session.id);
  } else if (event.type === "checkout.session.expired" && hold) {
    await release(env, hold);
  }
  return new Response("ok");
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    const post = request.method === "POST";
    if (pathname === "/api/stock" && request.method === "GET") return json(await stock(env));
    if (pathname === "/api/checkout" && post) return checkout(request, env);
    if (pathname === "/api/release" && post) {
      const { hold } = await request.json().catch(() => ({}));
      if (typeof hold === "string" && hold) await release(env, hold);
      return json({ ok: true });
    }
    if (pathname === "/api/webhook" && post) return webhook(request, env);
    if (pathname.startsWith("/api/")) return json({ error: "Not found" }, 404);
    return env.ASSETS.fetch(request);
  },
};
