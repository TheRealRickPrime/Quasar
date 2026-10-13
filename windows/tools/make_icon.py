"""Render the Quasar icon: a glowing padlock floating in deep space.

Run: python tools/make_icon.py   (writes assets/quasar.png and assets/quasar.ico)
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 1024
ROOT = Path(__file__).resolve().parent.parent / "assets"


def radial(size, inner, outer, center=None, radius=None):
    cx, cy = center or (size / 2, size / 2)
    radius = radius or size / 2
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = min(math.hypot(x - cx, y - cy) / radius, 1.0)
            px[x, y] = tuple(int(inner[i] + (outer[i] - inner[i]) * t) for i in range(4))
    return img


def glow(layer, radius, strength=1.0):
    blurred = layer.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        a = blurred.getchannel("A").point(lambda v: min(255, int(v * strength)))
        blurred.putalpha(a)
    return blurred


def lock_mask(pad=0):
    """Mask of the padlock silhouette (body + shackle)."""
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((262 - pad, 456 - pad, 762 + pad, 806 + pad), 70 + pad, fill=255)
    d.arc((352 - pad, 190 - pad, 672 + pad, 590 + pad), 180, 360, fill=255, width=70 + 2 * pad)
    d.rectangle((352 - pad, 390, 422 + pad, 470), fill=255)
    d.rectangle((602 - pad, 390, 672 + pad, 470), fill=255)
    return m


def build():
    random.seed(7)
    base = radial(S, (24, 34, 78, 255), (3, 5, 16, 255), center=(S * 0.42, S * 0.38), radius=S * 0.8)

    # nebula washes
    neb = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    nd = ImageDraw.Draw(neb)
    nd.ellipse((520, 80, 980, 540), fill=(140, 60, 255, 110))
    nd.ellipse((40, 520, 560, 980), fill=(0, 190, 255, 90))
    base = Image.alpha_composite(base, glow(neb, 120))

    # stars
    stars = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stars)
    for _ in range(140):
        x, y = random.randrange(S), random.randrange(S)
        r = random.choice([1.5, 2, 2, 3, 4])
        a = random.randint(110, 255)
        sd.ellipse((x - r, y - r, x + r, y + r), fill=(230, 240, 255, a))
    base = Image.alpha_composite(base, glow(stars, 2, 1.0))
    base = Image.alpha_composite(base, stars)

    # comet trail sweeping behind the lock
    trail = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    td = ImageDraw.Draw(trail)
    for i in range(60):
        t = i / 60
        x, y = 90 + t * 300, 130 + t * 260
        r = 3 + t * 16
        td.ellipse((x - r, y - r, x + r, y + r), fill=(120, 220, 255, int(30 + 150 * t)))
    base = Image.alpha_composite(base, glow(trail, 10))
    base = Image.alpha_composite(base, trail)

    # lock glow layers
    cyan, violet = (70, 225, 255), (170, 100, 255)
    mask = lock_mask()
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    halo.paste(Image.new("RGBA", (S, S), violet + (255,)), mask=lock_mask(22))
    base = Image.alpha_composite(base, glow(halo, 60, 1.6))
    halo2 = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    halo2.paste(Image.new("RGBA", (S, S), cyan + (255,)), mask=lock_mask(6))
    base = Image.alpha_composite(base, glow(halo2, 22, 1.3))

    # lock fill: dark glass with a cyan -> violet gradient rim
    grad = Image.new("RGBA", (S, S))
    gp = grad.load()
    for y in range(S):
        for x in range(S):
            t = min(max((x + y - 400) / 900, 0), 1)
            gp[x, y] = tuple(int(cyan[i] + (violet[i] - cyan[i]) * t) for i in range(3)) + (255,)
    rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rim.paste(grad, mask=mask)
    base = Image.alpha_composite(base, rim)

    inner = lock_mask(-14)
    glass = radial(S, (28, 40, 96, 255), (8, 12, 34, 255), center=(S / 2, 560), radius=420)
    fill = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    fill.paste(glass, mask=inner)
    base = Image.alpha_composite(base, fill)

    # keyhole: glowing star-core
    key = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    kd = ImageDraw.Draw(key)
    kd.ellipse((452, 540, 572, 660), fill=(255, 255, 255, 255))
    kd.polygon([(492, 640), (532, 640), (546, 740), (478, 740)], fill=(255, 255, 255, 255))
    base = Image.alpha_composite(base, glow(key, 28, 2.0))
    base = Image.alpha_composite(base, glow(key, 8, 1.5))
    base = Image.alpha_composite(base, key)

    # four-point sparkle on the shackle
    sp = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    spd = ImageDraw.Draw(sp)
    cx, cy = 700, 250
    spd.polygon([(cx, cy - 70), (cx + 10, cy - 10), (cx + 70, cy), (cx + 10, cy + 10),
                 (cx, cy + 70), (cx - 10, cy + 10), (cx - 70, cy), (cx - 10, cy - 10)],
                fill=(255, 255, 255, 255))
    base = Image.alpha_composite(base, glow(sp, 14, 2.0))
    base = Image.alpha_composite(base, sp)

    # circular badge with a soft rim
    badge = Image.new("L", (S, S), 0)
    ImageDraw.Draw(badge).ellipse((24, 24, S - 24, S - 24), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(base, mask=badge)
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((24, 24, S - 24, S - 24), outline=cyan + (200,), width=10)
    out = Image.alpha_composite(out, glow(ring, 8, 1.2))
    out = Image.alpha_composite(out, ring)
    return out


def main():
    ROOT.mkdir(exist_ok=True)
    icon = build()
    icon.resize((512, 512), Image.LANCZOS).save(ROOT / "quasar.png")
    sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
    icon.save(ROOT / "quasar.ico", sizes=[(s, s) for s in sizes])
    print("wrote", ROOT / "quasar.png", ROOT / "quasar.ico")


if __name__ == "__main__":
    main()
