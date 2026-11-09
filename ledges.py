"""Screen ledges: find boxes on your screen that Capri can sit on (PIL only, no Tk).

She takes a screenshot IN MEMORY, looks for the top edges of boxes (cards, text boxes, images,
panels, buttons) and throws the screenshot away. Nothing is saved to disk or sent anywhere. Her own
windows are masked out so she can't sit on herself, and scanning pauses on pages that look private
(banking, passwords, private browsing).

How it works: shrink the screenshot to grayscale, mark pixels where brightness jumps between
neighbouring rows / columns, find long horizontal runs (candidate tops) and check there are vertical
runs going down from both ends (so it's really a box, not a line of text).
"""
import re
import threading

from PIL import Image, ImageChops, ImageDraw, ImageFilter

TRANSPOSE = getattr(Image, "Transpose", Image).TRANSPOSE
TH = 22                 # brightness jump that counts as an edge
SMALL_W = 640           # screenshots are shrunk to this width before analysis
MIN_W = 170             # narrowest ledge, in screen pixels
MIN_V = 28              # shortest vertical side that makes it a box, in screen pixels
MAX_LEDGES = 12
SENSITIVE = ("password", "passcode", "bank", "banking", "1password", "bitwarden", "keepass", "lastpass",
             "sign in", "sign-in", "log in", "login", "incognito", "private browsing", "inprivate",
             "wallet", "paypal", "checkout")


def should_scan(title):
    """False when the front window looks private. Nothing is analysed then."""
    t = (title or "").lower()
    return not any(k in t for k in SENSITIVE)


def capture():
    """Screenshot of the screen as a PIL image, or None if this system won't allow it."""
    try:
        from PIL import ImageGrab
        return ImageGrab.grab()
    except Exception:
        return None


_FRAGMENT = re.compile(b"\\xff+")


def _runs(img, minlen, max_density=0.45):
    """[(row, start, end)] of long horizontal runs of white pixels in a binary 'L' image."""
    w, h = img.size
    data = img.tobytes()
    pat = re.compile(b"\\xff{" + str(minlen).encode() + b",}")
    out = []
    for y in range(h):
        row = data[y * w:(y + 1) * w]
        # busy texture (photo, noise) = lots of edge pixels in lots of separate fragments. A wide box top
        # also fills much of a row but is ONE long run, so density alone must not reject it.
        if row.count(b"\xff") > max_density * w and len(_FRAGMENT.findall(row)) > 8:
            continue
        for m in pat.finditer(row):
            out.append((y, m.start(), m.end()))
    return out


def _group(runs, gap=2, overlap=0.6):
    """Merge runs on neighbouring rows that cover the same span into one group {y0, y1, x0, x1}."""
    groups = []
    for y, a, b in sorted(runs):
        for g in groups:
            if y - g["y1"] > gap:
                continue
            ov = min(b, g["x1"]) - max(a, g["x0"])
            if ov >= overlap * min(b - a, g["x1"] - g["x0"]):
                g["y1"], g["x0"], g["x1"] = y, min(a, g["x0"]), max(b, g["x1"])
                break
        else:
            groups.append({"y0": y, "y1": y, "x0": a, "x1": b})
    return groups


def _edge_map(small, dx, dy):
    diff = ImageChops.difference(small, ImageChops.offset(small, dx, dy))
    return diff.point(lambda v: 255 if v > TH else 0)


def detect(image, masks=(), screen=None, raw=False):
    """Ledges found in `image`: [{'l', 't', 'r', 'kind'}] in screen coordinates ('box' or 'edge').
    raw=True returns (ledges, every horizontal edge found) - the second list lets a ledge she's sitting on
    survive while her own body hides its corner.

    masks: [(x, y, w, h)] screen rectangles to ignore (Capri's own windows).
    screen: (width, height) of the screen in the coordinates you want back (defaults to the image size).
    """
    W, H = image.size
    sw, sh = screen or (W, H)
    k = min(1.0, SMALL_W / float(W))
    gray = image.convert("L")
    small = gray if k == 1.0 else gray.resize((max(1, int(W * k)), max(1, int(H * k))), Image.BOX)
    w, h = small.size
    sc = w / float(sw)                                    # small pixels per screen pixel
    hmap, vmap = _edge_map(small, 0, 1), _edge_map(small, 1, 0)
    mboxes = []
    for m in masks:                                       # forget edges inside her own windows
        x, y, mw, mh = m
        box = [int((x - 4) * sc), int((y - 4) * sc), int((x + mw + 4) * sc) + 1, int((y + mh + 4) * sc) + 1]
        mboxes.append(box)
        for mp in (hmap, vmap):
            ImageDraw.Draw(mp).rectangle(box, fill=0)

    def behind_her(x, y):
        """An edge that stops exactly where her own window starts may well go on behind her: returns where it
        would come out on her other side (or None)."""
        for b in mboxes:
            if b[1] <= y <= b[3]:
                if abs(x - b[0]) <= 3:
                    return b[2]
                if abs(x - b[2]) <= 3:
                    return b[0]
        return None
    hmap, vmap = hmap.filter(ImageFilter.MaxFilter(3)), vmap.filter(ImageFilter.MaxFilter(3))
    hgroups = _group(_runs(hmap, max(8, int(MIN_W * sc))))
    minv = max(6, int(MIN_V * sc))
    vgroups = _group(_runs(vmap.transpose(TRANSPOSE), minv))     # rows here are original columns

    def side(x):
        """The vertical groups sitting at column x: [(top, bottom)]."""
        return [(v["x0"], v["x1"]) for v in vgroups if v["y0"] - 3 <= x <= v["y1"] + 3]

    found = []
    for g in hgroups:
        top, xl, xr = g["y0"], g["x0"], g["x1"]
        hidden_l, hidden_r = behind_her(xl, top), behind_her(xr, top)
        has = [hid is not None or any(abs(t - top) <= 4 and b - top >= minv for t, b in side(x))
               for x, hid in ((xl, hidden_l), (xr, hidden_r))]
        if hidden_l is not None and hidden_l < xl:      # it continues behind her: count that part too, so the
            xl = hidden_l                               # spot she's sitting on is still part of the ledge
        if hidden_r is not None and hidden_r > xr:
            xr = hidden_r
        found.append({"l": xl / sc, "t": top / sc, "r": xr / sc, "kind": "box" if all(has) else "edge"})
    all_runs = list(found)
    keep = [f for f in found if f["kind"] == "box" or (f["r"] - f["l"]) >= 0.4 * sw]
    out = []
    for f in sorted(keep, key=lambda d: (d["kind"] != "box", -(d["r"] - d["l"]))):
        dup = False
        for o in out:                                     # double borders / shadows: keep the wider one
            ov = min(f["r"], o["r"]) - max(f["l"], o["l"])
            if abs(f["t"] - o["t"]) <= 6 and ov >= 0.7 * min(f["r"] - f["l"], o["r"] - o["l"]):
                dup = True
                break
        if not dup and f["t"] > 20:
            out.append(f)
    return (out[:MAX_LEDGES], all_runs) if raw else out[:MAX_LEDGES]


def hold(prev, new, runs, keep_id, min_visible=MIN_W * 0.5):
    """The ledge she's sitting on (keep_id) vanished from this scan? Her own window hides part of it (it's
    masked out), which can make it stop looking like a box. Keep it if some of that edge is still visibly
    there (any horizontal run at the same height overlapping it); if the window closed or moved, it isn't."""
    if not keep_id or any(d.get("id") == keep_id for d in new):
        return new
    old = next((d for d in prev if d.get("id") == keep_id), None)
    if old is None:
        return new
    for r in runs or ():
        ov = min(r["r"], old["r"]) - max(r["l"], old["l"])
        if abs(r["t"] - old["t"]) <= 6 and ov >= min_visible:
            return new + [old]
    return new


def track(prev, new, counter):
    """Give detections stable ids so she can follow a ledge that scrolls or a window that moves. Returns
    (ledges, counter). Pairs are chosen globally, closest first, and a box top prefers a box top (after a
    window moves, its title bar's lower line can be closer than its new top)."""
    pairs = []
    for i, n in enumerate(new):
        for j, p in enumerate(prev):
            ov = min(p["r"], n["r"]) - max(p["l"], n["l"])
            narrow = min(p["r"] - p["l"], n["r"] - n["l"])
            dy = abs(p["t"] - n["t"])
            if narrow > 0 and ov >= 0.5 * narrow and dy <= 160:
                cost = dy + (0 if p.get("kind") == n.get("kind") else 40)
                pairs.append((cost, i, j))
    taken_new, taken_old, ids = set(), set(), {}
    for cost, i, j in sorted(pairs):
        if i in taken_new or j in taken_old:
            continue
        taken_new.add(i)
        taken_old.add(j)
        ids[i] = prev[j]["id"]
    out = []
    for i, n in sorted(enumerate(new), key=lambda kv: -(kv[1]["r"] - kv[1]["l"])):
        if i not in ids:
            counter += 1
            ids[i] = f"L{counter}"
        out.append(dict(n, id=ids[i]))
    return out, counter


class Scanner:
    """Runs capture + detect on a background thread so the pet never stutters."""

    def __init__(self, capture=capture, detect=detect, threaded=True):
        self.capture, self.detect, self.threaded = capture, detect, threaded
        self.result, self.error, self._thread, self.runs = None, "", None, None

    @property
    def busy(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, masks, screen):
        if self.busy:
            return False
        if not self.threaded:
            self._run(masks, screen)
            return True
        self._thread = threading.Thread(target=self._run, args=(masks, screen), daemon=True)
        self._thread.start()
        return True

    def _run(self, masks, screen):
        try:
            img = self.capture()
            if img is None:
                self.error = "can't capture the screen here"
                return
            res = self.detect(img, masks, screen)
            self.result, self.runs = res if isinstance(res, tuple) else (res, None)
            del img                                        # the screenshot is gone as soon as we're done
        except Exception as exc:
            self.error = type(exc).__name__

    def take(self):
        r, self.result = self.result, None
        return r
