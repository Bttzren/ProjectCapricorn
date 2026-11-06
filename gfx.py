"""Sprite scaling that keeps her crisp (pure Pillow, no Tk).

Her sheet cells are small (~170 px), so on high-DPI screens or at big sizes she gets stretched, and a plain
resize looks soft. resize_sharp() resizes with Lanczos (alpha-aware) and then unsharp-masks the colour
channels, more strongly the more it had to enlarge. The caller hard-cuts alpha afterwards (Windows colour-key
transparency can't do soft edges), so sharpening never creates halos.
"""
from PIL import Image, ImageFilter


def sharpen_rgb(img, percent, radius=1.3):
    """Unsharp-mask the colours of an RGBA image; alpha is untouched."""
    r, g, b, a = img.convert("RGBA").split()
    rgb = Image.merge("RGB", (r, g, b)).filter(ImageFilter.UnsharpMask(radius=radius, percent=int(percent), threshold=1))
    return Image.merge("RGBA", (*rgb.split(), a))


def strength(k):
    """Unsharp percent for a scale factor k: more when enlarging, a little when shrinking."""
    if k >= 1.0:
        return min(220, 120 + 200 * (k - 1.0))
    return 60


def resize_sharp(img, size, k=None):
    w, h = size
    if k is None:
        k = h / float(img.height)
    out = img.convert("RGBA").resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)
    return sharpen_rgb(out, strength(k), radius=1.0 + min(1.0, abs(k - 1.0)))


def sharpness(img):
    """Mean absolute difference between neighbouring opaque pixels (higher = crisper). For tests/tuning."""
    g = img.convert("RGBA")
    a = g.getchannel("A").load()
    px = g.convert("L").load()
    tot = n = 0
    for y in range(g.height - 1):
        for x in range(g.width - 1):
            if a[x, y] > 200 and a[x + 1, y] > 200 and a[x, y + 1] > 200:
                tot += abs(px[x, y] - px[x + 1, y]) + abs(px[x, y] - px[x, y + 1])
                n += 2
    return tot / n if n else 0.0
