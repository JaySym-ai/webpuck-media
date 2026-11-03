"""Frame renderer: camera moves over real page captures, marker sweeps, rings, captions.
Shots and overlays are in global seconds. Page coordinates are capture pixels (DPR 2)."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

Image.MAX_IMAGE_PIXELS = None
BASE = os.path.dirname(os.path.abspath(__file__)) + '/..'
CAP = BASE + '/cap/'
VID = BASE + '/raw/vid/'
FONT_XB = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
FONT_SB = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
YELLOW = (255, 214, 0)
RED = (255, 59, 48)


def ease(u, kind='io'):
    u = min(1.0, max(0.0, u))
    if kind == 'lin':
        return u
    if kind == 'out':  # punch: fast in, soft land
        return 1 - (1 - u) ** 4
    if kind == 'sine':
        return 0.5 - 0.5 * math.cos(math.pi * u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


# ---------------------------------------------------------------- pages
class Page:
    def __init__(self, name):
        self.name = name
        self.im = Image.open(CAP + name + '.png').convert('RGB')
        self.W, self.H = self.im.size
        p = CAP + name + '.json'
        self.bx = json.load(open(p)) if os.path.exists(p) else {}
        a = np.asarray(self.im.crop((0, 0, min(40, self.W), min(40, self.H))))
        self.bg = tuple(int(v) for v in a.reshape(-1, 3).mean(0))


_pages = {}


def page(name):
    if name not in _pages:
        if len(_pages) > 4:
            _pages.pop(next(iter(_pages)))
        _pages[name] = Page(name)
    return _pages[name]


_meta = {}


def meta(name):
    """Boxes and size without loading pixels."""
    if name not in _meta:
        im = Image.open(CAP + name + '.png')
        p = CAP + name + '.json'
        _meta[name] = (im.size, json.load(open(p)) if os.path.exists(p) else {})
    return _meta[name]


def lines(name, key, occ=0):
    (_, bx) = meta(name)
    v = bx.get(key)
    if not v:
        raise KeyError(f'{name}: no box for {key!r}')
    return [list(r) for r in v[min(occ, len(v) - 1)]]


class Rect(list):
    blk = None


def _u(rs):
    return [min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)]


def box(name, key, occ=0):
    r = Rect(_u(lines(name, key, occ)))
    (_, bx) = meta(name)
    b = bx.get(key + '@blk')
    if b:
        r.blk = list(b[min(occ, len(b) - 1)][0])
    return r


def union(*rs):
    r = Rect(_u(rs))
    bl = [x.blk for x in rs if getattr(x, 'blk', None)]
    r.blk = _u(bl) if bl else None
    return r


def center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


# ---------------------------------------------------------------- camera
class Cam:
    """keys: list of (t_start, dur, cx, cy, vw, kind). State before first key = first key."""
    def __init__(self, keys):
        self.keys = sorted(keys, key=lambda k: k[0])

    def at(self, t):
        k0 = self.keys[0]
        cx, cy, vw = k0[2], k0[3], k0[4]
        for (ts, d, x, y, w, kind) in self.keys[1:]:
            if t <= ts:
                break
            u = 1.0 if d <= 0 else ease((t - ts) / d, kind)
            cx += (x - cx) * u
            cy += (y - cy) * u
            vw = math.exp(math.log(vw) + (math.log(w) - math.log(vw)) * u)
        return cx, cy, vw


def clamp_view(cx, cy, vw, vh, PW, PH):
    x0, y0 = cx - vw / 2, cy - vh / 2
    x0 = (PW - vw) / 2 if vw >= PW else min(max(0, x0), PW - vw)
    y0 = (PH - vh) / 2 if vh >= PH else min(max(0, y0), PH - vh)
    return x0, y0


# ---------------------------------------------------------------- overlays
def draw_marker(frame, rects_screen, prog, dark):
    """prog 0..1 sweeps across the lines in order."""
    a = np.asarray(frame).astype(np.float32)
    total = sum(r[2] - r[0] for r in rects_screen) or 1
    done = prog * total
    for r in rects_screen:
        w = r[2] - r[0]
        if done <= 0:
            break
        x1 = r[0] + min(w, done)
        done -= w
        pad_y = (r[3] - r[1]) * 0.12
        X0, X1 = int(max(0, r[0] - 6)), int(min(a.shape[1], x1 + 6))
        Y0, Y1 = int(max(0, r[1] - pad_y)), int(min(a.shape[0], r[3] + pad_y))
        if X1 <= X0 or Y1 <= Y0:
            continue
        reg = a[Y0:Y1, X0:X1]
        col = np.array(YELLOW, np.float32)
        if dark:
            reg[:] = np.minimum(255, reg * 1.12 + 10)
            th = max(4, int((r[3] - r[1]) * 0.16))
            yb0 = int(min(a.shape[0] - 1, r[3] + pad_y * 0.3))
            a[yb0:yb0 + th, X0:X1] = col
        else:
            reg[:] = reg * (0.18 + 0.82 * col / 255.0)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def ring_points(r, seed):
    cx, cy = center(r)
    rx = (r[2] - r[0]) / 2 * 1.18 + 18
    ry = (r[3] - r[1]) / 2 * 1.45 + 16
    rng = np.random.RandomState(seed)
    ph = rng.uniform(0, 6.28)
    pts = []
    n = 90
    for i in range(n + 9):  # overshoot a bit, like a hand-drawn loop
        th = -2.2 + 2 * math.pi * i / n
        wob = 1 + 0.035 * math.sin(3 * th + ph) + 0.02 * i / n
        pts.append((cx + rx * wob * math.cos(th), cy + ry * wob * math.sin(th)))
    return pts


def draw_ring(frame, r_screen, prog, width, seed=1):
    pts = ring_points(r_screen, seed)
    k = max(2, int(len(pts) * prog))
    d = ImageDraw.Draw(frame)
    d.line(pts[:k], fill=RED, width=width, joint='curve')
    for p in (pts[0], pts[k - 1]):
        d.ellipse([p[0] - width / 2, p[1] - width / 2, p[0] + width / 2, p[1] + width / 2], fill=RED)
    return frame


def whip_blur(frame, strength, direction=1):
    if strength <= 0.02:
        return frame
    a = np.asarray(frame).astype(np.float32)
    n = 9
    span = int(140 * strength)
    acc = np.zeros_like(a)
    for i in range(n):
        acc += np.roll(a, direction * int(span * i / (n - 1)), axis=1)
    return Image.fromarray((acc / n).astype(np.uint8))


# ---------------------------------------------------------------- text
_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


def draw_caption(frame, words, active, cx, cy, size, maxw):
    """words: list of strings; active index highlighted. Wraps to 2 lines if needed."""
    f = font(FONT_XB, size)
    d = ImageDraw.Draw(frame)
    sp = size * 0.30
    widths = [d.textlength(w, font=f) for w in words]
    rows, cur, cw = [], [], 0
    for i, w in enumerate(widths):
        if cur and cw + sp + w > maxw:
            rows.append(cur); cur, cw = [], 0
        cw = cw + (sp if cur else 0) + w
        cur.append(i)
    if cur:
        rows.append(cur)
    lh = size * 1.18
    y = cy - lh * len(rows) / 2
    stroke = max(4, size // 9)
    for row in rows:
        tw = sum(widths[i] for i in row) + sp * (len(row) - 1)
        x = cx - tw / 2
        for i in row:
            col = YELLOW if i == active else (255, 255, 255)
            d.text((x + 3, y + 5), words[i], font=f, fill=(0, 0, 0), stroke_width=stroke, stroke_fill=(0, 0, 0))
            d.text((x, y), words[i], font=f, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0))
            x += widths[i] + sp
        y += lh
    return frame


def draw_label(frame, text, x, y, size, anchor='ls', alpha=170):
    f = font(FONT_SB, size)
    ov = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    l, t, r, b = d.textbbox((x, y), text, font=f, anchor=anchor)
    pad = size * 0.45
    d.rounded_rectangle([l - pad, t - pad * 0.8, r + pad, b + pad * 0.8], radius=size * 0.5, fill=(0, 0, 0, alpha))
    d.text((x, y), text, font=f, fill=(255, 255, 255, 255), anchor=anchor)
    return Image.alpha_composite(frame.convert('RGBA'), ov).convert('RGB')


# ---------------------------------------------------------------- shot render
def render_page_frame(sh, t, W, H):
    pg = page(sh['src'])
    cx, cy, vw = sh['cam'].at(t)
    vh = vw * H / W
    x0, y0 = clamp_view(cx, cy, vw, vh, pg.W, pg.H)
    s = W / vw
    bg = sh.get('bg', pg.bg)
    fr = pg.im.transform((W, H), Image.AFFINE, (1 / s, 0, x0, 0, 1 / s, y0), resample=Image.BILINEAR, fillcolor=bg)
    to_s = lambda r: [(r[0] - x0) * s, (r[1] - y0) * s, (r[2] - x0) * s, (r[3] - y0) * s]
    for fx in sh.get('fx', []):
        if t < fx['t']:
            continue
        prog = min(1.0, (t - fx['t']) / fx.get('d', 0.5))
        if 'until' in fx and t > fx['until']:
            continue
        if fx['type'] == 'marker':
            rs = [to_s(r) for r in fx['rects']]
            dark = fx.get('dark')
            if dark is None:
                rr = fx['rects'][0]
                reg = np.asarray(pg.im.crop((int(rr[0]), int(rr[1]), int(rr[2]) + 1, int(rr[3]) + 1)))
                dark = reg.mean() < 110
                fx['dark'] = dark
            fr = draw_marker(fr, rs, ease(prog, 'io'), dark)
        elif fx['type'] == 'ring':
            fr = draw_ring(fr, to_s(fx['rect']), ease(prog, 'out'), fx.get('w', 8), fx.get('seed', 1))
    return fr


def render_video_frame(sh, t, W, H):
    vt = sh['vt0'] + (t - sh['t0']) * sh.get('rate', 1.0)
    n = min(587, max(1, int(vt * 30) + 1))
    im = Image.open(VID + 'f%04d.jpg' % n).convert('RGB')
    crop = sh.get('crop')  # (cx, cy, vw) in 1920x1080 video px
    if crop:
        cx, cy, vw = crop
        vh = vw * H / W
        x0, y0 = clamp_view(cx, cy, vw, vh, 1920, 1080)
        s = W / vw
        return im.transform((W, H), Image.AFFINE, (1 / s, 0, x0, 0, 1 / s, y0), resample=Image.BILINEAR)
    return im.resize((W, H), Image.BILINEAR)


def render_frame(EDL, t, W, H):
    sh = None
    for s in EDL['shots']:
        if s['t0'] <= t < s['t1']:
            sh = s
            break
    if sh is None:
        sh = EDL['shots'][-1]
    fr = render_video_frame(sh, t, W, H) if sh['src'] == 'video' else render_page_frame(sh, t, W, H)
    # whip transitions around cut points
    wd = 0.2
    if sh.get('whip_in') and t - sh['t0'] < wd:
        fr = whip_blur(fr, 1 - (t - sh['t0']) / wd, 1)
    if sh.get('whip_out') and sh['t1'] - t < wd:
        fr = whip_blur(fr, 1 - (sh['t1'] - t) / wd, -1)
    if sh.get('dim'):
        a = np.asarray(fr).astype(np.float32)
        k = 1 - 0.55 * min(1, (t - sh['t0']) / 0.6)
        fr = Image.fromarray((a * k).astype(np.uint8))
    for lb in EDL.get('labels', []):
        if lb['t0'] <= t < lb['t1']:
            fr = lb['fn'](fr, t)
    cap = EDL['captions']
    for c in cap['chunks']:
        if c['t0'] <= t < c['t1']:
            act = 0
            for i, (w, ws, we) in enumerate(c['words']):
                if t >= ws:
                    act = i
            fr = draw_caption(fr, [w for w, _, _ in c['words']], act, cap['cx'], cap['cy'], cap['size'], cap['maxw'])
            break
    return fr


def render_range(EDL, f0, f1, W, H, out):
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', '30', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
           '-pix_fmt', 'yuv420p', '-x264-params', 'threads=2', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        fr = render_frame(EDL, f / 30.0, W, H)
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()


# ---------------------------------------------------------------- captions from words
def load_words(path):
    d = json.load(open(path))
    return [w for w in d['words'] if w.get('type') == 'word']


def find(words, phrase, n=0, after=0.0):
    """start time of the nth occurrence of phrase (word sequence) at/after time `after`."""
    raw = phrase.split()
    toks = [norm(x) for x in raw]
    hits = []
    for i in range(len(words) - len(toks) + 1):
        if words[i]['start'] < after:
            continue
        if all(tokmatch(words[i + j]['text'], raw[j]) for j in range(len(toks))):
            hits.append(i)
    if len(hits) <= n:
        raise KeyError(f'phrase not found: {phrase!r} after {after}')
    i = hits[n]
    return words[i]['start'], words[i + len(toks) - 1]['end']


def tokmatch(word, tok):
    if norm(word) != norm(tok):
        return False
    p = tok[-1] if not tok[-1].isalnum() else ''
    return (not p) or word.endswith(p)


def norm(s):
    return ''.join(ch for ch in s.lower() if ch.isalnum())


SUBS = [(['two', 'hundred', 'and', 'fifty', 'K'], '250K'), (['A', 'D', 'B'], 'adb'), (['A', 'D', 'B,'], 'adb,'),
        (['tee-mux'], 'tmux'), (['e-SIM,'], 'eSIM,'), (['e-SIM.'], 'eSIM.'), (['mobile', 'MCP,'], 'mobile-mcp,')]


def caption_chunks(words, max_words=4, max_chars=22, tail=0.35):
    toks = []
    i = 0
    while i < len(words):
        hit = None
        for pat, rep in SUBS:
            if [w['text'] for w in words[i:i + len(pat)]] == pat:
                hit = (len(pat), rep)
                break
        if hit:
            toks.append([hit[1], words[i]['start'], words[i + hit[0] - 1]['end']])
            i += hit[0]
        else:
            toks.append([words[i]['text'], words[i]['start'], words[i]['end']])
            i += 1
    chunks, cur = [], []
    for k, tk in enumerate(toks):
        cur.append(tk)
        txt = ' '.join(x[0] for x in cur)
        nxt = toks[k + 1] if k + 1 < len(toks) else None
        brk = (tk[0][-1] in '.,?!:' or len(cur) >= max_words or
               (nxt and len(txt) + 1 + len(nxt[0]) > max_chars) or nxt is None or
               (nxt and nxt[1] - tk[2] > 0.45))
        if brk:
            chunks.append(cur)
            cur = []
    out = []
    for j, c in enumerate(chunks):
        t0 = c[0][1]
        t1 = c[-1][2] + tail
        if j + 1 < len(chunks):
            t1 = min(t1 if chunks[j + 1][0][1] - c[-1][2] > 0.6 else chunks[j + 1][0][1], chunks[j + 1][0][1])
        out.append({'t0': t0, 't1': t1, 'words': [(x[0].rstrip(',.:;'), x[1], x[2]) for x in c]})
    return out
