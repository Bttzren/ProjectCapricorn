"""The launch animation's timeline and text (pure logic, no Tk).

Beam and ring power on -> a scanner reveals her top to bottom while a terminal types boot lines -> flash.
progress(t, D) says how far each effect is at time t of a D-second animation.
"""
NORMAL = ["> CAPRI.SYS v2.0", "> neural link........ OK", "> slang module........ OK", "> choom detected...... OK",
          "> ONLINE"]
FIRST = ["> hello, world.", "> building Capri...... OK", "> loading attitude..... OK",
         "> installing sass...... OK", "> new choom detected", "> ONLINE. nice to meet you"]
DURATION = {False: 3.4, True: 5.0}
BEAM_END, REVEAL_START, REVEAL_END, FLASH_START = 0.24, 0.26, 0.66, 0.76


def duration(first):
    return DURATION[bool(first)]


def lines(first):
    return list(FIRST if first else NORMAL)


def _clamp(x):
    return max(0.0, min(1.0, x))


def progress(t, D):
    """{'beam','ring','reveal','flash','done'}: every value 0..1 except 'done' (bool)."""
    f = _clamp(t / D)
    beam = _clamp(f / BEAM_END) if f < BEAM_END else _clamp(1 - (f - BEAM_END) / 0.14)
    ring = _clamp(f / (BEAM_END + 0.1))
    r = _clamp((f - REVEAL_START) / (REVEAL_END - REVEAL_START))
    reveal = 1 - (1 - r) ** 2                                       # fast start, soft landing
    flash = 0.0 if f < FLASH_START else _clamp(1 - abs((f - (FLASH_START + 0.06)) / 0.12))
    return {"beam": beam, "ring": ring, "reveal": reveal, "flash": flash, "done": t >= D}


def typed(text_lines, t, D):
    """The terminal's visible lines at time t: finished lines plus the one being typed (with a cursor)."""
    start, end = 0.12 * D, 0.72 * D
    total = sum(len(x) + 3 for x in text_lines)                      # +3 = a short pause after each line
    frac = _clamp((t - start) / (end - start))
    chars = int(frac * total)
    out = []
    for x in text_lines:
        if chars <= 0:
            break
        out.append(x[:chars])
        chars -= len(x) + 3
    if out and frac < 1.0:
        out[-1] += "_"
    return out
