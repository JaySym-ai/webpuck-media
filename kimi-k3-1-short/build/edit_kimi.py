"""Kimi K3.1 Pro open weights Short, 1080x1920. Real pages, static or slow gentle moves, hard cuts.
The only zoom is the blog's Nov 4 line."""
import json
from edl import *

W, H = 1080, 1920
raw = load_words(BASE + '/audio/full_words.json')

# caption display forms (spoken form -> written form); timing stays on the spoken words
MERGE = [
    (['k', 'three', 'point', 'one'], 'K3.1'),
    (['two', 'point', 'eight', 'trillion'], '2.8 trillion'),
    (['two', 'point', 'eight'], '2.8'),
    (['a', 'hundred', 'and', 'four', 'billion'], '104 billion'),
    (['two', 'trillion'], '2 trillion'),
    (['november', 'fourth'], 'November 4'),
    (['october', 'twentythird'], 'October 23'),
]
FIX = {'qimi': 'Kimi'}


def caption_words(ws):
    out, i = [], 0
    while i < len(ws):
        hit = None
        for pat, rep in MERGE:
            seg = ws[i:i + len(pat)]
            if len(seg) == len(pat) and [norm(w['text']) for w in seg] == pat:
                tail = ''.join(ch for ch in seg[-1]['text'] if not ch.isalnum() and ch not in '"\'')[-1:]
                hit = dict(text=rep + tail, type='word', start=seg[0]['start'], end=seg[-1]['end'])
                i += len(pat)
                break
        if not hit:
            w = dict(ws[i]); i += 1
            t = w['text'].replace('"', '')
            core = norm(t)
            if core in FIX:
                t = FIX[core] + ''.join(ch for ch in t if not ch.isalnum())
            w['text'] = t
            hit = w
        out.append(hit)
    return out


words = raw
B = Builder(W, H, words)
def T(ph, n=0, after=0.0):
    try:
        return find(words, ph, n, after)[0]
    except KeyError:
        return find(words, ph.replace('Kimi', 'Qimi'), n, after)[0]
on = lambda r, vw, ypos=0.40: B.on(r, vw, ypos=ypos, punch=0)


def drift(src, t, r, vw, ypos=0.40, fx=(), k=0.95, **kw):
    """Static framing with a slow gentle push (k < 1) or pull (k > 1) over the shot."""
    a = on(r, vw, ypos)
    b = on(r, vw * k, ypos)
    return B.shot(src, t, [(t, 0, a, 'io'), (t + 0.05, 6.0, b, 'sine')], fx=list(fx), **kw)


# ---- punchy open: cover as frame 1, then Moonshot's own charts
B.shot('cover', 0.0, [(0.0, 0, (540, 960, 1080), 'io'), (0.05, 2.0, (540, 960, 1040), 'sine')])
t = T('just beat')
SWE_K = [1490, 186, 2372, 222]     # Kimi K3.1 Pro row, SWE Marathon chart (51.7 vs Opus 5.5 46.3)
KCB_K = [1490, 634, 2372, 670]     # Kimi K3.1 Pro row, Kimi Code Bench 3.0 Long-horizon (61.2 vs Opus 5.5 58.5)
B.shot('blog_charts', t, [(t, 0, (1960, 930, 1060), 'io'), (t + 0.05, 3.0, (1960, 900, 1010), 'sine')],
       fx=[dict(type='ring', rect=SWE_K, t=T('beat'), d=0.45, w=7, seed=2),
           dict(type='ring', rect=KCB_K, t=T('long coding'), d=0.45, w=7, seed=5)])
t = T('And any day')
drift('blog', t, box('blog', 'most capable 3T-class open-weight model to date'), 1150, ypos=0.40,
      fx=[mk('blog', 'most capable 3T-class open-weight model to date', T('anyone'), 0.8)])

# ---- deadline hook
t = T('In China,')
r_cl = union(box('clock', 'Current local time in Beijing'), box('clock', 'Wednesday, November 4, 2026'))
drift('clock', t, r_cl, 1150, ypos=0.36, fx=[mk('clock', 'Wednesday, November 4, 2026', T('November fourth,'), 0.7)])
t = T('And Kimi K')
r_k3 = box('hf', 'moonshotai/Kimi-K3', occ=1)
r_models = union(box('hf', 'Models', occ=1), r_k3)
drift('hf', t, r_models, 1200, ypos=0.30, fx=[rg('hf', 'Models', T('Still not'), occ=1, w=7),
                                            mkr([[r_k3[0], r_k3[1], r_k3[2], r_k3[3]]], T('Hugging Face.'), 0.5)])
t = T('But someone')
r_vt = box('pr_vllm', '[Doc] Add Kimi-K3.1 A5 PD deployment guide')
drift('pr_vllm', t, r_vt, 1250, ypos=0.34, fx=[mk('pr_vllm', '[Doc] Add Kimi-K3.1 A5 PD deployment guide', T('install guide.'), 0.6)])

# ---- context
t = T('October twenty-third,')
r_bt = union(box('blog', 'Introducing Kimi K3.1 Pro'), box('blog', 'available today on Kimi.ai, Kimi Work, Kimi Code, and the Kimi API'))
drift('blog', t, r_bt, 1250, ypos=0.36, fx=[mk('blog', 'available today on Kimi.ai, Kimi Work, Kimi Code, and the Kimi API', T('in the API'), 1.2)])
t = T('Two point eight trillion')
r_par = box('officechai', '2.8 trillion total parameters and 104 billion active parameters')
drift('officechai', t, r_par, 1150, ypos=0.38, fx=[mkr(lines('officechai', '2.8 trillion total parameters and 104 billion active parameters'), t + 0.1, 3.0)])
t = T('a million tokens')
drift('blog', t, box('blog', '1-million-token context window'), 1150, ypos=0.38,
      fx=[mk('blog', '1-million-token context window', t + 0.1, 0.8)])
t = T('Fourth on the')
r_hl = union(box('officechai', 'Kimi K3.1 Pro Places 4th On Artificial Analysis Intelligence Index'), box('officechai', 'OCTOBER 23, 2026'))
drift('officechai', t, r_hl, 1300, ypos=0.36, fx=[mk('officechai', 'Kimi K3.1 Pro Places 4th On Artificial Analysis Intelligence Index', t + 0.1, 1.0)])

# ---- promise: the one zoom
t = T('And on their blog')
r_nov = box('blog', 'The full model weights will be released by Nov 4.')
B.shot('blog', t, [(t, 0, on(r_nov, 1250, 0.42), 'io'), (T('Full model'), 1.3, on(r_nov, 820, 0.42), 'io')],
       fx=[mk('blog', 'The full model weights will be released by Nov 4.', T('Full model') + 0.3, 2.2)])

# ---- proof
t = T('This morning,')
r_dr = union(r_vt, box('pr_vllm', 'opened this pull request on'))
drift('pr_vllm', t, r_dr, 1250, ypos=0.36, fx=[rg('pr_vllm', 'Draft', T('draft pull'), w=7), mk('pr_vllm', 'opened this pull request on', T('vLLM Ascend,'), 0.7)])
t = T('a full eight-node')
drift('pr_vllm', t, box('pr_vllm', 'eight-node 950DT (A5) PD deployment'), 1200, ypos=0.40,
      fx=[mk('pr_vllm', 'eight-node 950DT (A5) PD deployment', t + 0.2, 0.9)])
t = T('Checkpoint paths?')
drift('pr_vllm', t, box('pr_vllm', 'Environment and checkpoint paths and IPs are placeholders.'), 1200, ypos=0.40,
      fx=[mk('pr_vllm', 'Environment and checkpoint paths and IPs are placeholders.', t + 0.1, 1.3)])
t = T('And yesterday,')
r_pt = union(box('pr_primus', 'feat(kimi_k3): Kimi K3.1 Pro preset'), box('pr_primus', 'opened this pull request on'))
drift('pr_primus', t, r_pt, 1250, ypos=0.36, fx=[mk('pr_primus', 'feat(kimi_k3): Kimi K3.1 Pro preset', T('Pro preset'), 0.8), rg('pr_primus', 'Draft', T('preset') + 0.5, w=7)])
t = T('literally waiting')
r_cfg = union(box('pr_primus', 'weights and config.json announced for 2026-11-04'), box('pr_primus', 'until the K3.1 Pro config.json is public'))
drift('pr_primus', t, r_cfg, 1300, ypos=0.40, fx=[mk('pr_primus', 'weights and config.json announced for 2026-11-04', t + 0.1, 0.8),
                                                  mk('pr_primus', 'until the K3.1 Pro config.json is public', T('config file'), 0.8)])

# ---- wrinkle
t = T('One wrinkle.')
r_sh = union(box('santage', 'China Targets 2-Trillion-Parameter AI Models in Proposed Export Controls'), box('santage', 'October 17, 2026'))
drift('santage', t, r_sh, 1350, ypos=0.36, fx=[mk('santage', 'China Targets 2-Trillion-Parameter AI Models in Proposed Export Controls', T('two trillion'), 1.0)])
t = T('This one is')
drift('officechai', t, r_par, 1150, ypos=0.38, fx=[mkr(lines('officechai', '2.8 trillion total parameters and 104 billion active parameters')[:1], t + 0.2, 0.6)])
t = T('but the draft')
r_auto = box('santage', 'future open releases fall under automatic licensing')
drift('santage', t, r_auto, 1250, ypos=0.40, fx=[mk('santage', 'future open releases fall under automatic licensing', T('automatic'), 0.9)])

# ---- payoff
t = T('The guides are')
drift('pr_vllm', t, r_vt, 1250, ypos=0.36)
t = T('The presets are')
drift('pr_primus', t, r_pt, 1250, ypos=0.36)
t = T('Now we just')
drift('hf', t, r_models, 1200, ypos=0.30, fx=[mkr([[r_k3[0], r_k3[1], r_k3[2], r_k3[3]]], t + 0.4, 0.5)])

END = words[-1]['end'] + 0.7
SHOTS = B.finish(END)


def question_card(fr, t):
    t0 = Q0
    k = min(1, (t - t0) / 0.18)
    ov = Image.new('RGBA', fr.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(FONT_XB, 72)
    x0, x1, yc, h = 70, 900, 470 + (1 - k) * 40, 260
    d.rounded_rectangle([x0 + 8, yc - h / 2 + 14, x1 + 8, yc + h / 2 + 14], radius=36, fill=(0, 0, 0, int(70 * k)))
    d.rounded_rectangle([x0, yc - h / 2, x1, yc + h / 2], radius=36, fill=(18, 18, 20, int(245 * k)))
    d.rounded_rectangle([x0, yc - h / 2, x0 + 16, yc + h / 2], radius=8, fill=(255, 59, 48, int(255 * k)))
    for i, s in enumerate(['Do they make it', 'on time?']):
        d.text(((x0 + x1) / 2 + 8, yc - 44 + i * 88), s, font=f, anchor='mm',
               fill=(255, 255, 255, int(255 * k)) if i == 0 else (255, 214, 0, int(255 * k)))
    return Image.alpha_composite(fr.convert('RGBA'), ov).convert('RGB')


Q0 = T('Do they make') - 0.1
LABELS = [dict(t0=T('just beat'), t1=T('And any day'), fn=lambda fr, t: draw_label(fr, "Moonshot's own benchmarks", 465, 92, 30, 'mm')),
          dict(t0=Q0, t1=T('October twenty-third,'), fn=question_card)]
CAPTIONS = dict(chunks=caption_chunks(caption_words(raw), max_words=4, max_chars=18), cx=470, cy=1475, size=74, maxw=760)
EDL = dict(shots=SHOTS, labels=LABELS, captions=CAPTIONS)
