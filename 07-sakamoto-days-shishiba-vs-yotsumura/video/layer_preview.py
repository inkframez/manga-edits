"""Canva RGBA layer preview. Run: python layer_preview.py stills | video.

No Canva access is needed to render. Coordinates come from ../layers.json;
picture and sound share layer_preview_timeline.json. Uses premultiplied alpha
while resampling so invisible colors cannot create fringes.
"""
from pathlib import Path
from functools import lru_cache
import argparse, json, math, os, subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio_ffmpeg

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
TL=json.loads((HERE/'layer_preview_timeline.json').read_text())
FPS=TL['fps']; DUR=TL['duration']; NFRAMES=round(FPS*DUR)
LAYERS={a['id']:a for a in json.loads((ROOT/'layers.json').read_text())['assets']}
PAPER=np.float32([239,234,224])/255
INK=np.float32([11,11,13])/255
AMBER=np.float32([245,179,53])/255
cv2.setNumThreads(4)

def clamp(x): return float(np.clip(x,0,1))
def ease(x): return 1-(1-clamp(x))**3
def event_frame(name): return round(TL['events'][name]*FPS)

def scene_at_frame(frame):
    if not 0<=frame<NFRAMES: raise ValueError('Frame outside preview')
    t=frame/FPS
    return next(s['id'] for s in TL['scenes'] if s['start']<=t<s['end'])

@lru_cache(maxsize=64)
def raster(file): return np.asarray(Image.open(ROOT/file).convert('RGBA'))

def place_rgba(canvas,sprite,origin,scale=1.,angle=0.,opacity=1.):
    """Place an RGBA image into a float RGB canvas; origin is its top-left.

    Rotation is around the PNG center. Transform only the visible destination
    region, and interpolate premultiplied RGB and alpha together.
    """
    if scale<=0 or opacity<=0:return
    h,w=sprite.shape[:2]; H,W=canvas.shape[:2]
    a=math.radians(angle); c=math.cos(a)*scale; s=math.sin(a)*scale
    matrix=np.float32([[c,-s,origin[0]+scale*w/2-c*w/2+s*h/2],
                       [s,c,origin[1]+scale*h/2-s*w/2-c*h/2]])
    pts=np.float32([[0,0],[w,0],[w,h],[0,h]])@matrix[:,:2].T+matrix[:,2]
    x0=max(0,int(np.floor(pts[:,0].min()))-2);x1=min(W,int(np.ceil(pts[:,0].max()))+2)
    y0=max(0,int(np.floor(pts[:,1].min()))-2);y1=min(H,int(np.ceil(pts[:,1].max()))+2)
    if x1<=x0 or y1<=y0:return
    rgba=sprite.astype(np.float32)/255
    rgba[:,:,:3]*=rgba[:,:,3:4]
    rgba*=opacity
    # Suppress screentone aliasing before substantial reduction.
    if scale<.7: rgba=cv2.GaussianBlur(rgba,(0,0),max(.3,(1/scale-1)*.3))
    matrix[:,2]-=[x0,y0]
    transformed=cv2.warpAffine(rgba,matrix,(x1-x0,y1-y0),flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
    view=canvas[y0:y1,x0:x1]
    view[:]=transformed[:,:,:3]+view*(1-transformed[:,:,3:4])

def layer(canvas,name,center,zoom,shift=(0,0),angle=0.,opacity=1.):
    a=LAYERS[name];H,W=canvas.shape[:2]
    origin=(W/2+(a['origin'][0]-center[0]+shift[0])*zoom,
            H/2+(a['origin'][1]-center[1]+shift[1])*zoom)
    place_rgba(canvas,raster(a['file']),origin,zoom*a['sprite_scale'],angle,opacity)

@lru_cache(maxsize=20)
def text_image(text,size):
    choices=[Path('C:/Windows/Fonts/impact.ttf'),ROOT.parent/'fonts/impact.ttf']
    font=next((ImageFont.truetype(str(p),size) for p in choices if p.exists()),ImageFont.load_default(size=size))
    bbox=font.getbbox(text);im=Image.new('RGBA',(bbox[2]-bbox[0]+8,bbox[3]-bbox[1]+8))
    ImageDraw.Draw(im).text((4-bbox[0],4-bbox[1]),text,font=font,fill=(11,11,13,255))
    return np.asarray(im)

def opening(canvas,t,k):
    # The rooftop is the frame. The original top strip restores the drawn BAM.
    zoom=(1.67-.16*ease(t/2.8))*k
    center=(555+15*math.sin(t*1.1),520+15*ease(t/.5))
    layer(canvas,'opening_rooftop',center,zoom)
    top=raster('panels/ch100_004.jpg')[:290]
    place_rgba(canvas,top,(canvas.shape[1]/2-center[0]*zoom,canvas.shape[0]/2-center[1]*zoom),zoom)
    q=ease(t/.35)
    layer(canvas,'opening_shishiba',center,zoom,(18*(1-q)-8*math.sin(t*1.8),-8*math.sin(t*1.5)))
    layer(canvas,'opening_yotsumura',center,zoom,(-20*(1-q)+6*math.sin(t*1.8),4*math.sin(t*1.5)))
    age=t-TL['events']['opening_hit']
    if 0<=age<.11:canvas[:]=canvas*(1-.22*(1-age/.11))+PAPER*.22*(1-age/.11)

def reflection(canvas,t,k):
    H,W=canvas.shape[:2]; canvas[:]=INK
    u=clamp((t-3)/2.25)
    # Two full-width image bands, with a large free-standing hammer between them.
    panel=raster(LAYERS['hammer_reflection']['file'])
    ps=(1.12+.14*ease(u))*k
    place_rgba(canvas,panel,((W-panel.shape[1]*ps)/2,180*k),ps)
    canvas[int(790*k):]=PAPER
    lines=raster(LAYERS['hammer_speedlines']['file'])
    place_rgba(canvas,lines,(-30*k,1010*k),1.15*k)
    place_rgba(canvas,text_image('MIRROR.',218),(65*k,820*k),k)
    hammer=raster(LAYERS['hammer_flying']['file'])
    hs=(2.05+.13*ease(u))*k
    place_rgba(canvas,hammer,((W-hammer.shape[1]*hs)/2+(16-32*ease(u))*k,1010*k-40*k*ease(u)),hs,-4+8*ease(u))
    age=t-TL['events']['glint']
    if -.10<age<.22:
        strength=1-abs(age-.04)/.18
        lay=np.zeros_like(canvas);y=int((1450-650*(age+.10))*k)
        cv2.line(lay,(int(450*k),y),(int(660*k),y-int(85*k)),tuple(float(v) for v in AMBER),max(1,round(4*k)),cv2.LINE_AA)
        canvas[:]=np.clip(canvas+cv2.GaussianBlur(lay,(0,0),max(.4,8*k))*max(0,strength)*1.8,0,1)

def impact(canvas,t,k):
    age=t-TL['events']['impact'];zoom=(1.17+.18*math.exp(-age*8))*k
    shake=math.exp(-age*12)
    center=(1430+12*shake*math.sin(age*160),840+10*shake*math.cos(age*143))
    layer(canvas,'impact_ink_arc',center,zoom,(0,-10*(1-ease(age/.4))))
    layer(canvas,'impact_droplets',center,zoom,(-10*ease(age/.4),4*ease(age/.4)))
    layer(canvas,'impact_pair',center,zoom,(12*(1-ease(age/.22)),8*(1-ease(age/.22))))
    if age<.16:
        spokes=np.zeros_like(canvas);cx,cy=int(650*k),int(1020*k)
        for i in range(7):
            a=i*math.tau/7+.2; r=(45+80*age/.16)*k
            cv2.line(spokes,(cx,cy),(int(cx+r*math.cos(a)),int(cy+r*math.sin(a))),tuple(float(v) for v in AMBER),max(1,round(3*k)),cv2.LINE_AA)
        canvas[:]=np.clip(canvas+spokes*(1-age/.16),0,1)
    # End on the authentic spread, not Canva's reconstructed background.
    mix=ease((t-TL['events']['settle'])/.45)
    if mix>0:
        still=np.empty_like(canvas);still[:]=PAPER
        src=raster('panels/ch100_017.jpg')
        place_rgba(still,src,(canvas.shape[1]/2-center[0]*zoom,canvas.shape[0]/2-center[1]*zoom),zoom)
        canvas[:]=canvas*(1-mix)+still*mix

def render_frame(frame,width=1080,height=1920):
    scene=scene_at_frame(frame);t=frame/FPS;k=width/1080
    if abs(width/height-9/16)>.001:raise ValueError('Use a 9:16 output size')
    canvas=np.empty((height,width,3),np.float32);canvas[:]=PAPER
    if scene=='opening':opening(canvas,t,k)
    elif scene in ('reflection','hold'):reflection(canvas,min(t,5.25),k)
    else:impact(canvas,t,k)
    if event_frame('impact')<=frame<event_frame('impact')+2:canvas[:]=PAPER
    # Deterministic fine grain, deliberately below the page's own screentone.
    rng=np.random.default_rng(frame+1700)
    canvas+=rng.normal(0,.002,(height,width,1)).astype(np.float32)
    return (np.clip(canvas,0,1)*255+.5).astype(np.uint8)

def save_stills():
    frames=[0,12,45,89,90,120,150,158,179,180,184,195,225,255,269]
    out=HERE/'stills_layers';out.mkdir(exist_ok=True)
    sheet=Image.new('RGB',(5*216,3*418),(24,27,32));d=ImageDraw.Draw(sheet)
    for i,f in enumerate(frames):
        im=Image.fromarray(render_frame(f));im.save(out/f'{f:03d}.jpg',quality=92)
        sheet.paste(im.resize((216,384),Image.Resampling.LANCZOS),(i%5*216,i//5*418))
        d.text((i%5*216+8,i//5*418+390),f'{f/FPS:.2f}s / {f}',fill='white')
    sheet.save(ROOT/'layer-preview-sheet.jpg',quality=92)
    print(ROOT/'layer-preview-sheet.jpg',flush=True)

def save_video():
    score=HERE/'layer_preview_score.wav'
    if not score.exists():raise FileNotFoundError('Run music_layer_preview.py first')
    output=ROOT/'sakamoto-layer-preview-short.mp4'
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r',str(FPS),'-i','-','-i',str(score),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-tune','animation','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-t',str(DUR),'-movflags','+faststart',str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for f in range(NFRAMES):
            proc.stdin.write(render_frame(f).tobytes())
            if f%30==0:print(f'{f}/{NFRAMES}',flush=True)
        proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('FFmpeg failed')
    except BaseException:
        proc.kill();proc.wait();raise
    print(output,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['stills','video']);args=parser.parse_args()
    save_stills() if args.mode=='stills' else save_video()
