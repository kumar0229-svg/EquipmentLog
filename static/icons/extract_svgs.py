"""One-off helper: pull the <svg>...</svg> markup out of each .dc.html design
export in this folder and save it as a standalone icon under svg/<slug>.svg.

The .dc.html files are full Claude-design-tool documents (they load React via
support.js) — not usable directly as lightweight dashboard icons. This script
extracts just the vector artwork.
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / 'svg'

FILES = {
    'AFND.dc.html': 'afnd',
    'AOD Pump.dc.html': 'aod-pump',
    'Candle Filter.dc.html': 'candle-filter',
    'Centrifuge.dc.html': 'centrifuge',
    'Co Mill.dc.html': 'co-mill',
    'Jet Mill.dc.html': 'jet-mill',
    'Multi Mill.dc.html': 'multi-mill',
    'Nutsche Filter.dc.html': 'nutsche-filter',
    'Reactor.dc.html': 'reactor',
    'Sifter.dc.html': 'sifter',
    'Vacuum Tray Drier.dc.html': 'vacuum-tray-drier',
    'Vessels.dc.html': 'vessels',
}

SVG_RE = re.compile(r'<svg\b[^>]*>.*?</svg>', re.DOTALL)

for filename, slug in FILES.items():
    html = (HERE / filename).read_text(encoding='utf-8')
    match = SVG_RE.search(html)
    if not match:
        raise SystemExit(f'no <svg> found in {filename}')
    svg = match.group(0)
    svg = svg.replace(
        '<svg ',
        '<svg xmlns="http://www.w3.org/2000/svg" ',
        1,
    )
    out_path = OUT / f'{slug}.svg'
    out_path.write_text(svg + '\n', encoding='utf-8')
    print(f'wrote {out_path.relative_to(HERE.parent.parent)}')
