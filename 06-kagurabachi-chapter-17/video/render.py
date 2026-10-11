"""Kagurabachi / Twelve Seconds. Deterministic 36s manga motion edit.

python music.py
python render.py stills --width 540
python render.py video --width 1080 --workers 3

Original page art is kept intact in panels/. All motion is procedural compositing:
camera ramps, sliding panels, ink wipes, vector electricity, typography, and clock.
"""
import argparse
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor
import os, math, subprocess, json, time
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from timeline import SHOTS, CLOCK, BEAT, DURATION, FPS, EVENTS

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
W,H,SCALE=1080,1920,1.0
INK=(12,14,18); PAPER=(241,238,231); RED=(244,52,65); CYAN=(77,211,239)
FONT=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
cv2.setNumThreads(1)

def configure(width):
    global W,H,SCALE
    W=width; H=round(width*16/9); SCALE=width/1080
    cv2.setNumThreads(1)
def d(v): return round(v*SCALE)
def clamp(x): return max(0,min(1,x))
def ease(x): x=clamp(x); return x*x*(3-2*x)
def out(x): return 1-(1-clamp(x))**3
def mix(a,b,u): return a+(b-a)*u

@lru_cache(maxsize=20)
def page(n):
    im=cv2.imread(str(ROOT/'panels'/f'{n:02}.png'))
    if im is None: raise FileNotFoundError(n)
    return cv2.cvtColor(im,cv2.COLOR_BGR2RGB)

@lru_cache(maxsize=80)
def crop(n,r):
    x,y,w,h=map(round,r)
    im=page(n)[y:y+h,x:x+w]
    if im.size==0: raise ValueError((n,r))
    return im.copy()

def camera(n,r,w,h,u=0,zoom=(1.0,1.055),pan=(0,0),contain=False):
    im=crop(n,tuple(r)); ih,iw=im.shape[:2]
    z=mix(*zoom,ease(u))
    sc=(min(w/iw,h/ih) if contain else max(w/iw,h/ih))*z
    tx=w/2-iw*sc/2 + pan[0]*SCALE*(u-.5)
    ty=h/2-ih*sc/2 + pan[1]*SCALE*(u-.5)
    return cv2.warpAffine(im,np.float32([[sc,0,tx],[0,sc,ty]]),(w,h),
                          flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)

def paste(dst,src,x,y,alpha=None):
    x,y=round(x),round(y); h,w=src.shape[:2]
    x0,y0=max(0,x),max(0,y); x1,y1=min(W,x+w),min(H,y+h)
    if x1<=x0 or y1<=y0:return
    a=src[y0-y:y1-y,x0-x:x1-x]
    if alpha is None:dst[y0:y1,x0:x1]=a;return
    m=alpha[y0-y:y1-y,x0-x:x1-x,None].astype(np.float32)/255
    dst[y0:y1,x0:x1]=(a*m+dst[y0:y1,x0:x1]*(1-m)).astype(np.uint8)

def panel(dst,n,r,box,u,angle=0,zoom=(1,1.055),pan=(0,0),accent=RED,enter=0):
    x,y,w,h=box; bw,bh=d(w),d(h)
    im=camera(n,r,bw,bh,u,zoom,pan)
    # A fine paper edge and one colored registration edge stay outside the drawing.
    cv2.rectangle(im,(0,0),(bw-1,bh-1),PAPER,max(1,d(4)))
    cv2.line(im,(0,bh-1),(bw-1,bh-1),accent,max(1,d(5)))
    a=math.radians(angle); nw=round(abs(bw*math.cos(a))+abs(bh*math.sin(a)))+d(8)
    nh=round(abs(bh*math.cos(a))+abs(bw*math.sin(a)))+d(8)
    mat=cv2.getRotationMatrix2D((bw/2,bh/2),angle,1)
    mat[:,2]+=[(nw-bw)/2,(nh-bh)/2]
    warped=cv2.warpAffine(im,mat,(nw,nh),flags=cv2.INTER_LINEAR)
    mask=cv2.warpAffine(np.full((bh,bw),255,np.uint8),mat,(nw,nh))
    px=d(x+w/2)-nw/2+enter*SCALE; py=d(y+h/2)-nh/2
    paste(dst,np.zeros_like(warped),px+d(13),py+d(20),mask)
    paste(dst,warped,px,py,mask)

@lru_cache(maxsize=300)
def type_sprite(text,size,font='impact.ttf',col=PAPER,outline=False):
    f=ImageFont.truetype(str(FONT/font),max(8,d(size)))
    bb=f.getbbox(text,stroke_width=0); pad=d(12)
    im=Image.new('RGBA',(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2))
    dr=ImageDraw.Draw(im)
    dr.text((pad-bb[0],pad-bb[1]),text,font=f,fill=(*col,0 if outline else 255),
            stroke_width=max(1,d(2)) if outline else 0,stroke_fill=(*col,255))
    ar=np.array(im)
    return ar[:,:,:3].copy(),ar[:,:,3].copy()

def txt(dst,s,x,y,size=65,color=PAPER,font='impact.ttf',align='left',alpha=1,outline=False):
    im,mask=type_sprite(s,size,font,tuple(color),outline)
    xx=d(x)- (im.shape[1]/2 if align=='center' else im.shape[1] if align=='right' else 0)
    yy=d(y)-im.shape[0]/2
    paste(dst,im,xx,yy,(mask*clamp(alpha)).astype(np.uint8) if alpha<1 else mask)

def line(dst,a,b,col=PAPER,th=2): cv2.line(dst,(d(a[0]),d(a[1])),(d(b[0]),d(b[1])),col,max(1,d(th)),cv2.LINE_AA)
def box(dst,r,col):
    x,y,w,h=r; cv2.rectangle(dst,(d(x),d(y)),(d(x+w),d(y+h)),col,-1)

SEGMENTS={'0':'abcedf','1':'bc','2':'abged','3':'abgcd','4':'fgbc','5':'afgcd',
          '6':'afgecd','7':'abc','8':'abcdefg','9':'abfgcd'}
def clock_digit(dst,ch,x,y,size,col):
    w=size*.55; h=size; k=max(2,size*.085)
    seg={'a':(x+k,y,x+w-k,y),'g':(x+k,y+h/2,x+w-k,y+h/2),
         'd':(x+k,y+h,x+w-k,y+h),'f':(x,y+k,x,y+h/2-k),
         'b':(x+w,y+k,x+w,y+h/2-k),'e':(x,y+h/2+k,x,y+h-k),
         'c':(x+w,y+h/2+k,x+w,y+h-k)}
    if ch==':':
        for q in [.32,.7]:cv2.circle(dst,(d(x+w/2),d(y+h*q)),d(k*.7),col,-1)
    else:
        for key in SEGMENTS[ch]:
            a,b,c,e=seg[key];line(dst,(a,b),(c,e),col,k)

def clock(dst,remaining,x=80,y=112,size=93,col=PAPER):
    q=max(0,round(remaining*100)); value=f'{q//100:02}:{q%100:02}'
    for i,ch in enumerate(value): clock_digit(dst,ch,x+i*size*.76,y,size,col)

@lru_cache(maxsize=20)
def background(n,r):
    ar=camera(n,r,max(1,W//3),max(1,H//3),0,zoom=(1.15,1.15))
    ar=cv2.GaussianBlur(ar,(0,0),2.8)
    ar=cv2.resize(ar,(W,H),interpolation=cv2.INTER_LINEAR)
    return (ar.astype(np.float32)*.125+np.array(INK)*.75).astype(np.uint8)

def streaks(dst,t,intensity=1,col=CYAN):
    # Edge-only speed strokes leave the center of the manga legible.
    for i in range(24):
        yy=(i*127+t*(400+70*(i%4)))%1520+240
        xx=0 if i%2==0 else 1080
        length=(35+(i*29)%160)*intensity
        line(dst,(xx,yy),(xx+length*(1 if i%2==0 else -1),yy-length*.5),col,1+(i%3==0))

def electricity(dst,t,power=1):
    for side in [0,1]:
        pts=[]
        for j in range(16):
            x=(44 if side==0 else 1036)+math.sin(j*7.8+int(t*18)*3.2)*22*power
            pts.append((d(x),d(300+j*88)))
        cv2.polylines(dst,[np.int32(pts)],False,(30,74,89),max(1,d(8)),cv2.LINE_AA)
        cv2.polylines(dst,[np.int32(pts)],False,CYAN,max(1,d(2)),cv2.LINE_AA)

def hud(dst,t,remaining,phase):
    # Opaque top/bottom rails maintain mobile contrast and platform-safe labels.
    box(dst,(0,0,1080,248),INK)
    txt(dst,'ENTEN  /  CLOUD GOUGER',68,64,25,font='consola.ttf',color=(151,154,157))
    clock(dst,remaining)
    txt(dst,'REMAINING',1000,143,23,font='consola.ttf',align='right',color=(151,154,157))
    txt(dst,'SECONDS',1000,181,27,font='consola.ttf',align='right')
    line(dst,(72,234),(1008,234),(63,65,69),2)
    line(dst,(72,234),(72+936*remaining/12,234),RED if remaining<1.5 else CYAN,3)
    box(dst,(0,1665,1080,255),INK)
    txt(dst,'KAGURABACHI',68,1731,35,font='bahnschrift.ttf')
    txt(dst,phase,68,1779,21,font='consola.ttf',color=(137,141,147))
    txt(dst,'@inkframez',1000,1752,28,font='consola.ttf',align='right',color=(189,190,192))
    for i in range(24):
        xx=72+i*40
        line(dst,(xx,1837),(xx,1849 if i%4 else 1858),RED if i<t/DURATION*24 else (59,62,66),2)

def label(dst,title,sub='',col=RED,tau=1):
    a=out(tau/.22); dx=(1-a)*85
    if title:
        size=min(102,900/max(len(title),1)*1.9)
        txt(dst,title,76+dx,1515,size,color=PAPER,alpha=a)
        box(dst,(82,1590,80,5),col)
    if sub:txt(dst,sub,180+dx,1592,25,font='consola.ttf',color=col,alpha=a)

def render_frame(i):
    t=i/FPS; beat=t/BEAT
    shot=next(s for s in SHOTS if s[0]<=beat<s[1])
    a,b,kind,p,r,caption=shot; u=(beat-a)/(b-a); tau=(beat-a)*BEAT
    remaining=float(np.interp(t,*zip(*CLOCK)))
    dst=background(p,tuple(r)).copy()
    # Stable alignment marks and very slow floating fragments create depth.
    for j in range(16):
        xx=(j*193+math.sin(t*.35+j)*28)%1080
        yy=(j*237-t*(9+j%5))%1920
        cv2.circle(dst,(d(xx),d(yy)),max(1,d(1+j%2)),(75,76,80),-1)
    for yy in [312,1410]:
        line(dst,(28,yy),(60,yy),(109,113,118),1)
        line(dst,(1020,yy),(1052,yy),(109,113,118),1)
    angle=mix(-1.5,1.0,ease(u)) if int(a/4)%2 else mix(1.4,-1,ease(u))
    entry=(1-out(tau/.17))*160*(1 if int(a/4)%2 else -1)
    phase='THE TWELVE-SECOND DUEL'

    if kind=='open':
        panel(dst,1,(0,150,1005,465),(38,750,1004,466),u,angle=-1,zoom=(1.03,1.09),accent=CYAN)
        txt(dst,'12',62,500,340,color=PAPER)
        txt(dst,'SECONDS.',75,690,118,color=RED)
        txt(dst,'ONE OPENING.',82,1395,80)
        txt(dst,'CHIHIRO vs SOJO',82,1508,34,font='consola.ttf',color=CYAN)
        streaks(dst,t,.3)
    elif kind=='versus':
        panel(dst,2,(1220,1060,910,540),(70,340,940,556),u,angle=2,pan=(-42,0),accent=RED,enter=entry)
        panel(dst,2,(432,1050,850,550),(70,930,940,590),u,angle=-2,pan=(42,0),accent=CYAN,enter=-entry)
        box(dst,(0,848,720,98),INK)
        txt(dst,'CHIHIRO',76,893,88,color=RED)
        box(dst,(520,1430,560,100),INK)
        txt(dst,'SOJO',960,1482,100,color=CYAN,align='right')
        txt(dst,'VS',870,916,125,outline=True)
    elif kind in ('hero','rush','charge','charge3'):
        ar=r[2]/r[3]; hh=min(1170,1000/ar); yy=300+(1170-hh)/2
        panel(dst,p,r,(40,yy,1000,hh),out(u),angle,zoom=(1.22,1.025),pan=(65,-38),accent=CYAN if kind=='charge' else RED,enter=entry)
        if kind in ('rush','charge','charge3'):streaks(dst,t,1.4,CYAN if kind!='charge3' else RED)
        if kind=='charge':
            electricity(dst,t,1.6)
            txt(dst,'2x',80,420,170,color=CYAN)
            label(dst,'DOUBLE THE LIMIT','SOJO  /  SPIRIT ENERGY',CYAN,tau)
        elif kind=='charge3':
            txt(dst,'3x',80,420,190,color=RED)
            label(dst,'TRIPLE THE LIMIT','CHIHIRO  /  NISHIKI',RED,tau)
        elif kind=='rush':
            electricity(dst,t)
            label(dst,'ALL IN','06:00  >  03:00',CYAN,tau)
        else:label(dst,caption,'CHIHIRO / SOJO' if caption else '',RED,tau)
    elif kind=='wide':
        ar=r[2]/r[3]; hh=min(830,990/ar)
        panel(dst,p,r,(45,460,990,hh),u,angle,zoom=(1.015,1.06),pan=(-38,0),accent=CYAN,enter=entry)
        txt(dst,'CUT / '+f'{int(a/4):02}',78,348,36,font='consola.ttf',color=CYAN)
        if p==2:
            panel(dst,2,(432,1060,1698,540),(70,1155,940,300),u,-1,zoom=(1.01,1.04),accent=RED)
        elif p==7:
            panel(dst,7,(0,0,975,225),(68,1200,944,217),u,-1,zoom=(1,1),accent=CYAN)
        elif p==8:
            panel(dst,8,(0,461,600,95),(75,1270,930,147),u,-1,zoom=(1,1),accent=RED)
        label(dst,caption,'',CYAN,tau)
        streaks(dst,t,.5)
    elif kind=='strip':
        if p==8:
            panel(dst,p,r,(270,340,540,1110),u,angle=0,zoom=(1.02,1.08),accent=RED)
            txt(dst,'THE ANSWER',60,420,90,outline=True)
            label(dst,'CHIHIRO','ENTEN  /  NISHIKI',RED,tau)
        else:
            ratio=r[2]/r[3]; hh=min(1080,max(580,1010/ratio))
            # Tight strip and enlarged offset ink echo; both move toward the center.
            panel(dst,p,r,(35,850-hh/2,1010,hh),out(u),angle=-3 if a%4 else 3,zoom=(1.22,1.02),pan=(75,0),accent=RED,enter=entry*1.4)
            # Edge typography describes the current beat, not an instruction to the viewer.
            word='FASTER' if a<32 else 'COUNTER' if a<72 else 'TOO LATE'
            txt(dst,word,76,397,140,outline=True,color=(115,119,126))
            line(dst,(78,1358),(400,1358),RED,2)
            txt(dst,'ENTEN / KUREGUMO',76,1410,23,font='consola.ttf',color=(145,148,155))
            if caption:label(dst,caption,'',RED,tau)
    elif kind=='release':
        panel(dst,p,r,(115,300,850,1236),u,angle=mix(1,0,out(u)),zoom=(1.12,1),accent=PAPER)
        # Bars close, motion settles: the viewer feels the lost speed before the hit.
        shutter=out(u)*85
        box(dst,(0,250,1080,shutter),INK);box(dst,(0,1510-shutter,1080,shutter),INK)
        box(dst,(0,1460,1080,205),INK)
        label(dst,'RELEASE NISHIKI','SHIFT THE TIMING',PAPER,tau)
        phase='A FRACTION OF A SECOND'
    elif kind=='kuro':
        dst[:]=INK
        panel(dst,p,r,(310,355,730,1062),0,angle=0,zoom=(1.0,1.0),accent=PAPER)
        box(dst,(0,1300,1080,366),INK)
        txt(dst,'KURO.',76,1430,224,color=PAPER)
        txt(dst,'ZERO DISTANCE',84,1600,32,font='consola.ttf',color=RED)
        phase='ZERO DISTANCE'
    elif kind=='impact':
        panel(dst,p,r,(35,385,1010,745),u,angle=mix(-4,0,out(u)),zoom=(1.14,1),accent=RED)
        panel(dst,11,(1090,1250,1020,345),(45,1218,990,335),u,angle=1,zoom=(1.12,1.0),accent=RED)
        # Directional slash drawn along the sword path, then a short settling kick.
        if tau<.3:
            strength=(1-tau/.3)
            line(dst,(-100,1390),(1180,400),PAPER,8*strength+1)
            line(dst,(-100,1410),(1180,420),RED,3*strength+1)
        phase='KURO / POINT-BLANK'
    elif kind=='final':
        panel(dst,p,r,(56,245,968,1452),u,angle=0,zoom=(1.095,1),accent=RED)
        box(dst,(0,1450,1080,215),INK)
        label(dst,'CLOUD GOUGER','THE BLADE BREAKS',RED,tau)
        phase='THE DECISIVE STRIKE'
    elif kind=='broken':
        panel(dst,p,r,(230,250,408,1440),u,angle=-8,zoom=(1.06,1),accent=CYAN)
        # Offset typography separates on the fracture cue without inventing new art.
        txt(dst,'BRO',40-out(u)*12,720,177,color=PAPER)
        txt(dst,'KEN',570+out(u)*22,1020,177,color=RED)
        line(dst,(50,867),(1010,796),PAPER,3)
        phase='CLOUD GOUGER / BROKEN'
    elif kind=='aftermath':
        panel(dst,p,r,(200,280,690,1166),u,angle=0,zoom=(1.03,1),accent=PAPER)
        txt(dst,'THE COST.',74,1520,98)
        phase='AFTERMATH / CHAPTER 18'
    elif kind=='end':
        dst=(background(p,tuple(r))*.6).astype(np.uint8)
        panel(dst,12,(0,670,975,562),(0,440,1080,622),u,angle=0,zoom=(1.05,1.11),accent=RED)
        box(dst,(0,950,1080,400),INK)
        txt(dst,'KAGURA',58,1060,205)
        txt(dst,'BACHI',58,1260,205,color=RED)
        txt(dst,'カグラバチ',80,1455,60,font='YuGothB.ttc')
        txt(dst,'CHIHIRO  /  SOJO',80,1545,33,font='consola.ttf',color=CYAN)
        txt(dst,'12 SECONDS. ONE OPENING.',80,359,33,font='consola.ttf')
        phase='MANGA BY TAKERU HOKAZONO'

    # At high-energy cuts, a single diagonal ink wipe carries screen direction.
    if a not in [0,4,72,76,78,80,84,88,90,92] and tau<.10:
        q=tau/.10; center=1080*q*2-300
        pts=np.int32([[d(center-330),0],[d(center+260),0],[d(center-180),H],[d(center-750),H]])
        cv2.fillConvexPoly(dst,pts,INK)
    if kind in ('hero','rush','charge','charge3','impact') and tau<.18:
        kick=(1-tau/.18)**2
        mat=np.float32([[1,0,d(math.sin(tau*93)*13*kick)],[0,1,d(math.cos(tau*87)*9*kick)]])
        dst=cv2.warpAffine(dst,mat,(W,H),borderMode=cv2.BORDER_REFLECT_101)
    # Two separated high-contrast strike frames; no repetitive strobe treatment.
    if i==round(EVENTS['strike']*FPS):dst[:]=PAPER
    if i==round(EVENTS['strike']*FPS)+2:dst=255-dst
    hud(dst,t,remaining,phase)
    return dst

def frame_batch(indices): return [(i,render_frame(i)) for i in indices]

def make_stills():
    dest=HERE/'stills'; dest.mkdir(exist_ok=True)
    samples=[(s[0]+min(1.2,(s[1]-s[0])*.5))*BEAT for s in SHOTS]
    thumbs=[]
    for j,t in enumerate(samples):
        rgb=render_frame(round(t*FPS))
        Image.fromarray(rgb).save(dest/f'{j:02}_{t:05.2f}.jpg',quality=92)
        th=Image.fromarray(rgb);th.thumbnail((216,384));
        tile=Image.new('RGB',(236,420),(27,28,32));tile.paste(th,((236-th.width)//2,7))
        ImageDraw.Draw(tile).text((12,397),f'{t:05.2f}s  {SHOTS[j][2]}',fill='white')
        thumbs.append(tile)
    grid=Image.new('RGB',(236*7,420*4),(27,28,32))
    for j,tile in enumerate(thumbs):grid.paste(tile,((j%7)*236,(j//7)*420))
    grid.save(dest/'contact.jpg',quality=92)
    print(dest/'contact.jpg')

def make_video(workers,preview=False):
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    raw=HERE/('_preview.mp4' if preview else '_video.mp4')
    output=ROOT/('kagurabachi-preview.mp4' if preview else 'kagurabachi-short.mp4')
    cmd=[ff,'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}',
         '-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast' if preview else 'medium',
         '-crf','21' if preview else '18','-pix_fmt','yuv420p','-threads','3',str(raw)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    start=time.monotonic(); n=round(DURATION*FPS)
    # Bounded batches prevent full-HD RGB frames accumulating in the parent process.
    try:
        with ProcessPoolExecutor(max_workers=workers,initializer=configure,initargs=(W,)) as pool:
            for base in range(0,n,workers*12):
                futures=[pool.submit(frame_batch,list(range(j,min(j+12,n)))) for j in range(base,min(base+workers*12,n),12)]
                for future in futures:
                    for idx,rgb in future.result():proc.stdin.write(rgb.tobytes())
                print(f'{min(base+workers*12,n)}/{n} frames  {time.monotonic()-start:.1f}s',flush=True)
        proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('Video encode failed')
    except BaseException:
        proc.kill();raise
    # Loudness normalized stereo AAC delivery; retain the original WAV for editing.
    subprocess.run([ff,'-y','-v','warning','-i',str(raw),'-i',str(HERE/'score.wav'),
                    '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','320k',
                    '-af','loudnorm=I=-14:TP=-1.2:LRA=9','-ar','48000','-t',str(DURATION),
                    '-movflags','+faststart',str(output)],check=True)
    print(f'EXPORT {output} ({output.stat().st_size/1024**2:.1f} MiB)',flush=True)
    (HERE/'render_manifest.json').write_text(json.dumps({'width':W,'height':H,'fps':FPS,'duration':DURATION,
        'frames':n,'bpm':160,'file':output.name,'shots':len(SHOTS),'pages':14},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['stills','video'])
    parser.add_argument('--width',type=int,default=1080);parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--preview',action='store_true');args=parser.parse_args()
    configure(args.width)
    make_stills() if args.mode=='stills' else make_video(args.workers,args.preview)
