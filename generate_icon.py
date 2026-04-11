"""
generate_icon.py — EpisodeSplit icon generator
Faithfully recreates Option B from the design preview:
  - Dark rounded background
  - Two film strips angled apart (left=blue frames, right=orange frames)
  - Orange curved scissors crossing in the center
Requires: pip install Pillow
"""

import os, sys, io, math, struct, base64

try:
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "--quiet"], check=True)
    from PIL import Image, ImageDraw

os.makedirs("assets", exist_ok=True)

# ── Colours ──────────────────────────────────────────────────────────────────
BG         = (13,  17,  23, 255)    # #0d1117  dark background
STRIP      = (33,  38,  45, 255)    # #21262d  strip body
STRIP_BDR  = (48,  54,  61, 255)    # #30363d  strip border
PERF_COL   = (13,  17,  23, 255)    # same as BG (punched-out holes)
WIN_L      = (56, 189, 248,  77)    # #38bdf8 @ 30%  blue frames
WIN_R      = (249,115,  22,  77)    # #f97316 @ 30%  orange frames
SCISSORS   = (249,115,  22, 255)    # #f97316  solid orange


def bezier(p0, p1, p2, steps=30):
    """Quadratic Bezier as a list of (x,y) tuples."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u*u*p0[0] + 2*u*t*p1[0] + t*t*p2[0]
        y = u*u*p0[1] + 2*u*t*p1[1] + t*t*p2[1]
        pts.append((x, y))
    return pts


def draw_strip_layer(size: int, frame_color: tuple) -> Image.Image:
    """
    Draw ONE film strip centered on a transparent size×size canvas.
    Dimensions match the SVG: strip 60×190 in a 300-unit space, scaled to `size`.
    """
    s   = size
    sc  = s / 300.0          # scale factor  (300 = SVG coordinate space)
    cx  = s // 2
    cy  = s // 2

    # Strip rectangle (SVG: x=-30 y=-95 w=60 h=190 rx=6)
    sw  = int(60  * sc)
    sh  = int(190 * sc)
    rx  = max(2, int(6 * sc))
    x0  = cx - sw // 2
    y0  = cy - sh // 2
    x1  = x0 + sw
    y1  = y0 + sh

    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Body
    d.rounded_rectangle([x0, y0, x1, y1], radius=rx,
                        fill=STRIP, outline=STRIP_BDR, width=max(1, int(sc)))

    # Perforations — SVG uses x=-22/x=10 for left/right columns, y spacing ~30 apart
    # 6 rows, heights 16, spaced through the strip
    pw = max(3, int(12 * sc))
    ph = max(4, int(16 * sc))
    pr = max(1, int(3  * sc))
    pl_x = int(cx + (-22) * sc)   # left perf column
    pr_x = int(cx + 10   * sc)   # right perf column
    perf_ys_svg = [-82, -52, -22, 8, 38, 68]
    for py_svg in perf_ys_svg:
        py = int(cy + py_svg * sc)
        d.rounded_rectangle([pl_x, py, pl_x + pw, py + ph], radius=pr, fill=PERF_COL)
        d.rounded_rectangle([pr_x, py, pr_x + pw, py + ph], radius=pr, fill=PERF_COL)

    # Frame windows — SVG: x=-14 w=28 h=20, 5 windows
    fw = max(4, int(28 * sc))
    fh = max(3, int(20 * sc))
    fr = max(1, int(2  * sc))
    fx = int(cx + (-14) * sc)
    win_ys_svg = [-68, -38, -8, 22, 52]
    for wy_svg in win_ys_svg:
        wy = int(cy + wy_svg * sc)
        d.rounded_rectangle([fx, wy, fx + fw, wy + fh], radius=fr, fill=frame_color)

    return layer


def render_icon(size: int) -> Image.Image:
    s  = size
    sc = s / 300.0
    bg_r = max(6, int(40 * sc))   # SVG rx=40 on the background rect

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)

    # Background rounded square
    pad = max(1, int(2 * sc))
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=bg_r, fill=BG)

    cx, cy = s // 2, s // 2
    offset = int(55 * sc)   # SVG translate(-55,0) / translate(55,0)

    # ── Left strip (blue, rotated -12°, shifted left) ────────────────────────
    l_layer  = draw_strip_layer(s, WIN_L)
    l_rot    = l_layer.rotate(12, resample=Image.BICUBIC, expand=False)
    l_canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    l_canvas.paste(l_rot, (-offset, 0), l_rot)
    img = Image.alpha_composite(img, l_canvas)

    # ── Right strip (orange, rotated +12°, shifted right) ────────────────────
    r_layer  = draw_strip_layer(s, WIN_R)
    r_rot    = r_layer.rotate(-12, resample=Image.BICUBIC, expand=False)
    r_canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    r_canvas.paste(r_rot, (offset, 0), r_rot)
    img = Image.alpha_composite(img, r_canvas)

    # ── Scissors (SVG centered at 0,-6 relative to canvas center) ────────────
    # SVG scissors:
    #   top blade:    M-28,-18  Q0,0  28,-18   (curved upward V)
    #   bottom blade: M-28, 18  Q0,0  28, 18   (curved downward V)
    #   pivot dot:    circle r=5
    #   handle rings: circle cx=-38 cy=±20 r=9

    d2  = ImageDraw.Draw(img)
    scx = cx                        # scissors center x
    scy = cy + int(-6 * sc)         # scissors center y (SVG offset -6)
    lw  = max(2, int(5 * sc))       # line width

    # Top blade curve
    top_pts = bezier(
        (scx + int(-28*sc), scy + int(-18*sc)),
        (scx,                scy               ),
        (scx + int( 28*sc), scy + int(-18*sc)),
        steps=40
    )
    d2.line([(int(x), int(y)) for x,y in top_pts], fill=SCISSORS, width=lw)

    # Bottom blade curve
    bot_pts = bezier(
        (scx + int(-28*sc), scy + int( 18*sc)),
        (scx,                scy               ),
        (scx + int( 28*sc), scy + int( 18*sc)),
        steps=40
    )
    d2.line([(int(x), int(y)) for x,y in bot_pts], fill=SCISSORS, width=lw)

    # Pivot dot
    pr = max(2, int(5 * sc))
    d2.ellipse([scx-pr, scy-pr, scx+pr, scy+pr], fill=SCISSORS)

    # Handle rings (only drawn at larger sizes where they're visible)
    if size >= 32:
        hr   = max(3, int(9  * sc))
        hcx  = scx + int(-38 * sc)
        hcy1 = scy + int(-20 * sc)
        hcy2 = scy + int( 20 * sc)
        hw   = max(1, int(3 * sc))
        d2.ellipse([hcx-hr, hcy1-hr, hcx+hr, hcy1+hr], outline=SCISSORS, width=hw)
        d2.ellipse([hcx-hr, hcy2-hr, hcx+hr, hcy2+hr], outline=SCISSORS, width=hw)

    return img


# ── ICO builder ───────────────────────────────────────────────────────────────

def build_ico(sizes=(256, 128, 64, 48, 32, 16)) -> bytes:
    images = []
    for sz in sizes:
        buf = io.BytesIO()
        render_icon(sz).save(buf, "PNG")
        images.append((sz, buf.getvalue()))

    num    = len(images)
    header = struct.pack('<HHH', 0, 1, num)
    offset = 6 + num * 16
    entries, data = b'', b''
    for sz, png in images:
        w = sz if sz < 256 else 0
        h = sz if sz < 256 else 0
        entries += struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(png), offset)
        data    += png
        offset  += len(png)
    return header + entries + data


def write_bmp(path, w, h, bgr):
    rw  = ((w * 3 + 3) // 4) * 4
    row = bytes(bgr) * w + bytes(rw - w * 3)
    px  = row * h
    fs  = 54 + len(px)
    with open(path, 'wb') as f:
        f.write(b'BM' + struct.pack('<I',fs) + b'\x00\x00\x00\x00' +
                struct.pack('<I',54) + struct.pack('<I',40) +
                struct.pack('<ii',w,h) + struct.pack('<HH',1,24) +
                struct.pack('<I',0) + struct.pack('<I',len(px)) +
                struct.pack('<ii',2835,2835) + struct.pack('<II',0,0) + px)


if __name__ == "__main__":
    print("Generating Option B icon...")

    ico = build_ico()
    with open("assets/icon.ico", "wb") as f: f.write(ico)
    print(f"  -> assets/icon.ico  ({len(ico):,} bytes)")

    render_icon(256).save("assets/icon_preview.png", "PNG")
    print("  -> assets/icon_preview.png")

    write_bmp("assets/wizard_banner.bmp", 164, 314, [23, 17, 13])
    write_bmp("assets/wizard_small.bmp",   55,  58, [23, 17, 13])
    print("  -> wizard bitmaps")
    print("Done.")
