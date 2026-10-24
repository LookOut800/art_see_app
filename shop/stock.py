#!/usr/bin/env python3
"""See or change which shop pieces are sold, e.g. after selling one at the studio or a show.

    python3 shop/stock.py list                      every piece that is held or sold
    python3 shop/stock.py sold CMT-2026-004 "sold at the studio"
    python3 shop/stock.py available CMT-2026-004    undo: put it back on sale

Works on the live shop database; add --local to use the one `npx wrangler dev` uses.
Online sales need nothing: Stripe's webhook marks those pieces sold by itself.
"""
import re
import subprocess
import sys

HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
DB = "charlestalbot-shop"
SKU_RE = r"^CMT-(\d{4}|ND)-\d{3,5}$"


def run(sql, where):
    subprocess.run(["npx", "wrangler", "d1", "execute", DB, where, "--command", sql], cwd=HERE, check=True)


def main():
    args = [a for a in sys.argv[1:] if a != "--local"]
    where = "--local" if "--local" in sys.argv else "--remote"
    if not args or args[0] not in ("list", "sold", "available"):
        sys.exit(__doc__)
    if args[0] == "list":
        return run("SELECT sku, status, datetime(sold_at, 'unixepoch') AS sold, note FROM stock "
                   "WHERE status != 'available' ORDER BY sku", where)
    if len(args) < 2 or not re.match(SKU_RE, args[1]):
        sys.exit("Give a SKU like CMT-2026-004")
    sku, note = args[1], (args[2] if len(args) > 2 else "").replace("'", "''")
    if args[0] == "sold":
        run(f"INSERT INTO stock (sku, status, sold_at, note) VALUES ('{sku}', 'sold', strftime('%s','now'), '{note}') "
            f"ON CONFLICT (sku) DO UPDATE SET status = 'sold', sold_at = strftime('%s','now'), note = '{note}', "
            f"hold = NULL, hold_until = NULL", where)
    else:
        run(f"UPDATE stock SET status = 'available', sold_at = NULL, hold = NULL, hold_until = NULL, note = NULL "
            f"WHERE sku = '{sku}'", where)


if __name__ == "__main__":
    main()
