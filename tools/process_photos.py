#!/usr/bin/env python3
"""Clean up photos of work for the website, and write a before/after sheet to check them.

    python3 tools/process_photos.py --kind pot --out inbox/out inbox/bowl/*.HEIC
    python3 tools/process_photos.py --kind painting --out inbox/out inbox/painting.jpg

Edits are limited to what a careful photographer would do by hand, so glaze color and form are
not misrepresented: no generative "enhance", no retouching of the work itself.

  pot       white balance and exposure taken from the backdrop (the bright, nearly gray pixels
            around the edge of the frame), then cropped to the piece with even margins.
            If no neutral backdrop is found (wood, colored paper) the color is left as shot.
  painting  finds the canvas edge, corrects the perspective and crops to it. Color is left as
            shot unless --gray marks a neutral patch (a gray card) to balance from.
  none      only orientation, color profile, size and metadata.

Every kind: EXIF rotation applied, colors converted to sRGB (iPhone photos are Display P3),
all metadata (GPS, camera, dates) dropped, at most 1800px on the long edge, light sharpening,
JPEG quality 85. --cover crops to a fixed 4:5 for grid covers. Originals are never changed.

The sheet (<out>/sheet.jpg) shows each photo before and after, with what was done. Nothing is
published: look at the sheet, then copy what you want into images/ and run python3 build.py.
Needs the packages in tools/requirements.txt (pip install -r tools/requirements.txt).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:  # HEIC files then fail to open with a clear message below
    pillow_heif = None

LONGEST = 1800
QUALITY = 85
BACKDROP_TARGET = 244   # backdrop gray after balancing (0-255); bright but not blown out
MAX_GAIN = 1.35         # never push a channel or the exposure further than this
MARGIN = 0.10           # space around a pot, as a fraction of the crop's long side
SRGB = ImageCms.createProfile("sRGB")


def load(src):
    """Open, rotate upright and convert to sRGB. Metadata is not carried over."""
    if src.lower().endswith((".heic", ".heif")) and pillow_heif is None:
        sys.exit("HEIC photos need pillow-heif: pip install -r tools/requirements.txt")
    im = ImageOps.exif_transpose(Image.open(src))
    icc = im.info.get("icc_profile")
    if icc:
        src_profile = ImageCms.ImageCmsProfile(__import__("io").BytesIO(icc))
        im = ImageCms.profileToProfile(im.convert("RGB"), src_profile, SRGB,
                                       renderingIntent=ImageCms.Intent.PERCEPTUAL, outputMode="RGB")
    im = im.convert("RGB")
    im.info = {}  # pixels are sRGB now; do not let the source profile or EXIF follow them out
    return im


def to_linear(a):
    a = a / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def to_srgb(a):
    a = np.clip(a, 0, 1)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055) * 255.0


def apply_gains(im, gains):
    """Scale each channel in linear light, which is what a white-balance/exposure change is."""
    a = to_linear(np.asarray(im, dtype=np.float32))
    return Image.fromarray(to_srgb(a * np.asarray(gains, dtype=np.float32)).round().astype(np.uint8))


def gains_for(rgb, target=BACKDROP_TARGET):
    """Per-channel linear gains that turn this color into a neutral gray of the target level."""
    lin = to_linear(np.asarray(rgb, dtype=np.float64))
    want = to_linear(np.array([target] * 3, dtype=np.float64))
    return np.clip(want / np.maximum(lin, 1e-4), 1 / MAX_GAIN, MAX_GAIN)


def backdrop_color(im):
    """Median color of the bright, low-saturation pixels in a band around the frame, or None."""
    a = np.asarray(im.resize((300, int(300 * im.height / im.width))), dtype=np.float32)
    h, w = a.shape[:2]
    band = np.zeros((h, w), bool)
    bh, bw = max(1, h // 12), max(1, w // 12)
    band[:bh], band[-bh:], band[:, :bw], band[:, -bw:] = True, True, True, True
    px = a[band]
    mx, mn = px.max(1), px.min(1)
    ok = (mx > 150) & ((mx - mn) / np.maximum(mx, 1) < 0.12)
    if ok.mean() < 0.5:  # most of the border is not a light neutral backdrop
        return None
    return np.median(px[ok], axis=0)


def subject_box(im, bg):
    """Bounding box of everything that differs clearly from the backdrop, in full-size pixels."""
    scale = 600 / max(im.size)
    small = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))))
    a = np.asarray(small.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    diff = np.abs(a - np.asarray(bg, dtype=np.float32)).max(2)
    mask = diff > 28
    # drop rows/columns with only a few stray pixels (dust, sweep seams, vignetting)
    rows = np.where(mask.sum(1) > max(3, mask.shape[1] * 0.01))[0]
    cols = np.where(mask.sum(0) > max(3, mask.shape[0] * 0.01))[0]
    if not len(rows) or not len(cols):
        return None
    box = cols[0], rows[0], cols[-1] + 1, rows[-1] + 1
    return tuple(round(v / scale) for v in box)


def fit_box(box, size, aspect, margin=MARGIN):
    """Grow a subject box by the margin and to the aspect ratio (w/h), kept inside the image."""
    W, H = size
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0), (y1 - y0)
    w, h = w / (1 - 2 * margin), h / (1 - 2 * margin)
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    if w > W or h > H:  # cannot fit with full margins: largest crop of that aspect instead
        s = min(W / w, H / h)
        w, h = w * s, h * s
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h / 2, 0), H - h)
    return round(x0), round(y0), round(x0 + w), round(y0 + h)


def find_canvas(im):
    """Corners of the largest four-sided shape filling much of the frame (the painting), or None."""
    import cv2
    scale = 1000 / max(im.size)
    small = np.asarray(im.resize((round(im.width * scale), round(im.height * scale))))
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY), (5, 5), 0)
    edges = cv2.dilate(cv2.Canny(gray, 30, 90), np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    area = small.shape[0] * small.shape[1]
    best = None
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
        if cv2.contourArea(c) < 0.25 * area:
            break
        quad = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(quad) == 4 and cv2.isContourConvex(quad):
            best = quad.reshape(4, 2) / scale
            break
    if best is None:
        return None
    s, d = best.sum(1), np.diff(best, axis=1).ravel()
    return np.array([best[s.argmin()], best[d.argmin()], best[s.argmax()], best[d.argmax()]], np.float32)


def warp_canvas(im, corners):
    import cv2
    tl, tr, br, bl = corners
    w = round(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    h = round(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
    m = cv2.getPerspectiveTransform(corners, dst)
    out = cv2.warpPerspective(np.asarray(im), m, (w, h), flags=cv2.INTER_LANCZOS4)
    inset = max(2, round(min(w, h) * 0.004))  # trim the last sliver of wall or frame edge
    return Image.fromarray(out).crop((inset, inset, w - inset, h - inset))


def region_color(im, frac_box):
    x0, y0, x1, y1 = (round(f * s) for f, s in zip(frac_box, (im.width, im.height) * 2))
    return np.median(np.asarray(im.crop((x0, y0, x1, y1))).reshape(-1, 3), axis=0)


def process(src, kind="pot", cover=False, gray=None, rotate=0.0, crop=True):
    """Return (edited image, before image, list of notes saying what was done)."""
    before = load(src)
    im, notes = before, []
    if rotate:
        bg = backdrop_color(im)
        fill = tuple(int(v) for v in bg) if bg is not None else (255, 255, 255)
        im = im.rotate(-rotate, Image.BICUBIC, expand=False, fillcolor=fill)
        notes.append(f"rotated {rotate:+.1f} deg")

    if gray:
        g = gains_for(region_color(im, gray), target=200)  # a gray card sits well below the backdrop
        im = apply_gains(im, g)
        notes.append("balanced from gray patch " + gains_text(g))

    if kind == "pot":
        bg = backdrop_color(im)
        if bg is None:
            notes.append("no neutral backdrop found: color left as shot, not cropped")
        else:
            if not gray:
                g = gains_for(bg)
                im = apply_gains(im, g)
                bg = backdrop_color(im)
                notes.append("backdrop balanced " + gains_text(g))
            box = subject_box(im, bg) if crop else None
            if box:
                aspect = 4 / 5 if cover else im.width / im.height
                c = fit_box(box, im.size, aspect)
                if c != (0, 0, im.width, im.height):
                    im = im.crop(c)
                    notes.append(f"cropped to piece, {c[2] - c[0]}x{c[3] - c[1]}")
            elif crop:
                notes.append("piece not found against backdrop: not cropped")
    elif kind == "painting":
        corners = find_canvas(im) if crop else None
        if corners is not None:
            im = warp_canvas(im, corners)
            notes.append(f"canvas squared and cropped, {im.width}x{im.height}")
        elif crop:
            notes.append("canvas edge not found: not cropped")
    if cover and abs(im.width / im.height - 4 / 5) > 0.005:
        w, h = min(im.width, round(im.height * 4 / 5)), min(im.height, round(im.width * 5 / 4))
        im = ImageOps.fit(im, (w, h), Image.LANCZOS)
        notes.append("center-cropped to 4:5")

    im = finish(im)
    if max(before.size) < LONGEST:
        notes.append(f"source only {max(before.size)}px: not enlarged")
    return im, before, notes


def finish(im):
    if max(im.size) > LONGEST:
        im = im.copy()
        im.thumbnail((LONGEST, LONGEST), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))


def gains_text(g):
    r, gr, b = g
    exp = np.log2((r + gr + b) / 3)
    return f"(exposure {exp:+.2f} stops, R x{r / gr:.2f} B x{b / gr:.2f})"


def save(im, dst, quality=QUALITY, webp=False):
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)  # no EXIF written
    if webp:
        im.save(os.path.splitext(dst)[0] + ".webp", "WEBP", quality=80, method=6)
    return im.size


def contact_sheet(rows, dst, cell=520):
    """rows: (name, before, after, notes). Before on the left, after on the right."""
    pad, text_h = 12, 54
    sheet = Image.new("RGB", (2 * cell + 3 * pad, len(rows) * (cell + text_h + pad) + pad), "white")
    d = ImageDraw.Draw(sheet)
    for i, (name, before, after, notes) in enumerate(rows):
        y = pad + i * (cell + text_h + pad)
        for j, im in enumerate((before, after)):
            t = im.copy()
            t.thumbnail((cell, cell))
            x = pad + j * (cell + pad)
            sheet.paste(t, (x + (cell - t.width) // 2, y + (cell - t.height) // 2))
        d.text((pad, y + cell + 4), f"{name}   before | after", fill="black")
        d.text((pad, y + cell + 20), "; ".join(notes) or "resized and cleaned only", fill=(90, 90, 90))
    sheet.save(dst, "JPEG", quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photos", nargs="+")
    ap.add_argument("--out", required=True, help="folder for the edited photos and sheet.jpg")
    ap.add_argument("--kind", choices=("pot", "painting", "none"), default="pot")
    ap.add_argument("--cover", action="store_true", help="crop to 4:5 for a grid cover")
    ap.add_argument("--gray", help="neutral patch as fractions of the frame: left,top,right,bottom")
    ap.add_argument("--rotate", type=float, default=0.0, help="straighten by this many degrees (clockwise)")
    ap.add_argument("--no-crop", dest="crop", action="store_false")
    ap.add_argument("--names", choices=("keep", "number"), default="number",
                    help="number: 01.jpg, 02.jpg, ... in the order given (default); keep: original names")
    ap.add_argument("--webp", action="store_true", help="also write a .webp next to each JPEG")
    args = ap.parse_args()
    gray = tuple(float(v) for v in args.gray.split(",")) if args.gray else None

    rows = []
    for n, src in enumerate(args.photos, 1):
        im, before, notes = process(src, args.kind, args.cover, gray, args.rotate, args.crop)
        base = os.path.splitext(os.path.basename(src))[0] if args.names == "keep" else f"{n:02d}"
        dst = os.path.join(args.out, base + ".jpg")
        save(im, dst, webp=args.webp)
        rows.append((f"{os.path.basename(src)} -> {os.path.basename(dst)}", before, im, notes))
        print(f"{dst}: " + ("; ".join(notes) or "resized and cleaned only"))
    sheet = os.path.join(args.out, "sheet.jpg")
    contact_sheet(rows, sheet)
    print(f"Check {sheet} before using these photos.")


if __name__ == "__main__":
    main()
