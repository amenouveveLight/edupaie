"""Génère resources/icons/app.ico (16 à 256 px) — Pillow requis.

Usage :  python scripts/generate_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

NAVY = (30, 58, 95, 255)
GREEN = (46, 204, 113, 255)
WHITE = (255, 255, 255, 255)

SIZES = [16, 32, 48, 64, 256]
OUT = Path(__file__).resolve().parents[1] / "resources" / "icons" / "app.ico"


def make_icon(size: int = 256) -> Image.Image:
    """Carte navy arrondie, traits blancs (document), point vert (solde à jour)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size * 0.04
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size * 0.22,
        fill=NAVY,
    )

    line_height = max(2.0, size * 0.075)
    x0 = size * 0.24
    for fy, fx_end in ((0.36, 0.78), (0.52, 0.66), (0.68, 0.78)):
        y = size * fy
        draw.rounded_rectangle(
            [x0, y - line_height / 2, size * fx_end, y + line_height / 2],
            radius=line_height / 2,
            fill=WHITE,
        )

    r = size * 0.10
    cx, cy = size * 0.74, size * 0.76
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN)
    return img


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    make_icon(256).save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Icône générée : {OUT} ({OUT.stat().st_size} octets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
