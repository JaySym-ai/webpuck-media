import json, wave, numpy as np, sys
TEMPO = float(sys.argv[1]) if len(sys.argv) > 1 else 1.10
KEEP_MID, KEEP_END = 0.09, 0.18
w = wave.open('take1.wav'); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
words = [x for x in json.load(open('take1_words.json'))['words'] if x['type'] == 'word']
sil = [tuple(map(float, l.split())) for l in open('sil.txt')]
dur = len(a) / sr
cuts = []  # (start, end) of removed audio
for s, e in sil:
    if s < 0.05 or e > dur - 0.05:   # keep head/tail as is (trim tail later)
        continue
    prev = [x for x in words if x['end'] <= e + 0.05]
    end_sent = prev and prev[-1]['text'][-1] in '.?!'
    keep = KEEP_END if end_sent else KEEP_MID
    if e - s > keep:
        m = (s + e) / 2
        cuts.append((m - (e - s - keep) / 2, m + (e - s - keep) / 2))
# tail: keep 0.5 s after last word
cuts.append((min(dur, words[-1]['end'] + 0.5), dur))
keepsegs, t = [], 0.0
for s, e in cuts:
    keepsegs.append((t, s)); t = e
keepsegs.append((t, dur))
keepsegs = [(s, e) for s, e in keepsegs if e - s > 0.001]
xf = int(0.008 * sr)
out = np.zeros(0, np.float32)
for s, e in keepsegs:
    seg = a[int(s * sr):int(e * sr)].copy()
    if len(out) and len(seg) > xf:
        ramp = np.linspace(0, 1, xf)
        out[-xf:] = out[-xf:] * (1 - ramp) + seg[:xf] * ramp
        seg = seg[xf:]
    out = np.concatenate([out, seg])
def remap(t):
    acc = 0.0
    for s, e in keepsegs:
        if t <= e:
            return (acc + max(0, t - s)) / TEMPO
        acc += e - s
    return acc / TEMPO
nw = [dict(x, start=round(remap(x['start']), 3), end=round(remap(x['end']), 3)) for x in words]
json.dump({'words': nw}, open('tight_words.json', 'w'))
wo = wave.open('tight_pre.wav', 'wb'); wo.setnchannels(1); wo.setsampwidth(2); wo.setframerate(sr)
wo.writeframes(np.clip(out, -32768, 32767).astype(np.int16).tobytes()); wo.close()
print('cut silences', len(cuts), 'pre-tempo', round(len(out) / sr, 2), 'final ~', round(len(out) / sr / TEMPO, 2))
