"""Generate a profile picture for @claudemakes: Lorenz attractor in gold on dark."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 800
img = Image.new('RGB', (SIZE, SIZE), (8, 8, 12))
draw = ImageDraw.Draw(img)

# Simulate Lorenz attractor
sigma, rho, beta = 10.0, 28.0, 8.0/3.0
dt = 0.002
x, y, z = 0.1, 0.0, 0.0
points = []

for _ in range(60000):
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    x += dx * dt
    y += dy * dt
    z += dz * dt
    points.append((x, z))  # x-z projection gives the butterfly

points = np.array(points)

# Normalize to fit canvas with padding
pad = 100
xmin, xmax = points[:, 0].min(), points[:, 0].max()
ymin, ymax = points[:, 1].min(), points[:, 1].max()
scale = min((SIZE - 2*pad) / (xmax - xmin), (SIZE - 2*pad) / (ymax - ymin))
cx = SIZE / 2
cy = SIZE / 2
ox = (xmax + xmin) / 2
oy = (ymax + ymin) / 2

# Draw with varying opacity for depth
layer = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
ldraw = ImageDraw.Draw(layer)

n = len(points)
for i in range(1, n):
    px = cx + (points[i-1, 0] - ox) * scale
    py = cy + (points[i-1, 1] - oy) * scale
    qx = cx + (points[i, 0] - ox) * scale
    qy = cy + (points[i, 1] - oy) * scale

    # Color: warm golden, alpha varies with position in trace
    t = i / n
    r = int(220 + 35 * t)
    g = int(170 + 40 * t)
    b = int(80 + 30 * t)
    a = int(15 + 35 * t)

    ldraw.line([(px, py), (qx, qy)], fill=(r, g, b, a), width=1)

# Blur slightly for glow
glow = layer.filter(ImageFilter.GaussianBlur(radius=2))
# Composite: glow then sharp
result = Image.new('RGBA', (SIZE, SIZE), (8, 8, 12, 255))
result = Image.alpha_composite(result, glow)
result = Image.alpha_composite(result, layer)

# Save
out = result.convert('RGB')
out.save('/Users/liberbey/Projects/claudes-corner/avatar.png')

# Also save a 400x400 version
small = out.resize((400, 400), Image.LANCZOS)
small.save('/Users/liberbey/Projects/claudes-corner/avatar-400.png')

print("Avatar saved: avatar.png (800x800), avatar-400.png (400x400)")
