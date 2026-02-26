"""Generate X banner image for @claudemakes: panoramic emergence in gold on dark.
1500x500 pixels. Multiple attractor fragments + flow particles spanning the width.
Enhanced version: bolder, more contrast, reads well at small sizes."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1500, 500
BG = (8, 8, 12)
img = Image.new('RGB', (W, H), BG)
layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(layer)

# --- Section 1: Lorenz attractor (left-center, larger) ---
sigma, rho, beta = 10.0, 28.0, 8.0/3.0
dt = 0.002
x, y, z = 0.1, 0.0, 0.0
lorenz_pts = []
for _ in range(80000):
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    x += dx * dt
    y += dy * dt
    z += dz * dt
    lorenz_pts.append((x, z))

lorenz_pts = np.array(lorenz_pts)
lx_min, lx_max = lorenz_pts[:, 0].min(), lorenz_pts[:, 0].max()
ly_min, ly_max = lorenz_pts[:, 1].min(), lorenz_pts[:, 1].max()
lscale = min(500 / (lx_max - lx_min), 300 / (ly_max - ly_min))
lox = (lx_max + lx_min) / 2
loy = (ly_max + ly_min) / 2
lcx, lcy = 380, 250

n = len(lorenz_pts)
for i in range(1, n):
    px = lcx + (lorenz_pts[i-1, 0] - lox) * lscale
    py = lcy + (lorenz_pts[i-1, 1] - loy) * lscale
    qx = lcx + (lorenz_pts[i, 0] - lox) * lscale
    qy = lcy + (lorenz_pts[i, 1] - loy) * lscale
    t = i / n
    r = int(210 + 45 * t)
    g = int(165 + 45 * t)
    b = int(60 + 40 * t)
    a = int(30 + 70 * t)
    draw.line([(px, py), (qx, qy)], fill=(r, g, b, a), width=1)

# --- Section 2: Halvorsen attractor (right side, larger) ---
a_h = 1.89
dt2 = 0.003
x2, y2, z2 = 1.0, 0.0, 0.0
halv_pts = []
for _ in range(60000):
    dx2 = -a_h*x2 - 4*y2 - 4*z2 - y2*y2
    dy2 = -a_h*y2 - 4*z2 - 4*x2 - z2*z2
    dz2 = -a_h*z2 - 4*x2 - 4*y2 - x2*x2
    x2 += dx2 * dt2
    y2 += dy2 * dt2
    z2 += dz2 * dt2
    halv_pts.append((x2, y2))

halv_pts = np.array(halv_pts)
hx_min, hx_max = halv_pts[:, 0].min(), halv_pts[:, 0].max()
hy_min, hy_max = halv_pts[:, 1].min(), halv_pts[:, 1].max()
hscale = min(380 / (hx_max - hx_min), 280 / (hy_max - hy_min))
hox = (hx_max + hx_min) / 2
hoy = (hy_max + hy_min) / 2
hcx, hcy = 1100, 250

n2 = len(halv_pts)
for i in range(1, n2):
    px = hcx + (halv_pts[i-1, 0] - hox) * hscale
    py = hcy + (halv_pts[i-1, 1] - hoy) * hscale
    qx = hcx + (halv_pts[i, 0] - hox) * hscale
    qy = hcy + (halv_pts[i, 1] - hoy) * hscale
    t = i / n2
    r = int(190 + 55 * t)
    g = int(150 + 55 * t)
    b = int(70 + 45 * t)
    a = int(25 + 60 * t)
    draw.line([(px, py), (qx, qy)], fill=(r, g, b, a), width=1)

# --- Section 3: Thomas attractor (center, subtle) ---
b_t = 0.208186
dt3 = 0.05
x3, y3, z3 = 1.1, 1.1, -0.01
thomas_pts = []
for _ in range(40000):
    dx3 = np.sin(y3) - b_t * x3
    dy3 = np.sin(z3) - b_t * y3
    dz3 = np.sin(x3) - b_t * z3
    x3 += dx3 * dt3
    y3 += dy3 * dt3
    z3 += dz3 * dt3
    thomas_pts.append((x3, y3))

thomas_pts = np.array(thomas_pts)
tx_min, tx_max = thomas_pts[:, 0].min(), thomas_pts[:, 0].max()
ty_min, ty_max = thomas_pts[:, 1].min(), thomas_pts[:, 1].max()
tscale = min(200 / (tx_max - tx_min), 180 / (ty_max - ty_min))
tox = (tx_max + tx_min) / 2
toy = (ty_max + ty_min) / 2
tcx, tcy = 750, 250

n3 = len(thomas_pts)
for i in range(1, n3):
    px = tcx + (thomas_pts[i-1, 0] - tox) * tscale
    py = tcy + (thomas_pts[i-1, 1] - toy) * tscale
    qx = tcx + (thomas_pts[i, 0] - tox) * tscale
    qy = tcy + (thomas_pts[i, 1] - toy) * tscale
    t = i / n3
    r = int(170 + 50 * t)
    g = int(140 + 40 * t)
    b = int(70 + 35 * t)
    a = int(12 + 30 * t)
    draw.line([(px, py), (qx, qy)], fill=(r, g, b, a), width=1)

# --- Section 4: Flowing particles connecting everything (curl noise) ---
np.random.seed(42)
num_particles = 500
for _ in range(num_particles):
    px = np.random.uniform(0, W)
    py = np.random.uniform(0, H)
    trail = [(px, py)]
    for step in range(250):
        freq = 0.003
        angle = (np.sin(px * freq * 1.3 + py * freq * 0.7) *
                 np.cos(py * freq * 1.1 - px * freq * 0.5) * np.pi * 2)
        angle += np.sin(px * freq * 2.7 + py * freq * 1.9) * 0.6
        vx = np.cos(angle) * 1.8
        vy = np.sin(angle) * 1.8
        px += vx
        py += vy
        if px < -10 or px > W + 10 or py < -10 or py > H + 10:
            break
        trail.append((px, py))

    if len(trail) > 3:
        for i in range(1, len(trail)):
            t = i / len(trail)
            r = int(180 + 50 * t)
            g = int(150 + 40 * t)
            b = int(80 + 25 * t)
            a = int(10 + 25 * t)
            draw.line([trail[i-1], trail[i]], fill=(r, g, b, a), width=1)

# --- Section 5: Scattered dots (stars / particles) ---
for _ in range(600):
    dx = np.random.randint(0, W)
    dy = np.random.randint(0, H)
    brightness = np.random.uniform(0.3, 1.0)
    r = int(230 * brightness)
    g = int(190 * brightness)
    b = int(110 * brightness)
    a = int(50 + 100 * brightness)
    size = 1 if np.random.random() < 0.75 else 2
    draw.ellipse([dx-size, dy-size, dx+size, dy+size], fill=(r, g, b, a))

# Composite with layered glow
glow_tight = layer.filter(ImageFilter.GaussianBlur(radius=2))
glow_wide = layer.filter(ImageFilter.GaussianBlur(radius=6))
glow_bloom = layer.filter(ImageFilter.GaussianBlur(radius=12))

result = Image.new('RGBA', (W, H), (*BG, 255))
result = Image.alpha_composite(result, glow_bloom)
result = Image.alpha_composite(result, glow_wide)
result = Image.alpha_composite(result, glow_tight)
result = Image.alpha_composite(result, layer)

# Subtle vignette
vignette = Image.new('RGBA', (W, H), (0, 0, 0, 0))
vdraw = ImageDraw.Draw(vignette)
for i in range(80):
    edge_alpha = int(4 * (80 - i) / 80)
    vdraw.rectangle([i, i, W-1-i, H-1-i], outline=(0, 0, 0, edge_alpha))
result = Image.alpha_composite(result, vignette)

out = result.convert('RGB')
out.save('/Users/liberbey/Projects/claudes-corner/banner.png')
print(f"Banner saved: banner.png ({W}x{H})")
