"""Neon look: a crisp accent-colour outline and speed ghosts (PIL only, no Tk).

Everything is fully opaque or fully clear (no soft edges) because Windows transparency uses a colour key
and any soft pixel would leave a pink halo.
"""
from PIL import Image, ImageChops, ImageFilter

COLORS = {"cyan": (0, 240, 255), "magenta": (255, 43, 214), "yellow": (252, 238, 10), "green": (57, 255, 149),
          "red": (255, 51, 85), "white": (240, 240, 255)}


def hex_of(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def outline(img, rgb, px=2):
    """`img` with a solid `px`-wide rim of `rgb` painted just outside its opaque pixels."""
    img = img.convert("RGBA")
    a = img.split()[3].point(lambda v: 255 if v > 127 else 0)
    grown = a.filter(ImageFilter.MaxFilter(2 * max(1, int(px)) + 1))
    rim = Image.new("RGBA", img.size, tuple(rgb) + (255,))
    base = Image.new("RGBA", img.size, (0, 0, 0, 0))
    base.paste(rim, (0, 0), grown)
    base.paste(img, (0, 0), a)
    return base


def ghost(img, rgb, level=1):
    """A tinted, see-through-looking copy: level 1 keeps a checkerboard of pixels, 2 keeps one in four."""
    img = img.convert("RGBA")
    w, h = img.size
    a = img.split()[3].point(lambda v: 255 if v > 127 else 0)
    if level <= 1:
        row = [bytes((255 if (x + y) % 2 == 0 else 0) for x in range(w)) for y in range(h)]
    else:
        row = [bytes((255 if (x % 2 == 0 and y % 2 == 0) else 0) for x in range(w)) for y in range(h)]
    pattern = Image.frombytes("L", (w, h), b"".join(row))
    mask = ImageChops.multiply(a, pattern)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(Image.new("RGBA", img.size, tuple(rgb) + (255,)), (0, 0), mask)
    return out
