"""Shared helpers for building edit decision lists."""
from engine import *


class Builder:
    def __init__(self, W, H, words):
        self.W, self.H, self.words = W, H, words
        self.shots = []

    def T(self, phrase, n=0, after=0.0):
        return find(self.words, phrase, n, after)[0]

    def TE(self, phrase, n=0, after=0.0):
        return find(self.words, phrase, n, after)[1]

    # camera targets -> (cx, cy, vw)
    def on(self, rect, vw, dx=0, dy=0, ypos=0.42, punch=1000):
        """Frame a phrase. Wide views keep the start of its paragraph line in view."""
        rcx, rcy = center(rect)
        vh = vw * self.H / self.W
        cy = rcy + (0.5 - ypos) * vh
        blk = getattr(rect, 'blk', None)
        if vw <= punch or blk is None:
            return (rcx + (dx if vw <= punch else 0), cy, vw)
        L, R = blk[0], max(blk[2], rect[2])
        m = 0.07 * vw
        if R - L + 2 * m <= vw:
            cx = (L + R) / 2
        else:
            x0 = L - m
            if rect[2] + m > x0 + vw:
                x0 = rect[2] + m - vw
            x0 = min(x0, rect[0] - m)
            cx = x0 + vw / 2
        return (cx, cy, vw)

    def top(self, name, vw, y=0, cx=None):
        (PW, PH), _ = meta(name)
        vh = vw * self.H / self.W
        return (PW / 2 if cx is None else cx, y + vh / 2, vw)

    def shot(self, src, t0, keys, fx=(), **kw):
        """keys: [(t, dur, target, kind)] ; first key's t is ignored (initial state)."""
        ks = [(t, d, tg[0], tg[1], tg[2], kind) for (t, d, tg, kind) in keys]
        s = dict(src=src, t0=t0, cam=Cam(ks) if ks else None, fx=list(fx), **kw)
        self.shots.append(s)
        return s

    def video(self, t0, vt0, crop=None, **kw):
        s = dict(src='video', t0=t0, vt0=vt0, crop=crop, **kw)
        self.shots.append(s)
        return s

    def finish(self, t_end):
        self.shots.sort(key=lambda s: s['t0'])
        for a, b in zip(self.shots, self.shots[1:]):
            a['t1'] = b['t0']
        self.shots[-1]['t1'] = t_end
        for s in self.shots:
            ts = [k[0] for k in s['cam'].keys[1:]] if s.get('cam') else []
            ts += [f['t'] for f in s.get('fx', [])]
            for x in ts:
                if not (s['t0'] - 0.01 <= x < s['t1']):
                    print(f"WARNING {s['src']} [{s['t0']:.2f},{s['t1']:.2f}) has event at {x:.2f}")
        return self.shots


def mk(name, key, t, d=0.7, occ=0, extend=0):
    rs = lines(name, key, occ)
    if extend:
        rs = [list(r) for r in rs]
        rs[-1][2] += extend
    return dict(type='marker', rects=rs, t=t, d=d)


def mkr(rects, t, d=0.7):
    return dict(type='marker', rects=rects, t=t, d=d)


def rg(name, key, t, occ=0, d=0.45, w=8, seed=1):
    return dict(type='ring', rect=box(name, key, occ), t=t, d=d, w=w, seed=seed)
