-- Whether each piece is still available. A piece with no row is available.
-- held: in someone's checkout until hold_until (seconds since 1970); sold: paid for, or sold in person.
CREATE TABLE stock (
  sku        TEXT PRIMARY KEY,
  status     TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'held', 'sold')),
  hold       TEXT,      -- the checkout holding it (also in the Stripe session's metadata)
  hold_until INTEGER,
  session_id TEXT,      -- the Stripe Checkout Session
  sold_at    INTEGER,
  note       TEXT       -- e.g. "sold at the studio"
);
CREATE INDEX stock_hold ON stock (hold);
