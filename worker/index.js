// Cloudflare Worker: handles /api/* only (see run_worker_first in wrangler.jsonc).
// Every other URL is served straight from the static files built by build.py.
//
//   POST /api/create-checkout-session  ->  303 redirect to a Stripe-hosted Checkout page
//
// Secrets and settings come from the Worker's environment, never from code:
// STRIPE_SECRET_KEY (a secret) and DOMAIN. Locally they go in .dev.vars (see .dev.vars.example).
import Stripe from "stripe";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/create-checkout-session") {
      if (request.method !== "POST") {
        return new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });
      }
      const stripe = new Stripe(env.STRIPE_SECRET_KEY);

      // TODO: one-time sales of single pieces, so "payment". Use "subscription" only for recurring billing.
      const mode = "payment";

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
        // Placeholders: see STRIPE_INTEGRATION_TODO.md
        mode,
        success_url: `${env.DOMAIN}/success?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${env.DOMAIN}`,
        line_items: [{ price: "price_...", quantity: 1 }],
      };
      if (mode === "subscription") {
        sessionParams.payment_method_collection = "always";
      }

      const session = await stripe.checkout.sessions.create(sessionParams);
      return Response.redirect(session.url, 303);
    }

    return env.ASSETS.fetch(request);
  },
};
