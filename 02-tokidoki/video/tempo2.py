import subprocess, numpy as np, imageio_ffmpeg
SR=22050; HOP=256; NF=2048
raw=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i','../tokidoki-bg-song.mp3','-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout
y=np.frombuffer(raw,np.float32); nfr=1+(len(y)-NF)//HOP
fr=np.lib.stride_tricks.as_strided(y,(nfr,NF),(4*HOP,4))
S=np.abs(np.fft.rfft(fr*np.hanning(NF),axis=1)); L=np.log1p(100*S)
fl=np.concatenate([[0],np.maximum(0,np.diff(L,axis=0)).sum(1)]); fps=SR/HOP
k=np.hanning(int(fps)); fl=np.maximum(0,fl-np.convolve(fl,k/k.sum(),'same'))
def comb(seg):
    res=[]
    for P in np.arange(0.30,1.2,0.001):
        l=P*fps; best=0
        for ph in np.linspace(0,l,40,endpoint=False):
            idx=np.round(np.arange(ph,len(seg)-1,l)).astype(int); best=max(best,seg[idx].mean())
        res.append((best/seg.mean(),P))
    return sorted(res,reverse=True)
import sys
if 0: r=comb(fl[int(50*fps):int(150*fps)])
r=[];seen=[]
for s,P in r:
    if all(abs(P-q)>0.01 for q in seen): seen.append(P); print(f'P={P:.3f} bpm={60/P:.2f} score={s:.3f}')
    if len(seen)>=8: break
for a in []:
    rr=comb(fl[int(a*fps):int((a+25)*fps)])[0]; print('win',a,'best P',round(rr[1],3),'bpm',round(60/rr[1],1))
print('---- local phase drift, P fixed, 10s windows')
for P in (0.5876,):
    l=P*fps
    for a in range(0,214,8):
        seg=fl[int(a*fps):int((a+8)*fps)]
        if len(seg)<l*3: continue
        best=max(((seg[np.round(np.arange(ph,len(seg)-1,l)).astype(int)].mean(),ph) for ph in np.linspace(0,l,60,endpoint=False)))
        t0=a+best[1]/fps; print(a, 'first beat', round(t0,3), 'phase mod P', round(t0%P,3), 'strength', round(best[0]/seg.mean(),2))
