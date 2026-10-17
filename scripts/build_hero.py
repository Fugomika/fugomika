"""Build the profile hero SVGs (dark/light, desktop/mobile) from avatar.png.

Usage: python3 scripts/build_hero.py path/to/avatar.png [--photo]
Writes assets/hero/hero-{dark,light}{,-mobile}.svg (hero-photo-* with --photo)
"""
import colorsys
import math
import sys
from html import escape
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

RAMP = " .,:;i1tfLCG08@"
FONT = "'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', 'Courier New', monospace"

THEMES = {
    "dark": dict(
        bg0="#0D1117", bg1="#161B22", panel="#0D1117", line="#30363D", text="#E6EDF3",
        muted="#8B949E", key="#58A6FF", accent="#1793D1", ascii0="#E6EDF3", ascii1="#58A6FF",
        eye="#FF5F56", radar="#3FB950", grid="#C9D1D9",
    ),
    "light": dict(
        bg0="#FFFFFF", bg1="#F6F8FA", panel="#FFFFFF", line="#D0D7DE", text="#1F2328",
        muted="#57606A", key="#0969DA", accent="#1793D1", ascii0="#1F2328", ascii1="#0969DA",
        eye="#CF222E", radar="#1A7F37", grid="#57606A",
    ),
}

INFO = [
    ("head", "farras@arch"),
    ("kv", "Name", "Farras Fadhila"),
    ("kv", "Role", "Software Engineer @ GEOSAT"),
    ("kv", "Based", "Bogor, Indonesia"),
    ("kv", "OS", "Arch Linux (btw)"),
    ("kv", "Shell", "zsh + tmux + neovim"),
    ("gap",),
    ("sec", "NOW.BUILDING"),
    ("kv", "Geotraking", "Satellite AIS vessel tracking"),
    ("kv", "Bloom", "Cozy life-dashboard PWA"),
    ("kv", "fugotools", "Local media & PDF toolbox"),
    ("gap",),
    ("sec", "STACK"),
    ("kv", "Back", "PHP / Laravel / Filament / Python"),
    ("kv", "Front", "Vue / TypeScript / Supabase"),
    ("kv", "Fuel", "Cireng, kopi, lo-fi"),
    ("gap",),
    ("palette",),
]


def subject_mask(img):
    """Mask out the teal night-city background (and the sign/lamp on the right)."""
    w, h = img.size
    px = img.load()
    mask = Image.new("L", img.size)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            hue, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            background = (0.33 < hue < 0.72 and s > 0.15) or v < 0.06
            background |= x > w * 0.79 and y < h * 0.54
            mp[x, y] = 0 if background else 255
    return mask.filter(ImageFilter.MedianFilter(9))


def photo_art(path, cols, rows, char_aspect, invert=False):
    """Return rows of [(char, False)] from a portrait shot on a black background."""
    src = ImageOps.exif_transpose(Image.open(path)).convert("L")
    w, h = src.size
    src = src.crop((0, 0, w, min(h, int(w * 1.55))))
    # how many columns the photo needs to keep its aspect in this character grid
    used = min(cols, round(rows * src.width / src.height / char_aspect))
    img = src.resize((used, rows), Image.LANCZOS).filter(ImageFilter.SHARPEN)
    gray = ImageEnhance.Contrast(ImageOps.autocontrast(img, cutoff=1)).enhance(1.2).load()
    pad = (cols - used) // 2
    out = []
    for y in range(rows):
        row = [(" ", False)] * pad
        for x in range(used):
            lum = gray[x, y] / 255
            if lum < 0.07:  # the black backdrop drops out entirely
                row.append((" ", False))
                continue
            if invert:
                lum = 1 - lum
            row.append((RAMP[min(len(RAMP) - 1, int(lum ** 0.9 * len(RAMP)))], False))
        row += [(" ", False)] * (cols - pad - used)
        out.append(row)
    return out


def ascii_art(avatar, cols, rows):
    """Return rows of [(char, is_eye)] from the avatar, background removed."""
    src = Image.open(avatar).convert("RGB")
    mask = ImageOps.fit(subject_mask(src), (cols, rows), Image.LANCZOS).load()
    img = ImageOps.fit(src, (cols, rows), Image.LANCZOS)
    rgb = img.load()
    gray = ImageEnhance.Contrast(ImageOps.grayscale(img).filter(ImageFilter.SHARPEN)).enhance(1.5).load()
    out = []
    for y in range(rows):
        row = []
        for x in range(cols):
            if mask[x, y] < 128:
                row.append((" ", False))
                continue
            ink = 1 - gray[x, y] / 255
            r, g, b = rgb[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            is_eye = (h < 0.04 or h > 0.95) and s > 0.5 and v > 0.45
            # cartoon line art: dark outlines and hair become the dense glyphs
            idx = max(1, int(ink ** 1.2 * len(RAMP)))
            row.append((RAMP[min(len(RAMP) - 1, idx)], is_eye))
        out.append(row)
    return out


def ascii_text(art, x, y, size, lh):
    width = len(art[0]) * size * 0.6
    lines = []
    for i, row in enumerate(art):
        spans, cur, buf = [], None, ""
        for ch, eye in row:
            if eye != cur and buf:
                spans.append((cur, buf))
                buf = ""
            cur = eye
            buf += ch
        spans.append((cur, buf))
        body = "".join(
            f'<tspan class="eye">{escape(t)}</tspan>' if e else escape(t) for e, t in spans
        )
        lines.append(f'<text x="{x}" y="{y + i * lh:.1f}" class="ascii" textLength="{width:.1f}" '
                     f'lengthAdjust="spacingAndGlyphs">{body}</text>')
    return "\n".join(lines)


def info_text(x, y, lh, width_chars, t):
    out = []
    for item in INFO:
        kind = item[0]
        if kind == "gap":
            y += lh * 0.6
            continue
        if kind == "head":
            out.append(f'<text x="{x}" y="{y}" class="head"><tspan fill="{t["key"]}">farras</tspan>'
                       f'<tspan fill="{t["muted"]}">@</tspan><tspan fill="{t["accent"]}">arch</tspan>'
                       f'<tspan fill="{t["line"]}"> {"-" * (width_chars - 12)}</tspan></text>')
        elif kind == "sec":
            dashes = "-" * (width_chars - len(item[1]) - 4)
            out.append(f'<text x="{x}" y="{y}" class="sec">- {item[1]} <tspan fill="{t["line"]}">{dashes}</tspan></text>')
        elif kind == "kv":
            k, v = item[1], item[2]
            dots = "." * max(2, 13 - len(k))
            out.append(f'<text x="{x}" y="{y}" class="row"><tspan fill="{t["muted"]}">.</tspan>'
                       f'<tspan class="k">{escape(k)}</tspan><tspan fill="{t["muted"]}">: {dots}</tspan>'
                       f'{escape(v)}</text>')
        elif kind == "palette":
            colors = ["#FF5F56", "#FFBD2E", "#27C93F", "#58A6FF", "#BC8CFF", "#39C5CF", "#E6EDF3", "#8B949E"]
            out.append("".join(
                f'<rect x="{x + i * 26}" y="{y - 13}" width="22" height="16" rx="2" fill="{c}"/>'
                for i, c in enumerate(colors)))
        y += lh
    return "\n".join(out), y


def radar(cx, cy, r, t):
    blips = [(0.55, 40, 0.0), (0.8, 155, 1.1), (0.35, 250, 2.3), (0.7, 310, 3.1)]
    dots = "\n".join(
        f'<circle cx="{cx + d * r * math.cos(math.radians(a)):.1f}" cy="{cy + d * r * math.sin(math.radians(a)):.1f}" '
        f'r="2.6" class="blip" style="animation-delay:{delay}s"/>'
        for d, a, delay in blips
    )
    return f'''
<g>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{t["radar"]}" fill-opacity="0.05" stroke="{t["radar"]}" stroke-opacity="0.55"/>
  <circle cx="{cx}" cy="{cy}" r="{r * 0.66:.1f}" fill="none" stroke="{t["radar"]}" stroke-opacity="0.25"/>
  <circle cx="{cx}" cy="{cy}" r="{r * 0.33:.1f}" fill="none" stroke="{t["radar"]}" stroke-opacity="0.25"/>
  <path d="M{cx - r} {cy} H{cx + r} M{cx} {cy - r} V{cy + r}" stroke="{t["radar"]}" stroke-opacity="0.2"/>
  <g class="sweep" style="transform-origin:{cx}px {cy}px">
    <path d="M{cx} {cy} L{cx + r} {cy} A{r} {r} 0 0 0 {cx + r * math.cos(math.radians(-40)):.1f} {cy + r * math.sin(math.radians(-40)):.1f} Z" fill="url(#sweep)"/>
    <line x1="{cx}" y1="{cy}" x2="{cx + r}" y2="{cy}" stroke="{t["radar"]}" stroke-width="1.5"/>
  </g>
  {dots}
</g>'''


def build(avatar, theme, mobile, photo=False):
    t = THEMES[theme]
    if mobile:
        W, H = 620, 1060
        port = (20, 70, 580, 470)
        art_cols, art_rows, asz, alh = 140, 82, 6.4, 5.4
        info_x, info_y, info_w = 40, 600, 50
        rad = (530, 600, 34)
        footer_y = H - 22
        info_panel = (20, 560, 580, 460)
        info_lh = 21
    else:
        W, H = 1180, 640
        port = (24, 70, 470, 520)
        art_cols, art_rows, asz, alh = 130, 86, 6.0, 5.6
        info_x, info_y, info_w = 534, 110, 52
        rad = (1092, 132, 40)
        footer_y = H - 18
        info_panel = (510, 70, 646, 520)
        info_lh = 24

    px, py, pw, ph = port
    if photo:
        art = photo_art(avatar, art_cols, art_rows, asz * 0.6 / alh, invert=theme == "light")
    else:
        art = ascii_art(avatar, art_cols, art_rows)
    char_w = asz * 0.6
    ax = px + (pw - art_cols * char_w) / 2
    ay = py + (ph - art_rows * alh) / 2 + alh
    info, end_y = info_text(info_x, info_y, info_lh, info_w, t)
    ix, iy, iw, ih = info_panel

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">Farras Fadhila - Software Engineer</title>
<desc id="desc">A terminal-style profile card with an ASCII portrait of Farras, a fastfetch-style summary, and a radar sweep tracking ships.</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg0"]}"/><stop offset="1" stop-color="{t["bg1"]}"/></linearGradient>
  <linearGradient id="ascii" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["ascii0"]}"/><stop offset="1" stop-color="{t["ascii1"]}"/></linearGradient>
  <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["radar"]}" stop-opacity="0"/><stop offset="1" stop-color="{t["radar"]}" stop-opacity="0.45"/></linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["key"]}" stop-opacity="0"/><stop offset="0.5" stop-color="{t["key"]}" stop-opacity="0.35"/><stop offset="1" stop-color="{t["key"]}" stop-opacity="0"/></linearGradient>
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{t["grid"]}" stroke-width="0.6" opacity="0.08"/></pattern>
  <clipPath id="port"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="12"/></clipPath>
  <style>
    text {{ font-family: {FONT}; white-space: pre; }}
    .ascii {{ font-size: {asz}px; letter-spacing: 0; fill: url(#ascii); }}
    .eye {{ fill: {t["eye"]}; animation: pulse 2.4s ease-in-out infinite; }}
    .chrome {{ font-size: 12px; fill: {t["muted"]}; }}
    .label {{ font-size: 11px; letter-spacing: 2px; fill: {t["muted"]}; }}
    .head {{ font-size: 16px; font-weight: 700; }}
    .sec {{ font-size: 14px; font-weight: 700; fill: {t["text"]}; }}
    .row {{ font-size: 14px; fill: {t["text"]}; }}
    .k {{ fill: {t["key"]}; font-weight: 700; }}
    .tag {{ font-size: 14px; fill: {t["text"]}; }}
    .cursor {{ fill: {t["key"]}; animation: blink 1.1s steps(1) infinite; }}
    .live {{ fill: {t["radar"]}; animation: pulse 1.6s ease-in-out infinite; }}
    .sweep {{ animation: spin 4s linear infinite; }}
    .blip {{ fill: {t["radar"]}; opacity: 0; animation: blip 4s linear infinite; }}
    .scan {{ animation: scan 6s ease-in-out infinite; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
    @keyframes pulse {{ 50% {{ opacity: 0.35; }} }}
    @keyframes blip {{ 0%, 8% {{ opacity: 0; }} 10% {{ opacity: 1; }} 60% {{ opacity: 0.15; }} 100% {{ opacity: 0; }} }}
    @keyframes scan {{ from {{ transform: translateY(0); }} to {{ transform: translateY({ph - 60}px); }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} .blip {{ opacity: 1; }} }}
  </style>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="url(#bg)" stroke="{t["line"]}"/>
<circle cx="24" cy="22" r="6" fill="#FF5F56"/><circle cx="44" cy="22" r="6" fill="#FFBD2E"/><circle cx="64" cy="22" r="6" fill="#27C93F"/>
<text x="{W / 2}" y="26" text-anchor="middle" class="chrome">farras@arch ~ $ fastfetch</text>
<circle cx="{W - 96}" cy="22" r="4" class="live"/><text x="{W - 86}" y="26" class="label">ONLINE</text>
<line x1="1" y1="44" x2="{W - 1}" y2="44" stroke="{t["line"]}"/>

<text x="{px + 6}" y="{py - 8}" class="label">PORTRAIT / FARRAS</text>
<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="12" fill="{t["panel"]}" stroke="{t["line"]}"/>
<g clip-path="url(#port)">
  <rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="url(#grid)"/>
  {ascii_text(art, round(ax, 1), round(ay, 1), asz, alh)}
  <rect x="{px}" y="{py}" width="{pw}" height="60" fill="url(#scan)" class="scan"/>
</g>

<text x="{ix + 6}" y="{iy - 8}" class="label">SYSTEM / BUILDER</text>
<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" rx="12" fill="{t["panel"]}" stroke="{t["line"]}"/>
{radar(*rad, t)}
<text x="{rad[0]}" y="{rad[1] + rad[2] + 18}" text-anchor="middle" class="label">AIS</text>
{info}
<text x="{info_x}" y="{end_y + 18}" class="tag"><tspan fill="{t["muted"]}">&gt; </tspan>fake software engineer, real satellites<tspan class="cursor">_</tspan></text>

<text x="{W / 2}" y="{footer_y}" text-anchor="middle" class="label">SATELLITE DATA / LARAVEL / VUE / PYTHON / ARCH BTW</text>
</svg>
'''


def main():
    args = [a for a in sys.argv[1:] if a != "--photo"]
    photo = "--photo" in sys.argv
    avatar = args[0] if args else "avatar.png"
    prefix = "hero-photo" if photo else "hero"
    out = Path(__file__).resolve().parent.parent / "assets" / "hero"
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        for mobile in (False, True):
            name = f"{prefix}-{theme}{'-mobile' if mobile else ''}.svg"
            (out / name).write_text(build(avatar, theme, mobile, photo))
            print("wrote", out / name)


if __name__ == "__main__":
    main()
