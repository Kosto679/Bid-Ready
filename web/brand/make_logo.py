"""Generate Bid-Ready brand SVGs: a regular Greek-key seal with a tick, plus wordmark lockups and a favicon.

    python web/brand/make_logo.py web/brand
"""
import math
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

C = 50.0          # centre in a 100x100 box
R_OUT = 47.0      # outer edge of the key band
# One hook per unit, attached to the inner ring: (u along the circle 0..1, v outward 0..1)
HOOK_FULL = [(0.0, 0.0), (0.0, 0.78), (0.72, 0.78), (0.72, 0.30), (0.36, 0.30), (0.36, 0.54)]  # two turns
HOOK_SMALL = [(0.0, 0.0), (0.0, 0.80), (0.62, 0.80), (0.62, 0.36), (0.30, 0.36)]               # one turn


def key_path(units, r_in, hook):
    def pt(u, v, k):
        a = 2 * math.pi * (k + u) / units - math.pi / 2
        r = r_in + (R_OUT - r_in) * v
        return C + r * math.cos(a), C + r * math.sin(a)

    parts = []
    for k in range(units):
        pts = [pt(*hook[0], k)]
        for p, q in zip(hook, hook[1:]):
            if p[1] == q[1]:  # along the circle: sample the arc
                pts += [pt(p[0] + (q[0] - p[0]) * i / 6, p[1], k) for i in range(1, 7)]
            else:
                pts.append(pt(*q, k))
        parts.append("M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts))
    return " ".join(parts)


TICK = "M33.5 50.5 L45 62 L67.5 37.5"


def mark(brand, gold, units=16, r_in=35.0, sw=2.4, hook=HOOK_FULL):
    """The seal. Inner gold ring and tick scale with the band so they never collide."""
    s = (r_in - 5) / 30  # 1.0 for the full seal
    inner = (f'<g transform="translate(50 50) scale({s:.3f}) translate(-50 -50)">'
             f'<path d="{TICK}" fill="none" stroke="{brand}" stroke-width="9" stroke-linejoin="miter" stroke-linecap="butt"/>'
             f'<circle cx="50" cy="50" r="30" fill="none" stroke="{gold}" stroke-width="{2.6 / s:.2f}"/></g>')
    return (f'<g fill="none" stroke="{brand}" stroke-width="{sw}">'
            f'<circle cx="50" cy="50" r="{R_OUT + sw * 0.7:.2f}"/>'
            f'<circle cx="50" cy="50" r="{r_in}"/>'
            f'<path d="{key_path(units, r_in, hook)}" stroke-linejoin="miter" stroke-linecap="square"/></g>' + inner)


def favicon(brand, gold):
    return (f'<circle cx="50" cy="50" r="46" fill="{brand}"/>'
            f'<circle cx="50" cy="50" r="38" fill="none" stroke="{gold}" stroke-width="5"/>'
            f'<path d="{TICK}" fill="none" stroke="#fff" stroke-width="10" stroke-linejoin="miter" stroke-linecap="butt"/>')


FONT = "'Arial Black','Helvetica Neue',Arial,sans-serif"


def lockup(brand, gold):
    w, h = 470, 100
    word = (f'<text x="118" y="70" font-family="{FONT}" font-weight="900" font-size="58" textLength="342" '
            f'lengthAdjust="spacingAndGlyphs" fill="{brand}">BID<tspan fill="{gold}">-</tspan>READY</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="Bid-Ready">'
            f'<svg x="0" y="0" width="100" height="100" viewBox="-2 -2 104 104">{mark(brand, gold)}</svg>{word}</svg>\n')


def solo(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 -2 104 104" role="img" aria-label="Bid-Ready">{body}</svg>\n'


NAVY, GOLD = "#0b3d91", "#e8a317"
LIGHT_BLUE, GOLD_DARK = "#9dbcff", "#f0b429"

(OUT / "logo-light.svg").write_text(lockup(NAVY, GOLD), encoding="utf-8")            # on white / light
(OUT / "logo-dark.svg").write_text(lockup(LIGHT_BLUE, GOLD_DARK), encoding="utf-8")  # on dark
(OUT / "mark.svg").write_text(solo(mark(NAVY, GOLD)), encoding="utf-8")
(OUT / "favicon.svg").write_text(solo(favicon(NAVY, GOLD)), encoding="utf-8")
# App header (~64 px): wider band, 10 one-turn hooks, coloured by the page's CSS variables.
# Pasted after the SEAL marker in web/index.html.
(OUT / "seal-header.svg.txt").write_text(mark("var(--brand)", "var(--gold)", units=10, r_in=29.0, sw=3.4, hook=HOOK_SMALL),
                                         encoding="utf-8")
print("ok")
