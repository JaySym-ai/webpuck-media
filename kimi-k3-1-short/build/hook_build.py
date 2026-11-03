import json, wave, numpy as np, subprocess
TEMPO, KEEP_MID, KEEP_END, GAP = 1.10, 0.09, 0.18, 0.20
hw = [{"text":t,"start":s,"end":e} for t,s,e in json.load(open('hook_words_raw.json'))]
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i','hook1.mp3','-ac','1','-ar','44100','hook1.wav'],check=True)
w = wave.open('hook1.wav'); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
sil = [(4.78927,5.23678),(6.29692,6.59887)]
cuts = []
for s,e in sil:
    prev = [x for x in hw if x['end'] <= e + 0.05]
    keep = KEEP_END if prev and prev[-1]['text'][-1] in '.?!' else KEEP_MID
    m=(s+e)/2; cuts.append((m-(e-s-keep)/2, m+(e-s-keep)/2))
cuts.append((7.84+0.10, len(a)/sr))
keep, t = [], 0.0
for s,e in cuts: keep.append((t,s)); t=e
xf=int(0.008*sr); out=np.zeros(0,np.float32)
for s,e in keep:
    seg=a[int(s*sr):int(e*sr)].copy()
    if len(out) and len(seg)>xf:
        r=np.linspace(0,1,xf); out[-xf:]=out[-xf:]*(1-r)+seg[:xf]*r; seg=seg[xf:]
    out=np.concatenate([out,seg])
def remap(x):
    acc=0.0
    for s,e in keep:
        if x<=e: return (acc+max(0,x-s))/TEMPO
        acc+=e-s
    return acc/TEMPO
wo=wave.open('hook_pre.wav','wb'); wo.setnchannels(1); wo.setsampwidth(2); wo.setframerate(sr); wo.writeframes(np.clip(out,-32768,32767).astype(np.int16).tobytes()); wo.close()
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i','hook_pre.wav','-af',f'atempo={TEMPO},volume=-1.4dB','-ar','44100','hook_t.wav'],check=True)
w2=wave.open('hook_t.wav'); hl=w2.getnframes()/w2.getframerate()
off = hl + GAP
main=[x for x in json.load(open('tight_words_scribe.json'))['words'] if x['type']=='word']
words=[dict(text=x['text'],type='word',start=round(remap(x['start']),3),end=round(min(remap(x['end']),hl),3)) for x in hw]
words+=[dict(x,start=round(x['start']+off,3),end=round(x['end']+off,3)) for x in main]
json.dump({'words':words, 'hook_len':hl, 'offset':off}, open('full_words.json','w'))
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i','hook_t.wav','-f','lavfi','-t',str(GAP),'-i','anullsrc=r=44100:cl=mono','-i','tight.wav',
  '-filter_complex','[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]','-map','[a]','full_pre.wav'],check=True)
print('hook', round(hl,2), 'offset', round(off,2), 'last word', words[-1])
