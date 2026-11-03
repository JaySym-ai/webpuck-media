import sys, os, subprocess, importlib, math
from multiprocessing import Process
import engine

def load(which):
    m = importlib.import_module('edit_' + which)
    return m

def worker(which, f0, f1, out):
    m = load(which)
    engine.render_range(m.EDL, f0, f1, m.W, m.H, out)

if __name__ == '__main__':
    which, mode = sys.argv[1], sys.argv[2]
    m = load(which)
    os.makedirs('../out', exist_ok=True)
    if mode == 'preview':
        for ts in sys.argv[3:]:
            fr = engine.render_frame(m.EDL, float(ts), m.W, m.H)
            fr.save(f'../out/prev_{which}_{float(ts):07.2f}.png')
        print('ok')
    elif mode == 'shots':
        for s in m.EDL['shots']:
            print(f"{s['t0']:7.2f} {s['t1']:7.2f} {s['src']}")
    elif mode == 'full':
        nf = int(math.ceil(m.EDL['shots'][-1]['t1'] * 30))
        if len(sys.argv) > 3:  # optional frame range for partial render
            nf = min(nf, int(float(sys.argv[3]) * 30))
        N = int(os.environ.get('WORKERS', 4))
        step = math.ceil(nf / N)
        ps, parts = [], []
        for i in range(N):
            out = f'../out/{which}_part{i}.mp4'
            parts.append(out)
            p = Process(target=worker, args=(which, i * step, min(nf, (i + 1) * step), out)); p.start(); ps.append(p)
        for p in ps: p.join()
        with open(f'../out/{which}_parts.txt', 'w') as fh:
            for p in parts: fh.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'../out/{which}_parts.txt', '-c', 'copy', f'../out/{which}_video.mp4'], check=True)
        print('video done', nf, 'frames')
