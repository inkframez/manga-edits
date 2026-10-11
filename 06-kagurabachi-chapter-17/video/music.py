"""Original 160 BPM industrial breakbeat score and synchronous sword sound design.
No third-party recordings, voice clones, or commercial music. Generates stereo WAV.
"""
from pathlib import Path
import wave
import numpy as np
from timeline import BEAT, DURATION, SLASH_BEATS, EVENTS

SR = 48000
N = round(SR * DURATION)
RNG = np.random.default_rng(17018)
music = np.zeros((N, 2), dtype=np.float64)
fx = np.zeros_like(music)
HERE = Path(__file__).resolve().parent

def time(d): return np.arange(round(d*SR))/SR
def hz(m): return 440*2**((m-69)/12)
def place(bus, s, at, gain=1, pan=0):
    i = round(at*SR)
    if i < 0: s, i = s[-i:], 0
    n = min(len(s), N-i)
    if n <= 0: return
    bus[i:i+n,0] += s[:n]*gain*np.sqrt((1-pan)/2)
    bus[i:i+n,1] += s[:n]*gain*np.sqrt((1+pan)/2)

def filtered_noise(d, low, high):
    n = round(d*SR)
    z = RNG.normal(size=n)
    f = np.fft.rfftfreq(n, 1/SR)
    h = (1-np.exp(-(f/max(low,1))**4))*np.exp(-(f/high)**4)
    s = np.fft.irfft(np.fft.rfft(z)*h,n)
    return s / max(0.05, np.std(s)) * .3

def kick():
    t=time(.5); f=48+140*np.exp(-t*48)
    s=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*11)
    return np.tanh(s*1.8)*.8 + filtered_noise(.5,2000,9500)*np.exp(-t*190)*.17
def snare():
    t=time(.29)
    return (filtered_noise(.29,900,11000)*np.exp(-t*22)*.95 +
            (np.sin(2*np.pi*187*t)+.4*np.sin(2*np.pi*312*t))*np.exp(-t*38)*.4)
def hat(opened=False):
    d=.3 if opened else .085; t=time(d)
    return filtered_noise(d,6500,17000)*np.exp(-t*(17 if opened else 65))*.38
def taiko(f=84):
    t=time(.7); ph=2*np.pi*(f*t+4*(1-np.exp(-t*24)))
    return (np.sin(ph)+.36*np.sin(ph*1.58))*np.exp(-t*7)+filtered_noise(.7,150,1600)*np.exp(-t*36)*.3
def bass(m,d):
    t=time(d); f=hz(m); ph=2*np.pi*f*t
    # Harmonic bass, slow detune, and an envelope that leaves room for the kick.
    sub=np.sin(ph)
    reese=sum(np.sin(ph*k+.016*k*np.sin(2*np.pi*1.4*t))/k for k in range(1,8))
    env=np.minimum(t/.007,1)*np.minimum((d-t)/.04,1)*(.55+.45*np.sin(np.pi*np.clip(t/.12,0,1))**2)
    return (sub*.6+np.tanh(reese*1.7)*.45)*env
def bell(m,d=.7):
    t=time(d); p=2*np.pi*hz(m)*t
    return (np.sin(p+1.1*np.sin(p*2)*np.exp(-t*9))+.2*np.sin(p*2.76))*np.exp(-t*7)*np.minimum(t/.002,1)
def metal(f=1200,d=.65):
    t=time(d)
    s=sum(np.sin(2*np.pi*f*r*t+RNG.uniform(-1,1))*np.exp(-t*(5+3*k))*.65/(k+1)
          for k,r in enumerate([1,1.483,2.174,2.91,4.03]))
    return s+filtered_noise(d,1800,14000)*np.exp(-t*95)*.8
def whoosh(d=.23):
    t=time(d); env=np.sin(np.pi*t/d)**2
    s=filtered_noise(d,650,9500)*env
    return s+np.sin(2*np.pi*(1800*t-1400*t*t/d/2))*env*.09
def electric(d=.45):
    t=time(d)
    pulse=(np.sin(2*np.pi*53*t+.8*np.sin(2*np.pi*11*t))>.82).astype(float)
    return filtered_noise(d,2100,12500)*pulse*np.exp(-t*4)+np.sin(2*np.pi*93*t)*np.exp(-t*9)*.15

K,S,H,OH=kick(),snare(),hat(),hat(True)
# Low, spacious opening. Four clock ticks precede the first musical drop.
tt=time(DURATION)
drone=(np.sin(2*np.pi*36.708*tt)+.3*np.sin(2*np.pi*55*tt))
drone*=np.interp(tt,[0,.15,2.8,3,27,29.25,30,34.5,36],[0,.09,.14,.035,.08,0,.13,.08,0])
place(music,drone,0)
for b in range(8):
    place(music,taiko(73.4),b*BEAT,.18 if b%2==0 else .07, -.25 if b%2 else .25)
    if b%2==0: place(music,bell(74,.65),b*BEAT,.11,(-1)**b*.25)

# Main drum arrangement. 8-bar phrase, with a half-time passage under Sojo's decision.
for b in range(8,78):
    at=b*BEAT
    section=.72 if 32<=b<40 else (1.05 if b>=52 else .9)
    if b%4 in [0,2]: place(music,K,at,.62*section)
    if b%4 in [1,3]: place(music,S,at,.43*section)
    if b%8==6: place(music,K,at+BEAT*.75,.34)
    place(music,H,at,.54*section,-.22)
    place(music,H,at+BEAT*.5,.37*section,.26)
    if b>=52 and b%2==0:
        place(music,H,at+BEAT*.75,.2,.4)
    if b%8==7:
        place(music,OH,at+BEAT*.5,.5,.38)
        for k in range(3): place(music,S,at+BEAT*(.5+k/6),.12+k*.035, -.2+k*.2)
    if b%8==0: place(music,taiko(73.4),at,.32)

# D-minor pulse; deliberate gaps make the edits and metal transients legible.
progression=[26,26,29,24,26,26,34,33]
for b in range(8,78,2):
    note=progression[((b-8)//8)%len(progression)]
    place(music,bass(note,BEAT*1.8),b*BEAT,.34 if b<52 else .4)
    if b%4==2: place(music,bass(note+12,BEAT*.4),(b+1.5)*BEAT,.16,.08)
motif=[74,77,81,72,74,77,82,81]
for b in range(8,76):
    if 32<=b<40 or b%4==3: continue
    place(music,bell(motif[(b//2)%8],.65),b*BEAT,.085 if b<52 else .12, -.35 if b%2 else .35)
    if b>=52: place(music,bell(motif[(b//2)%8]+12,.4),(b+.5)*BEAT,.045,.45)

# Air lifts into the two cloak escalations; no constant broadband wall of noise.
for end,d in [(3,.8),(16.5,1.1),(19.5,1.0),(24,.6)]:
    t=time(d); riser=filtered_noise(d,1400,9500)*(t/d)**2
    place(music,riser,end-d,.19,.1)
    place(fx,electric(.55),end,.34,.25)

# Each drawn cut has a pre-swish and a short, pitched metal contact.
for j,b in enumerate(SLASH_BEATS):
    at=b*BEAT
    place(fx,whoosh(),at-.17,.32,(-1)**j*.6)
    place(fx,metal(900+(j%4)*240,.4),at,.17 if b!=24 else .24,(-1)**(j+1)*.35)
    if b in [12,40,44,52,60,64]: place(fx,electric(),at+.025,.18,.4)
for at in [0,.75,1.5,2.25,9,12,15,16.5,19.5,24,27]:
    t=time(.065); click=np.sin(2*np.pi*2300*t)*np.exp(-t*105)
    place(fx,click,at,.2)

# Nishiki release: the rhythm rapidly drains, then 0.75 s of almost empty air.
duck=np.interp(tt,[0,26.95,27,28.5,29.15,29.25,30,30.02,33.2,34.5,35.8,36],
                 [1,1,.4,.25,.05,0,0,1,1,.7,.7,0])
music*=duck[:,None]
fx[int(29.25*SR):int(30*SR)] = 0
place(fx,whoosh(.5)[::-1],27,.25,-.4)
place(fx,metal(2400,.5)*.22,27,.35,.25)
# The final cut has a broad low transient, blade ring, and receding debris.
t=time(2.8)
boom=np.sin(2*np.pi*(37*t+3*(1-np.exp(-t*18))))*np.exp(-t*2.8)
crash=filtered_noise(2.8,150,12500)*np.exp(-t*7)
place(fx,boom+crash*.7,30,.92)
place(fx,metal(820,2.0),30,.47,-.1)
place(fx,whoosh(.18),29.99,.56,-.45)
for k in range(7): place(fx,metal(1900+k*360,.5),30.12+k*.09,.075,(-1)**k*.7)
place(music,bass(26,2.4),30,.45)
for b in [80,82,84,86]: place(music,taiko(73.4),b*BEAT,.26)
place(fx,metal(1750,1.4),33,.25,.38)
place(fx,metal(3100,.7),33.11,.12,-.5)
for m in [62,65,69,74]: place(music,bell(m,2),34.5,.12,(m-68)/16)
place(music,taiko(73.4),34.5,.2)

# Short stereo reflections, then peak-safe premaster. Export normalizes loudness.
for delay,gain in [(.047,.12),(.113,.09),(.191,.06)]:
    n=round(delay*SR)
    wet=music[:-n,::-1].copy()*gain
    music[n:]+=wet
mix=music+fx
mix[int(29.25*SR):int(30*SR)]*=.025
mix*=np.minimum((DURATION-tt)/.24,1).clip(0,1)[:,None]
mix=np.tanh(mix*1.15)
mix*=.91/max(.91,np.max(np.abs(mix)))
with wave.open(str(HERE/'score.wav'),'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix*32767).astype('<i2').tobytes())
print(f'Original score: {DURATION:.1f}s / {SR} Hz / stereo / peak {20*np.log10(np.max(np.abs(mix))):.2f} dBFS')
