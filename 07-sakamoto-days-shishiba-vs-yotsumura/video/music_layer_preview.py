"""Original 160 BPM score and metallic effects. No samples or voiceover.

Run this before layer_preview.py video. FFmpeg performs a measured two-pass
loudness normalization; the shared timeline determines every story cue.
"""
from pathlib import Path
import json, math, re, subprocess, tempfile, wave
import numpy as np
import imageio_ffmpeg

HERE=Path(__file__).resolve().parent
TL=json.loads((HERE/'layer_preview_timeline.json').read_text())
SR=48000;N=round(SR*TL['duration']);BEAT=60/TL['bpm']

def event_sample(name):return round(TL['events'][name]*SR)

def make_score():
    rng=np.random.default_rng(10017);bus=np.zeros((N,2),np.float64)
    def put(sig,time,gain=1.,pan=0.):
        start=round(time*SR)
        if start<0:sig=sig[-start:];start=0
        if start>=N:return
        sig=sig[:N-start]*gain
        bus[start:start+len(sig),0]+=sig*math.sqrt((1-pan)/2)
        bus[start:start+len(sig),1]+=sig*math.sqrt((1+pan)/2)
    def drum(kind):
        t=np.arange(round(SR*.35))/SR
        if kind=='kick':
            phase=np.cumsum(44+120*np.exp(-t*40))/SR
            return np.sin(math.tau*phase)*np.exp(-t*16)
        noise=rng.normal(0,1,len(t));noise-=np.convolve(noise,np.ones(13)/13,'same')
        return noise*np.exp(-t*(35 if kind=='snare' else 130))*.4
    for b in TL['sound']['kick_beats']:put(drum('kick'),b*BEAT,.85)
    for b in TL['sound']['snare_beats']:put(drum('snare'),b*BEAT,.6)
    for b in np.arange(0,24,.5):
        if 14<=b<16:continue
        put(drum('hat'),b*BEAT,.2,(-1 if int(b*2)%2 else 1)*.25)
    for b,note in [(0,38),(2,38),(4,41),(6,36),(8,38),(10,38),(12,45),(16,38),(18,36),(20,38),(22,33)]:
        t=np.arange(round(SR*.42))/SR;hz=440*2**((note-69)/12)
        sig=(np.sin(math.tau*hz*t)+.25*np.sin(math.tau*hz*2*t))*np.minimum(1,t/.008)*np.exp(-t*6)
        put(sig,b*BEAT,.34)
    for time in TL['sound']['whooshes']:
        t=np.arange(round(SR*.22))/SR;noise=rng.normal(0,1,len(t));noise=np.convolve(noise,np.ones(5)/5,'same')
        put(noise*np.sin(np.pi*np.arange(len(t))/len(t))**2,time,.42,-.35 if time<3 else .35)
    def metal(time,gain=.35):
        t=np.arange(round(SR*.6))/SR
        sig=sum(np.sin(math.tau*f*t)*np.exp(-t*d) for f,d in [(930,12),(1427,17),(2231,24),(3541,30)])
        put(sig,time,gain)
    metal(TL['events']['opening_hit'],.18);metal(TL['events']['glint'],.12)
    t=np.arange(round(SR*1.25))/SR
    impact=(np.sin(math.tau*(43*t+1.1*(1-np.exp(-t*25))))*np.exp(-t*5)+rng.normal(0,1,len(t))*np.exp(-t*35)*.5)
    put(impact,TL['events']['impact'],1.35);metal(TL['events']['impact'],.3)
    # Kill every tail for the dramatic pause. The final whoosh resumes at impact.
    q0=event_sample('quiet_start');q1=event_sample('impact')
    fade=round(.06*SR);bus[q0-fade:q0]*=np.linspace(1,0,fade)[:,None];bus[q0:q1]=0
    fadeout=round(.55*SR);bus[-fadeout:]*=np.linspace(1,0,fadeout)[:,None]
    bus=np.tanh(bus*.7);bus*=.88/max(.001,np.abs(bus).max())
    return bus.astype(np.float32)

def write_score():
    sound=make_score();ff=imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix='sakamoto-score-') as temp:
        raw=Path(temp)/'raw.wav'
        with wave.open(str(raw),'wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((sound*32767).astype('<i2').tobytes())
        # Tame synthetic transients before normalization, retaining the silent gap.
        compressor=('acompressor=threshold=0.18:ratio=3:attack=0.05:release=80:detection=peak:makeup=1,'
                    'alimiter=limit=0.18:attack=1:release=50:level=false:latency=true,')
        # Leave headroom for resampling and AAC overshoot, measured on the MP4.
        analysis=subprocess.run([ff,'-hide_banner','-i',str(raw),'-af',compressor+'loudnorm=I=-14:TP=-3.5:LRA=9:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
        measure=json.loads(re.findall(r'\{[^{}]+\}',analysis.stderr)[-1])
        filt=compressor+f"loudnorm=I=-14:TP=-3.5:LRA=9:measured_I={measure['input_i']}:measured_TP={measure['input_tp']}:measured_LRA={measure['input_lra']}:measured_thresh={measure['input_thresh']}:offset={measure['target_offset']}:linear=true:print_format=json"
        result=subprocess.run([ff,'-y','-hide_banner','-i',str(raw),'-af',filt,'-ar',str(SR),'-c:a','pcm_s24le',str(HERE/'layer_preview_score.wav')],capture_output=True,text=True,check=True)
        (HERE/'layer_preview_audio_measurements.json').write_text(json.dumps(dict(first_pass=measure,normalized=json.loads(re.findall(r'\{[^{}]+\}',result.stderr)[-1])),indent=2)+'\n')
    print(HERE/'layer_preview_score.wav',flush=True)

if __name__=='__main__':write_score()
