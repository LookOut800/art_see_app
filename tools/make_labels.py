#!/usr/bin/env python3
"""Make a printable sheet of SKU labels with a QR code that opens the piece's page.

One running number covers every piece. The year is added only when you know when it was made:

    CMT-2018-014   made in 2018
    CMT-ND-015     no date known (ND = no date; the label has a blank "made ____" line to fill in later)

Print a batch where you say each piece's year, in order (a blank means unknown):

    python3 tools/make_labels.py --start 14 --years 2018,2018,,2021,, --out tools/labels/batch.pdf

That prints CMT-2018-014, CMT-2018-015, CMT-ND-016, CMT-2021-017, CMT-ND-018, CMT-ND-019. Or print undated
labels in bulk (they never go stale):

    python3 tools/make_labels.py --start 1 --count 30 --out tools/labels/CMT-ND-001-to-030.pdf

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
    c.drawString(x + pad, y + LABEL_H / 2 - 0.07 * inch, sku)
    if not re.match(r"^CMT-\d{4}-", sku):
        # no year in the SKU (ND): a blank line to write it in by hand (or "c. 2018")
        c.setFillGray(0.35)
        c.setFont("Helvetica", 7)
        c.drawString(x + pad, y + 0.15 * inch, "made")
        c.setLineWidth(0.5)
        c.setStrokeGray(0.45)
        c.line(x + pad + 0.3 * inch, y + 0.14 * inch, x + pad + 1.3 * inch, y + 0.14 * inch)


def build_skus(args):
    if args.skus:
        skus = [t.strip().upper() for t in args.skus.split(",") if t.strip()]
    elif args.years is not None:
        skus = []
        for i, yr in enumerate(args.years.split(",")):
            yr = yr.strip()
            skus.append(f"CMT-{yr or 'ND'}-{args.start + i:03d}")
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
    ap.add_argument("--years", help='comma-separated year made for each piece in order, blank if unknown, e.g. "2018,2018,,2021"')
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
    print(f"Wrote {args.out}: {', '.join(skus[:6])}" + (" ..." if len(skus) > 6 else "")
          + (f" (first {args.skip} positions left empty)" if args.skip else ""))


if __name__ == "__main__":
    main()
