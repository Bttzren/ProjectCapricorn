"""Palette-swap skins for the sprite sheet (PIL only, no Tk). Alpha is never touched."""
from PIL import Image, ImageOps

IDS = ("neon", "ocean", "acid", "chrome", "gold")


def _grade(sheet, black, mid, white):
    r, g, b, a = sheet.split()
    gray = ImageOps.grayscale(Image.merge("RGB", (r, g, b)))
    col = ImageOps.colorize(gray, black=black, mid=mid, white=white).convert("RGB")
    return Image.merge("RGBA", (*col.split(), a))


def apply(sheet, skin):
    """Recolor an RGBA sheet. Unknown skin ids leave it unchanged."""
    sheet = sheet.convert("RGBA")
    r, g, b, a = sheet.split()
    if skin == "ocean":                       # swap red <-> blue
        return Image.merge("RGBA", (b, g, r, a))
    if skin == "acid":                        # swap red <-> green
        return Image.merge("RGBA", (g, r, b, a))
    if skin == "chrome":
        return _grade(sheet, (6, 8, 22), (70, 140, 165), (215, 248, 255))
    if skin == "gold":
        return _grade(sheet, (22, 10, 0), (190, 110, 0), (255, 232, 130))
    return sheet
