"""Draws the profile README artwork into assets/ as animated SVGs.

Every word is drawn as outlined paths from the fonts in assets/fonts, because GitHub serves SVGs
with a policy that blocks embedded fonts. The numbers are the public contribution calendar, read
fresh each run (the daily workflow keeps them current).

    pip install fonttools brotli
    python scripts/profile_art.py
"""

from __future__ import annotations

import datetime as dt
import html
import pathlib
import re
import urllib.request
from dataclasses import dataclass

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

USER = "AliShahbazi81"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


# ---------------------------------------------------------------- text as outlines
class Font:
    def __init__(self, name: str) -> None:
        self.font = TTFont(ASSETS / "fonts" / f"{name}.woff2")
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"]

    def _glyph(self, ch: str) -> str:
        name = self.cmap.get(ord(ch))
        if name is None:
            raise SystemExit(f"{ch!r} is not in this font: draw it as a shape instead.")
        return name

    def width(self, text: str, size: float, spacing: float = 0.0) -> float:
        return sum(self.hmtx[self._glyph(c)][0] for c in text) * size / self.upm + spacing * len(text)

    def path(self, text: str, x: float, y: float, size: float, spacing: float = 0.0) -> str:
        scale = size / self.upm
        pen = SVGPathPen(self.glyphs)
        cursor = x
        for ch in text:
            name = self._glyph(ch)
            self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, cursor, y)))
            cursor += self.hmtx[name][0] * scale + spacing
        return pen.getCommands()


F = {k: Font(k) for k in ("sora-700", "jbm-400", "jbm-600", "plexsans-400", "plexsans-600", "plexmono-500")}


def text(s: str, x: float, y: float, size: float, font: str, fill: str, anchor: str = "start",
         spacing: float = 0.0, attrs: str = "") -> str:
    f = F[font]
    w = f.width(s, size, spacing)
    x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
    d = f.path(s, x0, y, size, spacing)
    return f'<path d="{d}" fill="{fill}" {attrs}/>' if d else ""


def rich(parts: list[tuple[str, str, str]], x: float, y: float, size: float, spacing: float = 0.0) -> tuple[str, float]:
    """Pieces of (text, font, fill) side by side; returns the drawing and the total width."""
    out, cursor = "", x
    for s, font, fill in parts:
        out += text(s, cursor, y, size, font, fill, spacing=spacing)
        cursor += F[font].width(s, size, spacing)
    return out, cursor - x


def svg(name: str, w: int, h: int, css: str, body: str, label: str) -> None:
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="{html.escape(label)}"><title>{html.escape(label)}</title><style>{css}</style>{body}</svg>')
    (ASSETS / f"{name}.svg").write_text(doc, encoding="utf-8")


# ---------------------------------------------------------------- the year
@dataclass(frozen=True)
class Year:
    dates: list[str]
    counts: list[int]

    @property
    def total(self) -> int:
        return sum(self.counts)

    @property
    def best(self) -> int:
        return max(self.counts) or 1

    def streaks(self) -> tuple[int, int]:
        longest = run = 0
        for c in self.counts:
            run = run + 1 if c else 0
            longest = max(longest, run)
        tail = self.counts[:-1] if self.counts and self.counts[-1] == 0 else self.counts  # today may not have started
        current = 0
        for c in reversed(tail):
            if not c:
                break
            current += 1
        return current, longest

    def month_starts(self) -> list[tuple[int, str]]:
        return [(i, dt.date.fromisoformat(d).strftime("%b")) for i, d in enumerate(self.dates) if d.endswith("-01")]


def read_year() -> Year:
    req = urllib.request.Request(f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "profile-art"})
    page = urllib.request.urlopen(req, timeout=30).read().decode()
    ids = {i: d for d, i in re.findall(r'data-date="(\d{4}-\d\d-\d\d)" id="(contribution-day-component-\d+-\d+)"', page)}
    days: dict[str, int] = {}
    for i, tip in re.findall(r'<tool-tip [^>]*for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]+)</tool-tip>', page):
        m = re.match(r"(\d+|No) contribution", tip)
        if i in ids and m:
            days[ids[i]] = 0 if m.group(1) == "No" else int(m.group(1))
    if len(days) < 300:
        raise SystemExit(f"The contribution calendar did not parse ({len(days)} days); nothing was drawn.")
    dates = sorted(days)
    return Year(dates, [days[d] for d in dates])


# ---------------------------------------------------------------- shared look
C = {"bg": "#0a0e13", "panel": "#0e131a", "grid": "#16202b", "line": "#1f2a36", "fg": "#e8edf2", "mut": "#7d8a99",
     "up": "#2bd67b", "acc": "#5ab0ff", "vio": "#b48cff", "amb": "#ffb547"}
B = {"bg": "#0a1c2e", "fine": "#12304b", "major": "#1b4266", "ink": "#e7f0f7", "mut": "#8fb0c9", "acc": "#7fd1ff", "hot": "#ffd166"}
MOTION = """
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}} .pulse{animation:pulse 1.6s ease-in-out infinite}
@keyframes pop{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:scale(1)}}
.n{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .35s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes fade{from{opacity:0}to{opacity:1}} .in{opacity:0;animation:fade .55s ease forwards}
@keyframes draw{to{stroke-dashoffset:0}}
@keyframes tape{from{transform:translateX(0)}to{transform:translateX(var(--w))}}
@keyframes dash{to{stroke-dashoffset:-24}} .flow{stroke-dasharray:6 6;animation:dash 1.2s linear infinite}
@media (prefers-reduced-motion: reduce){*{animation:none!important;opacity:1!important;stroke-dashoffset:0!important}}
"""
STACK = ["C#", ".NET", "ASP.NET CORE", "TYPESCRIPT", "REACT", "NEXT.JS", "PYTHON", "DJANGO", "SQL SERVER",
         "POSTGRESQL", "DOCKER", "GITHUB ACTIONS", "AWS", "PLAYWRIGHT", "XUNIT", "PYTEST"]


def grid(x0: int, y0: int, x1: int, y1: int, step: int, color: str, opacity: float = 1.0) -> str:
    s = "".join(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}"/>' for x in range(x0, x1 + 1, step))
    s += "".join(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>' for y in range(y0, y1 + 1, step))
    return f'<g stroke="{color}" stroke-width="1" opacity="{opacity}">{s}</g>'


def delay(s: float) -> str:
    return f'class="in" style="animation-delay:{s:.2f}s"'


# ---------------------------------------------------------------- console: header
def console_hero() -> None:
    w, h = 1200, 400
    main_y, x0, x1 = 196, 690, 1120
    lanes = [("feat/api", C["acc"], 120, 730, 880), ("feat/web", C["vio"], 272, 800, 1000), ("fix/tests", C["amb"], 150, 940, 1070)]
    graph = (f'<line x1="{x0}" y1="{main_y}" x2="{x1}" y2="{main_y}" stroke="{C["up"]}" stroke-width="3" stroke-linecap="round" '
             f'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" style="animation:draw 1.6s ease .2s forwards"/>')
    dots = ""
    for k, (name, col, y, a, b) in enumerate(lanes):
        d = f"M{a} {main_y} C{a + 30} {main_y} {a + 20} {y} {a + 50} {y} H{b - 50} C{b - 20} {y} {b - 30} {main_y} {b} {main_y}"
        t = 0.5 + k * 0.35
        graph += (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.5" stroke-linecap="round" pathLength="1" '
                  f'stroke-dasharray="1" stroke-dashoffset="1" style="animation:draw 1.1s ease {t:.2f}s forwards"/>')
        for j, x in enumerate(range(a + 70, b - 49, 42)):
            dots += f'<circle class="n" style="animation-delay:{t + 0.25 + j * 0.08:.2f}s" cx="{x}" cy="{y}" r="6" fill="{C["bg"]}" stroke="{col}" stroke-width="2.5"/>'
        dots += f'<g {delay(t + 0.3)}>{text(name, a + 70, y - 16 if y < main_y else y + 28, 13, "jbm-400", col)}</g>'
        dots += f'<circle class="n" style="animation-delay:{t + 0.9:.2f}s" cx="{b}" cy="{main_y}" r="8" fill="{col}"/>'
    for j, x in enumerate((x0, 760, 860, x1)):
        dots += f'<circle class="n" style="animation-delay:{0.2 + j * 0.3:.2f}s" cx="{x}" cy="{main_y}" r="7" fill="{C["bg"]}" stroke="{C["up"]}" stroke-width="3"/>'
    dots += f'<g {delay(0.4)}>{text("main", x0, main_y - 18, 13, "jbm-600", C["up"])}</g>'

    parts: list[tuple[str, str, str]] = []
    for item in STACK:
        parts += [("•  ", "jbm-600", C["up"]), (item, "jbm-400", C["fg"]), ("      ", "jbm-400", C["fg"])]
    tape, tape_w = rich(parts, 24, 371, 15, spacing=1)
    tape2, _ = rich(parts, 24 + tape_w, 371, 15, spacing=1)

    body = f"""
<rect width="{w}" height="{h}" rx="18" fill="{C['bg']}"/>
<clipPath id="r"><rect width="{w}" height="{h}" rx="18"/></clipPath>
<g clip-path="url(#r)">
  {grid(640, 0, w, 330, 37, C['grid'])}
  <linearGradient id="fadeL" x1="0" x2="1"><stop offset="0" stop-color="{C['bg']}"/><stop offset="1" stop-color="{C['bg']}" stop-opacity="0"/></linearGradient>
  <rect x="0" y="0" width="660" height="330" fill="{C['bg']}"/>
  <rect x="660" y="0" width="90" height="330" fill="url(#fadeL)"/>
  {graph}{dots}
  <circle class="pulse" cx="62" cy="64" r="5" fill="{C['up']}"/>
  {text("~/alishahbazi81 · online", 78, 69, 15, "jbm-400", C['mut'], spacing=2)}
  {text("Ali Shahbazi", 56, 160, 78, "sora-700", C['fg'], spacing=-2)}
  {text("Full-stack developer.", 58, 212, 21, "jbm-400", C['fg'])}
  {text("From the database to the pixel: APIs, web apps,", 58, 246, 15, "jbm-400", C['mut'])}
  {text("and the pipelines that ship them.", 58, 268, 15, "jbm-400", C['mut'])}
  <rect x="0" y="330" width="{w}" height="70" fill="{C['panel']}"/>
  <line x1="0" y1="330" x2="{w}" y2="330" stroke="{C['line']}"/>
  <g style="--w:-{tape_w:.1f}px;animation:tape 36s linear infinite">{tape}{tape2}</g>
</g>"""
    svg("console-hero", w, h, MOTION, body, "Ali Shahbazi, full-stack developer")


# ---------------------------------------------------------------- console: the year
def console_year(year: Year) -> None:
    w, h = 1200, 470
    x0, x1, y0, y1 = 56, 1144, 150, 352
    vb0, vb1 = 376, 430
    counts, best = year.counts, year.best
    current, longest = year.streaks()
    cum, s = [], 0
    for c in counts:
        s += c
        cum.append(s)
    n = len(counts)

    def X(i: int) -> float:
        return x0 + i / (n - 1) * (x1 - x0)

    def Y(v: int) -> float:
        return y1 - v / max(cum[-1], 1) * (y1 - y0)

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(cum))
    bars = "".join(f'<rect x="{X(i) - 1.1:.1f}" y="{vb1 - c / best * (vb1 - vb0):.1f}" width="2.2" height="{c / best * (vb1 - vb0):.1f}" '
                   f'fill="{C["acc"]}" opacity="{0.35 + 0.65 * c / best:.2f}"/>' for i, c in enumerate(counts) if c)
    months = "".join(f'<line x1="{X(i):.1f}" y1="{y0}" x2="{X(i):.1f}" y2="{vb1}" stroke="{C["grid"]}"/>'
                     + text(m.upper(), X(i), vb1 + 26, 12, "jbm-400", C["mut"], anchor="middle") for i, m in year.month_starts())
    tiles = [("TOTAL", f"{year.total:,}"), ("BEST DAY", str(best)), ("STREAK", f"{current}d"), ("LONGEST", f"{longest}d")]
    tile_svg = "".join(text(lab, x1 - (len(tiles) - 1 - k) * 135, 64, 12, "jbm-400", C["mut"], "end", 1.5)
                       + text(val, x1 - (len(tiles) - 1 - k) * 135, 96, 26, "jbm-600", C["fg"], "end") for k, (lab, val) in enumerate(tiles))
    body = f"""
<rect width="{w}" height="{h}" rx="18" fill="{C['bg']}"/>
{text('git log --since="1 year ago"', x0, 64, 13, "jbm-400", C['mut'], spacing=1)}
{text("The year, commit by commit", x0, 102, 34, "sora-700", C['fg'], spacing=-0.5)}
{tile_svg}{months}
<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C['up']}" stop-opacity=".28"/><stop offset="1" stop-color="{C['up']}" stop-opacity="0"/></linearGradient>
<polygon {delay(1.6)} points="{x0},{y1} {pts} {x1},{y1}" fill="url(#area)"/>
<polyline points="{pts}" fill="none" stroke="{C['up']}" stroke-width="2.5" stroke-linejoin="round" pathLength="1"
  stroke-dasharray="1" stroke-dashoffset="1" style="animation:draw 2.2s cubic-bezier(.4,0,.2,1) .2s forwards"/>
<circle class="pulse" cx="{X(n - 1):.1f}" cy="{Y(cum[-1]):.1f}" r="5" fill="{C['up']}"/>
<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{C['line']}"/>
{text("PER DAY", x0, vb0 - 6, 11, "jbm-400", C['mut'], spacing=1.5)}
<g {delay(0.9)}>{bars}</g>"""
    svg("console-year", w, h, MOTION, body, f"{year.total:,} contributions in the last year")


# ---------------------------------------------------------------- blueprint: the drawing
def node(x: int, y: int, w: int, h: int, title: str, lines: list[str], t: float, hot: bool = False) -> str:
    tick = 8
    corners = "".join(f'<path d="M{cx} {cy + dy * tick} V{cy} H{cx + dx * tick}" stroke="{B["acc"]}" stroke-width="2" fill="none"/>'
                      for cx, cy, dx, dy in [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)])
    rows = "".join(text(s, x + 16, y + 58 + i * 20, 13, "plexmono-500", B["mut"]) for i, s in enumerate(lines))
    return (f'<g {delay(t)}><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{B["bg"]}" stroke="{B["ink"]}" stroke-width="1.5"/>{corners}'
            f'{text(title, x + 16, y + 32, 18, "plexsans-600", B["hot"] if hot else B["ink"])}{rows}</g>')


def blueprint(year: Year) -> None:
    w, h = 1200, 660
    nodes = [
        node(60, 220, 200, 120, "Client", ["browser · phone", "installable PWA"], 0.2),
        node(340, 220, 220, 140, "Web app", ["TypeScript", "React · Next.js", "Tailwind"], 0.4, hot=True),
        node(670, 220, 210, 140, "API", ["C# · .NET", "ASP.NET Core", "Python · Django"], 0.6, hot=True),
        node(990, 140, 170, 120, "Data", ["SQL Server", "PostgreSQL"], 0.8, hot=True),
        node(990, 330, 170, 100, "Cache · queue", ["Redis"], 0.95),
        node(340, 430, 220, 100, "Tests", ["Playwright · Vitest", "xUnit · pytest"], 1.05),
        node(670, 430, 210, 100, "Delivery", ["Docker · GitHub Actions", "AWS"], 1.15),
    ]
    edges = [("M260 280 H340", "HTTPS", 300, 268, "middle"), ("M560 290 H670", "REST", 615, 278, "middle"),
             ("M880 260 C935 260 935 200 990 200", "SQL", 935, 214, "middle"),
             ("M880 320 C935 320 935 380 990 380", "cache", 950, 404, "middle"),
             ("M560 480 H670", "CI", 615, 468, "middle"), ("M775 430 V360", "deploy", 790, 400, "start")]
    lines, labels = "", ""
    for k, (d, lab, lx, ly, anchor) in enumerate(edges):
        lines += (f'<path d="{d}" fill="none" stroke="{B["ink"]}" stroke-width="1.5" stroke-opacity=".55"/>'
                  f'<path class="flow" d="{d}" fill="none" stroke="{B["acc"]}" stroke-width="1.5"/>'
                  f'<circle r="4" fill="{B["hot"]}"><animateMotion dur="{2.2 + k * 0.3:.1f}s" repeatCount="indefinite" path="{d}" begin="{0.3 * k:.1f}s"/></circle>')
        labels += text(lab, lx, ly, 12, "plexmono-500", B["acc"], anchor)
    stamp = [("DRAWN", "A. Shahbazi", 942, 556), ("SHEET", "1 / 1", 1057, 556),
             ("REV", dt.date.today().strftime("%Y.%m"), 942, 600), ("COMMITS / YR", f"{year.total:,}", 1057, 600)]
    block = "".join(text(a, x, y, 10, "plexmono-500", B["mut"], spacing=1) + text(b, x, y + 18, 13, "plexsans-400", B["ink"]) for a, b, x, y in stamp)
    body = f"""
<rect width="{w}" height="{h}" rx="18" fill="{B['bg']}"/>
<clipPath id="r"><rect width="{w}" height="{h}" rx="18"/></clipPath>
<g clip-path="url(#r)">
{grid(0, 0, w, h, 12, B['fine'], .55)}{grid(0, 0, w, h, 60, B['major'], .8)}
{text("Ali Shahbazi", 60, 96, 54, "plexsans-600", B['ink'], spacing=-1)}
{text("FULL-STACK DEVELOPER · GENERAL ARRANGEMENT, ONE REQUEST END TO END", 62, 132, 15, "plexmono-500", B['acc'], spacing=1)}
{lines}{''.join(nodes)}
<g {delay(1.1)}>{labels}</g>
<g {delay(1.2)} stroke="{B['mut']}" stroke-width="1"><line x1="60" y1="586" x2="880" y2="586"/><line x1="60" y1="578" x2="60" y2="594"/><line x1="880" y1="578" x2="880" y2="594"/></g>
<g {delay(1.2)}>{text("one developer · every layer", 470, 606, 12, "plexmono-500", B['mut'], "middle")}</g>
<g {delay(1.3)}><rect x="930" y="540" width="230" height="88" fill="{B['bg']}" stroke="{B['ink']}" stroke-width="1.5"/>
<line x1="930" y1="584" x2="1160" y2="584" stroke="{B['ink']}" stroke-opacity=".5"/><line x1="1045" y1="540" x2="1045" y2="628" stroke="{B['ink']}" stroke-opacity=".5"/>{block}</g>
</g>"""
    svg("blueprint", w, h, MOTION, body, "Full-stack drawing: client, web app, API, data, cache, tests and delivery")


def blueprint_bom() -> None:
    w, h = 1200, 340
    rows = [("C# · .NET · ASP.NET Core", "APIs and services", "EF Core · xUnit"),
            ("TypeScript · React · Next.js", "web apps", "Tailwind · Vitest · Playwright"),
            ("Python · Django", "services and automation", "pydantic · pytest"),
            ("SQL Server · PostgreSQL", "data", "Redis"),
            ("Docker · GitHub Actions · AWS", "delivery", "Linux · Windows")]
    head = "".join(text(t, x, 92, 11, "plexmono-500", B["mut"], spacing=1.5) for x, t in [(60, "ITEM"), (110, "PART"), (520, "USED FOR"), (790, "WITH")])
    out = ""
    for k, (part, role, wth) in enumerate(rows):
        y = 134 + k * 40
        out += (f'<g {delay(0.15 * k)}><line x1="60" y1="{y - 26}" x2="1140" y2="{y - 26}" stroke="{B["ink"]}" stroke-opacity=".25"/>'
                + text(f"{k + 1:02d}", 60, y, 14, "plexmono-500", B["acc"]) + text(part, 110, y, 16, "plexsans-400", B["ink"])
                + text(role, 520, y, 16, "plexsans-400", B["hot"]) + text(wth, 790, y, 14, "plexmono-500", B["mut"]) + "</g>")
    end = 134 + len(rows) * 40 - 26
    body = f"""
<rect width="{w}" height="{h}" rx="18" fill="{B['bg']}"/>
{grid(0, 0, w, h, 60, B['major'], .5)}
{text("Bill of materials", 60, 58, 22, "plexsans-600", B['ink'])}
{head}{out}
<line x1="60" y1="{end}" x2="1140" y2="{end}" stroke="{B['ink']}" stroke-opacity=".25"/>"""
    svg("blueprint-bom", w, h, MOTION, body, "Stack: C#, .NET, TypeScript, React, Next.js, Python, Django, SQL Server, PostgreSQL, Docker, AWS")


# ---------------------------------------------------------------- link buttons
def link(name: str, label: str, handle: str) -> None:
    w, h = 300, 64
    body = (f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="12" fill="{C["bg"]}" stroke="{C["line"]}" stroke-width="2"/>'
            f'<circle class="pulse" cx="28" cy="32" r="5" fill="{C["up"]}"/>'
            + text(label, 46, 30, 16, "jbm-600", C["fg"]) + text(handle, 46, 48, 12, "jbm-400", C["mut"])
            + f'<path d="M{w - 34} 40 L{w - 20} 26 M{w - 31} 25 H{w - 20} V36" fill="none" stroke="{C["acc"]}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    svg(f"link-{name}", w, h, MOTION, body, f"{label}: {handle}")


def main() -> None:
    year = read_year()
    console_hero()
    console_year(year)
    blueprint(year)
    blueprint_bom()
    link("telegram", "Telegram", "t.me/AliShahbazi81")
    link("linkedin", "LinkedIn", "in/alishahbazi81")
    link("codepen", "CodePen", "codepen.io/alishahbazi81")
    print(f"drew {len(list(ASSETS.glob('*.svg')))} images · {year.total:,} contributions · best day {year.best}")


if __name__ == "__main__":
    main()
