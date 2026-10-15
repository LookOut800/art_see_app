#!/usr/bin/env python3
"""Make a printable sheet of SKU labels with a QR code that opens the piece's page.

One running number covers every piece. The year is added only when you know when it was made:

    CMT-2018-014   made in 2018
    CMT-ND-015     no date known (ND = no date)

Print a batch by saying how many labels of each year you want. "ND" (or a blank) means no date,
and "x9" repeats a label type nine times:

    python3 tools/make_labels.py --start 1 --years 2026x9,2027x12,NDx9 --out tools/labels/CMT-001-to-030.pdf

That prints CMT-2026-001 to 009, CMT-2027-010 to 021 and CMT-ND-022 to 030. You can also list years
one by one (--years 2018,2018,ND,2021). No-date labels never go stale, so print those in bulk:

    python3 tools/make_labels.py --start 31 --count 30 --out tools/labels/CMT-ND-031-to-060.pdf

After each print, note the batch in tools/labels/LOG.md so you know the next free number.

Or list exact SKUs: --skus CMT-2018-014,CMT-ND-015

The sheet matches Avery 5160-style address labels: US Letter, 3 across by 10 down, each
1 inch by 2-5/8 inches. Print page 1 on plain paper first and hold it against a label sheet to
check the alignment, and scan one QR code with your phone, before printing on real labels.

--skip N leaves the first N label positions empty, for a sheet you have already used some of.
--outline draws each label's edge (handy for a test print, not for the real sheet).
Needs reportlab (pip install reportlab).
"""
import argparse
import os
import re
import sys

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

SITE_URL = "https://charlestalbotart.com"

# Avery 5160 geometry
COLS, ROWS = 3, 10
LABEL_W, LABEL_H = 2.625 * inch, 1.0 * inch
LEFT, TOP = 0.1875 * inch, 0.5 * inch
COL_PITCH = 2.75 * inch  # label width plus the gap between columns


def draw_qr(c, text, x, y, size):
    widget = QrCodeWidget(text)
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, x, y)


def draw_label(c, x, y, sku, outline):
    if outline:
        c.setLineWidth(0.3)
        c.setStrokeGray(0.7)
        c.roundRect(x, y, LABEL_W, LABEL_H, 4)
    pad = 0.12 * inch
    qr_size = 0.78 * inch
    draw_qr(c, f"{SITE_URL}/shop/{sku.lower()}/", x + LABEL_W - qr_size - 0.06 * inch, y + (LABEL_H - qr_size) / 2, qr_size)
    c.setFillGray(0.35)
    c.setFont("Helvetica", 5.8)
    c.drawString(x + pad, y + LABEL_H - 0.2 * inch, "CHARLES TALBOT STUDIO")
    # the SKU, as large as fits beside the QR code
    room = LABEL_W - pad - qr_size - 0.2 * inch
    size = min(19, room / stringWidth(sku, "Helvetica-Bold", 1))
    c.setFillGray(0)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x + pad, y + LABEL_H / 2 - 0.1 * inch, sku)


def build_skus(args):
    if args.skus:
        skus = [t.strip().upper() for t in args.skus.split(",") if t.strip()]
    elif args.years is not None:
        skus = []
        for token in args.years.split(","):
            t = re.match(r"^(\d{4}|ND|)(?:x(\d+))?$", token.strip(), re.IGNORECASE)
            if not t:
                sys.exit(f"{token!r} is not understood in --years (use 2026, ND, 2026x9 or NDx9)")
            yr = (t.group(1) or "ND").upper()
            for _ in range(int(t.group(2) or 1)):
                skus.append(f"CMT-{yr}-{args.start + len(skus):03d}")
    else:
        skus = [f"CMT-ND-{args.start + n:03d}" for n in range(args.count)]
    for sku in skus:
        if not re.match(r"^CMT-(\d{4}|ND)-\d{3,5}$", sku):
            sys.exit(f"{sku!r} is not a valid SKU (use CMT-2018-014 or CMT-ND-014)")
    return skus


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=1, help="first running number")
    ap.add_argument("--count", type=int, default=30, help="how many undated labels (ignored with --years or --skus)")
    ap.add_argument("--years", help='how many labels of each year, e.g. "2026x9,2027x12,NDx9" or "2018,2018,ND,2021"')
    ap.add_argument("--skus", help="exact comma-separated SKUs, e.g. CMT-2018-014,CMT-015")
    ap.add_argument("--skip", type=int, default=0, help="label positions already used on the first sheet")
    ap.add_argument("--out", required=True)
    ap.add_argument("--outline", action="store_true")
    args = ap.parse_args()

    skus = build_skus(args)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    c = canvas.Canvas(args.out, pagesize=letter)
    c.setTitle("CMT labels")
    page_h = letter[1]
    per_page = COLS * ROWS
    for n, sku in enumerate(skus):
        pos = n + args.skip
        slot = pos % per_page
        if n and slot == 0:
            c.showPage()
        col, row = slot % COLS, slot // COLS
        x = LEFT + col * COL_PITCH
        y = page_h - TOP - (row + 1) * LABEL_H
        draw_label(c, x, y, sku, args.outline)
    c.save()
    nums = [int(s.rsplit("-", 1)[1]) for s in skus]
    print(f"Wrote {args.out}: {skus[0]} ... {skus[-1]} ({len(skus)} labels). Next free number: {max(nums) + 1}"
          + (f" (first {args.skip} positions left empty)" if args.skip else "")
          + (" (explicit SKUs: check the running number yourself)" if args.skus else ""))


if __name__ == "__main__":
    main()
