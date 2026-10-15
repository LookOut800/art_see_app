#!/usr/bin/env python3
"""Make a printable sheet of SKU labels with a QR code that opens the piece's page.

    python3 tools/make_labels.py --year 2026 --start 1 --count 30 --out tools/labels/CMT-2026-001-to-030.pdf

The sheet matches Avery 5160-style address labels: US Letter, 3 across by 10 down, each
1 inch by 2-5/8 inches. Print page 1 on plain paper first and hold it against a label sheet
to check the alignment, and scan one QR code with your phone, before printing on real labels.
Use --outline to draw each label's edge (handy for a test print, not for the real sheet).
Needs reportlab (pip install reportlab).
"""
import argparse
import os

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
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
    c.drawString(x + pad, y + LABEL_H - 0.22 * inch, "CHARLES TALBOT STUDIO")
    c.setFillGray(0)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x + pad, y + LABEL_H / 2 - 0.07 * inch, sku)
    c.setFillGray(0.35)
    c.setFont("Helvetica", 6.4)
    c.drawString(x + pad, y + 0.16 * inch, "charlestalbotart.com")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True, help="the year in the SKU (the year you catalogue the pieces)")
    ap.add_argument("--start", type=int, default=1, help="first running number")
    ap.add_argument("--count", type=int, default=30, help="how many labels")
    ap.add_argument("--out", required=True)
    ap.add_argument("--outline", action="store_true")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    c = canvas.Canvas(args.out, pagesize=letter)
    c.setTitle(f"CMT-{args.year} labels")
    page_h = letter[1]
    per_page = COLS * ROWS
    for n in range(args.count):
        slot = n % per_page
        if n and slot == 0:
            c.showPage()
        col, row = slot % COLS, slot // COLS
        x = LEFT + col * COL_PITCH
        y = page_h - TOP - (row + 1) * LABEL_H
        draw_label(c, x, y, f"CMT-{args.year}-{args.start + n:03d}", args.outline)
    c.save()
    last = args.start + args.count - 1
    print(f"Wrote {args.out}: CMT-{args.year}-{args.start:03d} to CMT-{args.year}-{last:03d}")


if __name__ == "__main__":
    main()
