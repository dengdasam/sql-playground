"""Compose the app icon from the vendored open-licensed glyph.

Icon art: lucide/plug-zap (ISC, via Iconify) — see
SqlController/assets/icons/NOTICE.md. This script only recolours the
glyph to white and places it on a solid rounded square; it does not change
the licence.

Flow:
  vendored SVG -> headless Chromium rasterise -> Pillow compose -> multi-size .ico

Outputs:
  SqlController/assets/app.ico    exe file icon (ApplicationIcon in csproj)
  SqlController/assets/glyph.png  white glyph, embedded and used at runtime
                                  to compose the three tray state icons
  preview-icon.png                256 px preview (not committed)

Dependencies (optional — only needed when you actually regenerate the icon):
  pip install pillow playwright
  python -m playwright install chromium

The committed app.ico / glyph.png are complete and correct; you only need
to run this if you change the glyph or the brand colour.

Run from sql-query-dotnet/:
  python tools/make_icon.py
"""
import asyncio
import io
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICONS = ROOT / "SqlController" / "assets" / "icons"
ASSETS = ROOT / "SqlController" / "assets"

PRIMARY = (0x3B, 0x5A, 0x6A)
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
SMALL_BELOW = 40  # 16-32 px use the bolder glyph
RASTER = 1024


def require_dependencies():
    """缺依赖时给出可执行的安装提示，而不是抛 ImportError 堆栈。"""
    missing = []
    try:
        import PIL  # noqa: F401
    except ImportError:
        missing.append("pillow")
    try:
        import playwright  # noqa: F401
    except ImportError:
        missing.append("playwright")

    if missing:
        print("缺少依赖：" + "、".join(missing), file=sys.stderr)
        print("\n本机未改动图标时无需运行本脚本 —— 仓库里的 app.ico 与 glyph.png 已完整可用。", file=sys.stderr)
        print("确实需要重新生成时，先安装：\n", file=sys.stderr)
        print("    pip install pillow playwright", file=sys.stderr)
        print("    python -m playwright install chromium\n", file=sys.stderr)
        raise SystemExit(2)


require_dependencies()

from PIL import Image, ImageDraw  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402


async def shoot(page, svg_path: pathlib.Path) -> Image.Image:
    svg = svg_path.read_text(encoding="utf-8")
    svg = svg.replace('width="1em" height="1em"', f'width="{RASTER}" height="{RASTER}"')
    svg = svg.replace('stroke="currentColor"', 'stroke="#FFFFFF"')
    html = (
        "<!doctype html><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:transparent}"
        f"svg{{display:block;width:{RASTER}px;height:{RASTER}px}}</style>" + svg
    )
    await page.set_content(html)
    shot = await page.screenshot(
        omit_background=True,
        clip={"x": 0, "y": 0, "width": RASTER, "height": RASTER},
    )
    return Image.open(io.BytesIO(shot)).convert("RGBA")


async def rasterise() -> tuple[Image.Image, Image.Image]:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": RASTER, "height": RASTER}, device_scale_factor=1
        )
        normal = await shoot(page, ICONS / "plug-zap.svg")
        bold = await shoot(page, ICONS / "plug-zap-small.svg")
        await browser.close()
    return normal, bold


def rounded_square(size: int, color: tuple[int, int, int]) -> Image.Image:
    """Solid rounded square (no gradient), supersampled then downscaled."""
    w = size * 4
    mask = Image.new("L", (w, w), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, w - 1, w - 1], radius=int(w * 0.22), fill=255
    )
    img = Image.new("RGBA", (w, w), color + (255,))
    img.putalpha(mask)
    return img.resize((size, size), Image.LANCZOS)


def compose(size: int, glyph: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    img = rounded_square(size, color)
    side = round(size * 0.66)
    g = glyph.resize((side, side), Image.LANCZOS)
    img.alpha_composite(g, ((size - side) // 2, (size - side) // 2))
    return img


def write_ico(path: pathlib.Path, frames: list[tuple[int, Image.Image]]) -> None:
    blobs = []
    for size, image in frames:
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        blobs.append((size, buf.getvalue()))

    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    directory = b""
    payload = b""
    for size, png in blobs:
        dim = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        payload += png
    path.write_bytes(header + directory + payload)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    normal, bold = asyncio.run(rasterise())

    bold.resize((256, 256), Image.LANCZOS).save(ASSETS / "glyph.png")
    frames = [
        (s, compose(s, bold if s < SMALL_BELOW else normal, PRIMARY)) for s in SIZES
    ]
    write_ico(ASSETS / "app.ico", frames)
    compose(256, normal, PRIMARY).save(ROOT / "preview-icon.png")

    print(f"app.ico   {(ASSETS / 'app.ico').stat().st_size} bytes  sizes={SIZES}")
    print(f"glyph.png {(ASSETS / 'glyph.png').stat().st_size} bytes")
    print("preview-icon.png (not committed)")


if __name__ == "__main__":
    main()
