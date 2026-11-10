"""Cyberpunk widgets for the chat and settings windows: sharp edges, 1px neon borders, monospace type.

Only tkinter. THEME['acc'] is the accent colour (the neon colour she uses); windows read it when they are built.
"""
import tkinter as tk
from tkinter import font as tkfont

THEME = {"acc": "#05f56f", "acc2": "#ff2bd6", "warn": "#fcee0a", "err": "#fb0948"}
BG, PANEL, PANEL2, LINE = "#07060f", "#0d0b1a", "#14112b", "#2a2547"
TEXT, DIM, BLACK = "#eaf6ff", "#7f7ca0", "#05040a"


def blend(c1, c2, t):
    """Mix two #rrggbb colours: t=0 gives c1, t=1 gives c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def mono_font(root):
    have = set(tkfont.families(root))
    for name in ("Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"):
        if name in have:
            return name
    return "Courier"


def acc():
    return THEME["acc"]


# ------------------------------------------------------------------ buttons
def button(parent, text, command, font, filled=False, color=None, padx=10, pady=4):
    """A sharp rectangular button: outlined (fills with colour on hover) or solid."""
    col = color or acc()
    if filled:
        b = tk.Label(parent, text=text, bg=col, fg=BLACK, font=font, padx=padx, pady=pady, cursor="hand2", bd=0,
                     highlightthickness=1, highlightbackground=col)
        hover_bg, hover_fg = blend(col, "#ffffff", 0.35), BLACK
        rest_bg, rest_fg = col, BLACK
    else:
        b = tk.Label(parent, text=text, bg=PANEL2, fg=col, font=font, padx=padx, pady=pady, cursor="hand2", bd=0,
                     highlightthickness=1, highlightbackground=blend(col, BG, 0.45))
        hover_bg, hover_fg = col, BLACK
        rest_bg, rest_fg = PANEL2, col
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>", lambda e: b.config(bg=hover_bg, fg=hover_fg, highlightbackground=col))
    b.bind("<Leave>", lambda e: b.config(bg=rest_bg, fg=rest_fg,
                                         highlightbackground=col if filled else blend(col, BG, 0.45)))
    return b


def rule(parent, height=10, color=None, bg=BG, notch=True):
    """A thin neon divider with a notch and tick marks (a Canvas that stretches to the window's width)."""
    col = color or acc()
    c = tk.Canvas(parent, height=height, bg=bg, highlightthickness=0, bd=0)

    def draw(_e=None):
        c.delete("all")
        w = max(40, c.winfo_width())
        y = height - 3
        dim = blend(col, bg, 0.55)
        if notch:
            c.create_line(0, y, 26, y, fill=col, width=2)
            c.create_polygon(26, y + 1, 34, y - 5, 90, y - 5, 98, y + 1, fill=col, outline=col)
            c.create_line(98, y, w - 30, y, fill=dim, width=1)
            c.create_line(w - 30, y, w - 22, y - 4, w, y - 4, fill=col, width=2)
            for x in range(110, w - 40, 14):
                c.create_line(x, y - 3, x, y, fill=dim)
        else:
            c.create_line(0, y, w, y, fill=col, width=2)
    c.bind("<Configure>", draw)
    return c


# ------------------------------------------------------------------ toggles
class _Toggle(tk.Frame):
    """Shared behaviour of NeonCheck and NeonRadio: a glyph + a label, clickable, with a disabled state."""
    GLYPH_ON, GLYPH_OFF = "[x]", "[ ]"

    def __init__(self, parent, text="", variable=None, command=None, font=None, wraplength=0, state="normal",
                 swatch=None, **_ignored):
        bg = parent.cget("bg")
        super().__init__(parent, bg=bg)
        self.var, self.command, self._state, self._bg, self.swatch = variable, command, state, bg, swatch
        f = font if isinstance(font, tuple) else ("Courier", 9)
        self.glyph = tk.Label(self, text=self.GLYPH_OFF, bg=bg, fg=DIM, font=(f[0], f[1], "bold"), cursor="hand2")
        self.glyph.pack(side="left", anchor="n", padx=(0, 6))
        self.label = tk.Label(self, text=text, bg=bg, fg=TEXT, font=f, justify="left", anchor="w", cursor="hand2",
                              wraplength=max(0, int(wraplength) - 30) if wraplength else 0)
        self.label.pack(side="left")
        for w in (self, self.glyph, self.label):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", lambda e: self._paint(hover=True))
            w.bind("<Leave>", lambda e: self._paint())
        if variable is not None:
            variable.trace_add("write", lambda *a: self._safe_paint())
        self._paint()

    def _safe_paint(self):
        try:
            self._paint()
        except tk.TclError:
            pass

    def on(self):
        raise NotImplementedError

    def _paint(self, hover=False):
        dead = self._state == "disabled"
        on = self.on()
        self.glyph.config(text=self.GLYPH_ON if on else self.GLYPH_OFF,
                          fg=DIM if dead else (acc() if on else blend(acc(), self._bg, 0.5)))
        base = self.swatch or TEXT
        self.label.config(fg=DIM if dead else (acc() if (hover and not self.swatch) else base))

    def _click(self, _e=None):
        if self._state == "disabled":
            return
        self.toggle()
        if self.command:
            self.command()

    def config(self, **kw):
        if "state" in kw:
            self._state = kw.pop("state")
            self.glyph.config(cursor="arrow" if self._state == "disabled" else "hand2")
            self._safe_paint()
        if kw:
            super().config(**kw)
    configure = config


class NeonCheck(_Toggle):
    def on(self):
        return bool(self.var.get())

    def toggle(self):
        self.var.set(not self.var.get())


class NeonRadio(_Toggle):
    GLYPH_ON, GLYPH_OFF = "(*)", "( )"

    def __init__(self, parent, text="", variable=None, value=None, command=None, **kw):
        self.value = value
        super().__init__(parent, text=text, variable=variable, command=command, **kw)

    def on(self):
        return str(self.var.get()) == str(self.value)

    def toggle(self):
        self.var.set(self.value)


class NeonSlider(tk.Canvas):
    """A flat slider you can actually see on a dark panel: a bright line up to a bright knob.
    Click or drag anywhere on it; the arrow keys nudge it by one."""

    def __init__(self, parent, from_, to, variable, command=None, length=330, bg=PANEL, color=None):
        super().__init__(parent, width=length, height=24, bg=bg, highlightthickness=0, bd=0, cursor="hand2",
                         takefocus=1)
        self.lo, self.hi, self.var, self.command = int(from_), int(to), variable, command
        self.length, self.pad, self.color = int(length), 9, color or acc()
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Left>", lambda e: self.set(self.value() - 1))
        self.bind("<Right>", lambda e: self.set(self.value() + 1))
        self.draw()

    def value(self):
        try:
            return min(self.hi, max(self.lo, int(self.var.get())))
        except (tk.TclError, ValueError):
            return self.lo

    def value_at(self, x):
        f = (x - self.pad) / float(self.length - 2 * self.pad)
        return int(round(self.lo + min(1.0, max(0.0, f)) * (self.hi - self.lo)))

    def x_of(self, v):
        f = (v - self.lo) / float(max(1, self.hi - self.lo))
        return self.pad + f * (self.length - 2 * self.pad)

    def set(self, v):
        v = min(self.hi, max(self.lo, int(v)))
        changed = v != self.value()
        self.var.set(v)
        self.draw()
        if changed and self.command:
            self.command(v)

    def _drag(self, e):
        self.focus_set()
        self.set(self.value_at(e.x))

    def draw(self):
        self.delete("all")
        y, x = 12, self.x_of(self.value())
        self.create_line(self.pad, y, self.length - self.pad, y, fill=LINE, width=3)
        self.create_line(self.pad, y, x, y, fill=self.color, width=3)
        self.create_rectangle(x - 5, y - 9, x + 5, y + 9, fill=self.color, outline=BLACK)
