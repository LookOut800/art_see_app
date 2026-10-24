#!/usr/bin/env python3
"""Clean up photos of work for the website, and write a before/after sheet to check them.

    python3 tools/process_photos.py --kind pot --out inbox/out inbox/bowl/*.HEIC
    python3 tools/process_photos.py --kind painting --out inbox/out inbox/painting.jpg

Edits are limited to what a careful photographer would do by hand, so glaze color and form are
not misrepresented: no generative "enhance", no retouching of the work itself.

  pot       on a white or gray backdrop (even one that falls off to dark at the top), white
            balance and exposure are set so its best-lit part reads as clean white; then the
            photo is cropped to the piece with even margins. A colored backdrop (blue paper,
            wood, a painted wall) is left as shot and only cropped.
  painting  finds the edge of the canvas (or, for drawing, the sheet of paper), corrects the
  drawing   perspective and crops to it, but only when the edge is clear; otherwise it is left
            uncropped. Color is left as shot unless --gray marks a neutral patch (a gray card).
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
MAX_EXPOSURE = 1.7      # never brighten or darken by more than this (about 3/4 stop)
MAX_TINT = 1.35         # nor shift red or blue against green by more than this
HIGHLIGHT_KNEE = 0.8    # linear level above which brightened highlights are compressed, not clipped
MARGIN = 0.12           # space around a pot, as a fraction of the crop
HEADROOM = 0.53         # where the middle of the pot sits, from the top of the crop (a little low)
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
    a = to_linear(np.asarray(im, dtype=np.float32)) * np.asarray(gains, dtype=np.float32)
    # roll off the top instead of clipping, so white glaze and highlights keep their detail
    k = HIGHLIGHT_KNEE
    a = np.where(a > k, k + (1 - k) * np.tanh((a - k) / (1 - k)), a)
    return Image.fromarray(to_srgb(a).round().astype(np.uint8))


def gains_for(rgb, target=BACKDROP_TARGET):
    """Per-channel linear gains that turn this color into a neutral gray of the target level."""
    lin = to_linear(np.asarray(rgb, dtype=np.float64))
    want = to_linear(np.array([target] * 3, dtype=np.float64))
    g = want / np.maximum(lin, 1e-4)
    tint = np.clip(g / g[1], 1 / MAX_TINT, MAX_TINT)  # capped separately, so a big exposure
    return tint * np.clip(g[1], 1 / MAX_EXPOSURE, MAX_EXPOSURE)  # change keeps the color fix


def backdrop_color(im):
    """Color of the brightest part of a white or gray backdrop, or None for a colored one.

    Looks at a band around the frame. A white sweep that falls off to gray or near black at the
    top still counts: its best-lit part (usually the floor in front of the piece) is what should
    read as clean white. A backdrop with a lot of clearly colored pixels (a blue gradient, wood,
    a painted wall) is a deliberate color and returns None."""
    a = np.asarray(im.resize((300, int(300 * im.height / im.width))), dtype=np.float32)
    h, w = a.shape[:2]
    band = np.zeros((h, w), bool)
    bh, bw = max(1, h // 12), max(1, w // 12)
    band[:bh], band[-bh:], band[:, :bw], band[:, -bw:] = True, True, True, True
    px = a[band]
    mx, mn = px.max(1), px.min(1)
    sat = (mx - mn) / np.maximum(mx, 1)
    if (sat > 0.22).mean() > 0.3:
        return None
    light = px[(sat < 0.2) & (mx > 120)]
    if len(light) < 0.3 * len(px):
        return None
    lum = light.mean(1)
    return np.median(light[lum >= np.percentile(lum, 80)], axis=0)


def subject_box(im):
    """Bounding box of everything that differs clearly from the backdrop, in full-size pixels.

    The backdrop is modelled row by row from the left and right edges of the frame, so a sweep
    or a gradient that darkens toward the top still counts as backdrop."""
    scale = 600 / max(im.size)
    small = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))))
    a = np.asarray(small.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    edge = max(2, a.shape[1] // 25)
    row_bg = np.median(np.concatenate([a[:, :edge], a[:, -edge:]], axis=1), axis=1)
    mask = np.abs(a - row_bg[:, None, :]).max(2) > 28
    # drop rows/columns with only a few stray pixels (dust, sweep seams, vignetting)
    rows = np.where(mask.sum(1) > max(3, mask.shape[1] * 0.01))[0]
    cols = np.where(mask.sum(0) > max(3, mask.shape[0] * 0.01))[0]
    if not len(rows) or not len(cols):
        return None
    box = cols[0], rows[0], cols[-1] + 1, rows[-1] + 1
    return tuple(round(v / scale) for v in box)


def frame_for(box):
    """The crop shape (w/h) that suits the piece: 4:5 for tall ones, square, or 4:3 for wide
    bowls and groups."""
    w, h = box[2] - box[0], box[3] - box[1]
    return 4 / 3 if w / h > 1.25 else 1.0 if w / h > 0.85 else 4 / 5


def fit_box(box, size, aspect, margin=MARGIN):
    """Grow a subject box by the margin and to the aspect ratio (w/h), kept inside the image.
    The piece is centered left to right and sits a little low, with more room above it."""
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
    room = 2 * min(cx, W - cx)  # widest crop still centered on the piece
    if w > room:  # near the edge of the photo: narrower margins rather than an off-center piece
        w = max(room, (x1 - x0) * 1.04)
        h = min(max(w / aspect, (y1 - y0) * 1.04), H)
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h * HEADROOM, 0), H - h)
    return round(x0), round(y0), round(x0 + w), round(y0 + h)


def find_canvas(im):
    """Corners (tl, tr, br, bl) of the canvas or sheet of paper, or None when unsure.

    GrabCut separates the work (the middle of the frame) from what surrounds it, and the outline
    of that region is reduced to four corners. It is only trusted when the result looks like a
    flat rectangle shot head-on: corners within 5 degrees of square and not running along the
    edge of the photo (a sheet that fills the frame, or a bent sketchbook page, is left alone)."""
    import cv2
    scale = 1000 / max(im.size)
    small = np.asarray(im.resize((round(im.width * scale), round(im.height * scale))))
    h, w = small.shape[:2]
    mask = np.full((h, w), cv2.GC_PR_FGD, np.uint8)
    b = max(4, round(min(h, w) * 0.02))
    mask[:b], mask[-b:], mask[:, :b], mask[:, -b:] = (cv2.GC_PR_BGD,) * 4
    mask[h // 4:3 * h // 4, w // 4:3 * w // 4] = cv2.GC_FGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mask, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    fg = cv2.morphologyEx(np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8),
                          cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if not 0.2 < cv2.contourArea(c) / (h * w) < 0.97:
        return None
    hull = cv2.convexHull(c)
    for eps in (0.01, 0.02, 0.03, 0.05):
        quad = cv2.approxPolyDP(hull, eps * cv2.arcLength(hull, True), True)
        if len(quad) == 4:
            break
    else:
        return None
    if cv2.contourArea(c) / cv2.contourArea(quad) < 0.9:  # only roughly four-sided
        return None
    q = quad.reshape(4, 2).astype(np.float32)
    s, d = q.sum(1), np.diff(q, axis=1).ravel()
    q = np.array([q[s.argmin()], q[d.argmin()], q[s.argmax()], q[d.argmax()]], np.float32)
    for i in range(4):
        v1, v2 = q[i - 1] - q[i], q[(i + 1) % 4] - q[i]
        angle = np.degrees(np.arccos(np.dot(v1, v2) / np.linalg.norm(v1) / np.linalg.norm(v2)))
        if abs(angle - 90) > 5:
            return None
    near_edge = sum(min(x, w - x) < 0.01 * w for x in q[:, 0]) + sum(min(y, h - y) < 0.01 * h for y in q[:, 1])
    if near_edge > 2:
        return None
    return q / scale


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


def date_taken(src):
    """When the photo was taken, as YYYY-MM-DD from its EXIF, or "" if it does not say.

    Read from the original before the metadata is dropped, so a web copy can still be traced
    to a date (often, but not always, around when the piece was made)."""
    try:
        exif = Image.open(src).getexif()
        when = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal, else DateTime
    except Exception:
        return ""
    return when[:10].replace(":", "-") if when and when[:4].isdigit() else ""


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
        if gray:
            pass
        elif bg is None:
            notes.append("colored backdrop: color left as shot")
        else:
            g = gains_for(bg)
            im = apply_gains(im, g)
            notes.append("backdrop balanced " + gains_text(g))
        box = subject_box(im) if crop else None
        if box:
            aspect = 4 / 5 if cover else frame_for(box)
            c = fit_box(box, im.size, aspect)
            if c != (0, 0, im.width, im.height):
                im = im.crop(c)
                notes.append(f"cropped to piece, {c[2] - c[0]}x{c[3] - c[1]}")
        elif crop:
            notes.append("piece not found against backdrop: not cropped")
    elif kind in ("painting", "drawing"):
        corners = find_canvas(im) if crop else None
        if corners is not None:
            im = warp_canvas(im, corners)
            notes.append(f"squared up and cropped to the edge, {im.width}x{im.height}")
        elif crop:
            notes.append("edge of the work not found clearly: not cropped")
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
    ap.add_argument("--kind", choices=("pot", "painting", "drawing", "none"), default="pot")
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
