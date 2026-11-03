"""1080x1920 cover (also frame 1 of the Short): real Kimi + Hugging Face logos, big NOV 4, red WEIGHTS? stamp."""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__)) + '/..'
W, H = 1080, 1920
BLACK = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
XB = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32) + np.array([11, 12, 18], np.float32)
def glow(cx, cy, r, col, k):
    return np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))[..., None] * np.array(col, np.float32) * k
bg += glow(540, 880, 520, (40, 90, 255), 0.45)
bg += glow(820, 1250, 380, (255, 59, 48), 0.30)
img = Image.fromarray(bg.clip(0, 255).astype(np.uint8)).convert('RGBA')

def shadowed(base, im, xy, blur=18, alpha=150, off=(0, 12)):
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').point(lambda a: a * alpha // 255))
    pad = blur * 3
    big = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); big.paste(sh, (pad, pad), sh)
    base.alpha_composite(big.filter(ImageFilter.GaussianBlur(blur)), (xy[0] - pad + off[0], xy[1] - pad + off[1]))
    base.alpha_composite(im, xy)

# Kimi wordmark: the site's SVG uses currentColor, rendered here in white
k = Image.open(BASE + '/logos/kimi_logo.png').convert('RGBA')
k = k.crop(k.getbbox())
white = Image.new('RGBA', k.size, (255, 255, 255, 255)); white.putalpha(k.getchannel('A')); k = white
k = k.resize((420, int(k.height * 420 / k.width)), Image.LANCZOS)
hf = Image.open(BASE + '/logos/hf_logo.png').convert('RGBA'); hf = hf.crop(hf.getbbox())
hf = hf.resize((210, int(hf.height * 210 / hf.width)), Image.LANCZOS)
d = ImageDraw.Draw(img)
top = 400
shadowed(img, k, (110, top + (hf.height - k.height) // 2))
fx = ImageFont.truetype(XB, 90)
d.text((598, top + hf.height // 2), '+', font=fx, fill=(255, 255, 255, 200), anchor='mm')
shadowed(img, hf, (665, top))

# big NOV 4
f = ImageFont.truetype(BLACK, 300)
while ImageDraw.Draw(img).textlength('NOV 4', font=f) > 820: f = ImageFont.truetype(BLACK, f.size - 10)
d.text((480 + 8, 900 + 14), 'NOV 4', font=f, fill=(0, 0, 0, 150), anchor='mm', stroke_width=12, stroke_fill=(0, 0, 0, 150))
d.text((480, 900), 'NOV 4', font=f, fill=(255, 255, 255, 255), anchor='mm', stroke_width=10, stroke_fill=(0, 0, 0, 255))

# red WEIGHTS? stamp, rotated
st = Image.new('RGBA', (820, 290), (0, 0, 0, 0))
sd = ImageDraw.Draw(st)
red = (255, 48, 48, 255)
sd.rounded_rectangle([12, 12, 808, 278], radius=28, outline=red, width=20)
sd.rounded_rectangle([40, 40, 780, 250], radius=16, outline=red, width=6)
sd.text((410, 147), 'WEIGHTS?', font=ImageFont.truetype(BLACK, 138), fill=red, anchor='mm')
# light stamp texture: knock out random specks
rng = np.random.RandomState(7)
a = np.asarray(st).copy()
mask = rng.rand(*a.shape[:2]) < 0.06
a[..., 3][mask] = (a[..., 3][mask] * 0.25).astype(np.uint8)
st = Image.fromarray(a).rotate(-8, expand=True, resample=Image.BICUBIC)
img.alpha_composite(st, (480 - st.width // 2, 1230 - st.height // 2))

out = img.convert('RGB')
out.save(BASE + '/out/cover.png', optimize=True)
out.save(BASE + '/cap/cover.png')
json.dump({}, open(BASE + '/cap/cover.json', 'w'))
print('cover saved', out.size)
