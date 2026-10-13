"""Reference-informed 9-second manga motion graphics, preserving the old preview.

Run: python motion_graphics.py stills | video. Original poses, no AI inbetweening.
Uses the accepted RGBA layer interface and a separate shared picture/audio map.
"""
from pathlib import Path
from functools import lru_cache
import argparse, json, math, subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from layer_preview import raster, place_rgba, LAYERS, PAPER, INK, AMBER, ease, clamp

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
TL=json.loads((HERE/'motion_graphics_timeline.json').read_text())
FPS=TL['fps'];NFRAMES=round(FPS*TL['duration'])


@lru_cache(maxsize=48)
def typography(words,size,color='ink',label=False):
    name='bahnschrift.ttf' if label else 'impact.ttf'
    fontpath=Path('C:/Windows/Fonts')/name
    if not fontpath.exists():fontpath=ROOT.parent/'fonts'/name
    font=ImageFont.truetype(str(fontpath),size) if fontpath.exists() else ImageFont.load_default(size=size)
    box=font.getbbox(words);im=Image.new('RGBA',(box[2]-box[0]+12,box[3]-box[1]+12))
    fill={'ink':(11,11,13,255),'paper':(239,234,224,255),'amber':(245,179,53,255)}[color]
    ImageDraw.Draw(im).text((6-box[0],6-box[1]),words,font=font,fill=fill)
    return np.asarray(im)


def word(canvas,words,position,size,k,color='ink',opacity=1,label=False,maxwidth=900):
    im=typography(words,size,color,label)
    s=min(1,maxwidth/im.shape[1])*k
    place_rgba(canvas,im,(position[0]*k,position[1]*k),s,opacity=opacity)


def sprite(canvas,name,center,zoom,shift=(0,0),opacity=1):
    a=LAYERS[name];H,W=canvas.shape[:2]
    p=(W/2+(a['origin'][0]-center[0]+shift[0])*zoom,
       H/2+(a['origin'][1]-center[1]+shift[1])*zoom)
    place_rgba(canvas,raster(a['file']),p,zoom*a['sprite_scale'],opacity=opacity)


def source(canvas,file,center,zoom,crop=None,opacity=1):
    im=raster(file);left,top=0,0
    if crop:
        left,top,right,bottom=crop;im=im[top:bottom,left:right]
    H,W=canvas.shape[:2]
    place_rgba(canvas,im,(W/2+(left-center[0])*zoom,H/2+(top-center[1])*zoom),zoom,opacity=opacity)


def rule(canvas,y,k,color=AMBER,width=3):
    cv2.line(canvas,(round(65*k),round(y*k)),(round(920*k),round(y*k)),
             tuple(float(v) for v in color),max(1,round(width*k)),cv2.LINE_AA)


def opening(canvas,t,k):
    # Fast depth arrival, then sustained camera travel; small source-space drifts.
    q=ease(t/.45);travel=ease(t/1.5)
    z=(2.15-.53*q-.12*travel)*k
    hit=max(0,t-TL['events']['opening_hit'])
    recoil=math.exp(-hit*22) if t>=TL['events']['opening_hit'] else 0
    center=(580-45*travel+12*recoil*math.sin(hit*115),510+30*travel)
    sprite(canvas,'opening_rooftop',center,z)
    source(canvas,'panels/ch100_004.jpg',center,z,(0,0,1200,290))
    sprite(canvas,'opening_yotsumura',center,z,(14*(1-q)-7*travel,3*travel))
    sprite(canvas,'opening_shishiba',center,z,(-16*(1-q)+8*travel,-4*travel))
    if 0<=t-TL['events']['opening_hit']<.065:
        canvas[:]=canvas*.72+PAPER*.28


def clash(canvas,t,k):
    u=(t-1.5)/1.125;q=ease(u)
    canvas[:]=PAPER
    # Typography is physically split along the weapon's diagonal.
    typefield=np.empty_like(canvas);typefield[:]=PAPER
    word(typefield,'CLASH',(56,1060),370,k)
    H,W=canvas.shape[:2];yy,xx=np.mgrid[:H,:W]
    mask=yy<(.22*xx+1230*k)
    offset=round(28*(1-ease(u/.28))*k)
    upper=np.roll(typefield,offset,axis=1);lower=np.roll(typefield,-offset,axis=1)
    canvas[:]=np.where(mask[:,:,None],upper,lower)
    z=(.97-.17*q)*k;center=(1100-180*q,410+100*q)
    arrival=ease(u/.3)
    # These sprites are over a designed paper field, so larger lateral travel
    # cannot uncover repaired plate areas. Each original pose remains intact.
    sprite(canvas,'clash_yotsumura',center,z,(-160*(1-arrival),18*(1-arrival)))
    sprite(canvas,'clash_shishiba',center,z,(160*(1-arrival),-18*(1-arrival)))
    # A small authentic spread band makes the geography readable.
    band=raster('panels/ch100_010.jpg')[:925]
    bs=1080/band.shape[1]*k
    place_rgba(canvas,band,(0,1420*k+60*k*(1-ease(u/.35))),bs)
    if u<.2:
        cv2.line(canvas,(0,round(1120*k)),(W,round(770*k)),tuple(float(v) for v in AMBER),max(1,round(3*k)),cv2.LINE_AA)


def disguise(canvas,t,k):
    u=(t-2.625)/.75;q=ease(u)
    canvas[:]=INK
    word(canvas,'SHIFT',(65,180),365,k,'paper')
    # Joined pair stays joined: foreground traverses the stage/type boundary.
    z=(1.30+.20*q)*k;center=(690+45*q,1430+50*q)
    sprite(canvas,'stage_disguise_plate',center,z)
    sprite(canvas,'stage_yotsumura',center,z,(0,4*q))
    sprite(canvas,'stage_disguise_pair',center,z,(7*(1-q),-5*(1-q)))
    # The untouched drawn sound effect stays visible as a second full-width band.
    original=raster('panels/ch100_014.jpg')[0:1030,45:980]
    scale=.75*k
    place_rgba(canvas,original,(-30*k,1400*k+45*(1-q)*k),scale)


def reveal(canvas,t,k):
    u=(t-3.375)/.75;q=ease(u)
    canvas[:]=PAPER
    # Head and cloth receive the same shift. No disconnected neck/limb rigging.
    center=(650+85*q,440+90*q);z=(1.57+.18*q)*k
    sprite(canvas,'reveal_yotsumura_head',center,z,(3*(1-q),0))
    sprite(canvas,'reveal_disguise_cloth',center,z,(3*(1-q),0))
    sprite(canvas,'reveal_motion_trail',center,z,(3*(1-q),0))
    # Actual eye close-up, retained as drawn rather than painted or regenerated.
    # Do not append dialogue fragments as tiny unreadable inset panels.


def reflection(canvas,t,k):
    u=clamp((t-4.125)/1.125);q=ease(u)
    canvas[:]=INK
    panel=raster(LAYERS['hammer_reflection']['file'])
    ps=(1.25+.3*q)*k
    # Reflected face lands in the upper third at a readable scale.
    place_rgba(canvas,panel,(-180*k-80*q*k,250*k-45*q*k),ps)
    canvas[round(900*k):]=PAPER
    word(canvas,'REFLECT.',(62,920),235,k)
    line=raster(LAYERS['hammer_speedlines']['file'])
    place_rgba(canvas,line,(-60*k,1170*k),1.2*k)
    hammer=raster(LAYERS['hammer_flying']['file'])
    hs=(1.85+.18*q)*k
    place_rgba(canvas,hammer,((110-24*q)*k,(1130-80*q)*k),hs,-8+12*q)
    # Local metal highlight. Never colour the reflected eye or the whole picture.
    age=t-TL['events']['glint']
    if -.08<age<.16:
        strength=math.sin(math.pi*(age+.08)/.24)**2
        glow=np.zeros_like(canvas);cx=int((540+age*320)*k);cy=int((1310-age*160)*k)
        cv2.line(glow,(cx-round(90*k),cy+round(35*k)),(cx+round(90*k),cy-round(35*k)),tuple(float(v) for v in AMBER),max(1,round(4*k)),cv2.LINE_AA)
        canvas[:]=np.clip(canvas+cv2.GaussianBlur(glow,(0,0),max(.5,4*k))*strength*2,0,1)


def impact(canvas,t,k):
    age=t-6.;q=ease(age/.6)
    z=(1.48-.33*q-.18*ease(age/2.8))*k
    decay=math.exp(-age*14)
    center=(1420+14*decay*math.sin(age*144),840+11*decay*math.cos(age*123))
    canvas[:]=PAPER
    sprite(canvas,'impact_ink_arc',center,z,(0,-12*(1-q)))
    sprite(canvas,'impact_droplets',center,z,(-12*q,8*q))
    # Decisive foreground follow-through over paper; the joined pose is intact.
    sprite(canvas,'impact_pair',center,z,(250*(1-ease(age/.36)),80*(1-ease(age/.36))))
    if .067<=age<.20:
        power=(.20-age)/.133
        H,W=canvas.shape[:2]
        cv2.line(canvas,(0,round(1450*k)),(W,round(450*k)),tuple(float(v) for v in (PAPER*(1-power)+AMBER*power)),max(1,round(6*k)),cv2.LINE_AA)
    mix=ease((t-TL['events']['settle'])/.5)
    if mix:
        authentic=np.empty_like(canvas);authentic[:]=PAPER
        source(authentic,'panels/ch100_017.jpg',center,z)
        canvas[:]=canvas*(1-mix)+authentic*mix
    if t>7.875:
        # Pull out to the complete authentic spread, rather than cropping its hit.
        end=np.empty_like(canvas);end[:]=PAPER
        im=raster('panels/ch100_017.jpg');s=1080/im.shape[1]*k
        place_rgba(end,im,(0,260*k),s)
        rule(end,1120,k)
        word(end,'SAKAMOTO',(65,1170),175,k,maxwidth=840)
        word(end,'DAYS',(65,1340),185,k,maxwidth=840)
        word(end,'YUTO SUZUKI / SHUEISHA',(520,1455),25,k,'ink',label=True,maxwidth=390)
        reveal=ease((t-7.875)/.55)
        canvas[:]=canvas*(1-reveal)+end*reveal


SCENES={'opening':opening,'clash':clash,'disguise':disguise,'reveal':reveal,'reflection':reflection,'impact':impact}


def picture(t,width,height):
    k=width/1080;canvas=np.empty((height,width,3),np.float32);canvas[:]=PAPER
    scene=next(s for s in TL['scenes'] if s['start']<=t<s['end'])
    if scene['id']=='hold':reflection(canvas,5.25,k)
    else:SCENES[scene['id']](canvas,t,k)
    # A camera bank conveys depth without altering the drawn poses. Overscan
    # keeps a rolling camera from exposing repeated borders or plate holes.
    if scene['id'] not in ('hold','impact'):
        age=t-scene['start']
        angles={'opening':-6,'clash':8,'disguise':-4,'reveal':-9,'reflection':3}
        angle=angles[scene['id']]*math.exp(-age*9)
        scale=1.0+.08*math.exp(-age*8)
        matrix=cv2.getRotationMatrix2D((width/2,height/2),angle,scale)
        fill=INK if scene['id'] in ('disguise','reflection') else PAPER
        canvas=cv2.warpAffine(canvas,matrix,(width,height),flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT,borderValue=tuple(float(v) for v in fill))
    return canvas


def render_frame(frame,width=1080,height=1920):
    if not 0<=frame<NFRAMES:raise ValueError('Frame outside edit')
    if abs(width/height-9/16)>.001:raise ValueError('Use a 9:16 output size')
    t=frame/FPS;canvas=picture(t,width,height)
    # A shutter sample only on fast camera arrivals. Quiet hold is truly still.
    fast=any(0<t-c<.13 for c in [0,1.5,2.625,3.375,4.125,6])
    if fast and not 6<=t<6.067:
        canvas=canvas*.75+picture(max(0,t-1/(FPS*2)),width,height)*.25
    if 6<=t<6+2/FPS:canvas[:]=PAPER
    # Grain is fixed during the anticipation pause; source screentones stay crisp.
    seed=158 if 5.25<=t<6 else frame
    rng=np.random.default_rng(seed+4700)
    canvas+=rng.normal(0,.0015,(height,width,1)).astype(np.float32)
    return (np.clip(canvas,0,1)*255+.5).astype(np.uint8)


def save_stills():
    frames=[0,12,30,46,65,80,93,103,115,125,139,156,165,179,180,183,195,225,249,269]
    out=HERE/'stills_motion';out.mkdir(exist_ok=True)
    sheet=Image.new('RGB',(1080,4*418),(20,20,24));d=ImageDraw.Draw(sheet)
    for i,f in enumerate(frames):
        im=Image.fromarray(render_frame(f));im.save(out/f'{f:03d}.jpg',quality=93)
        x=i%5*216;y=i//5*418;sheet.paste(im.resize((216,384),Image.Resampling.LANCZOS),(x,y));d.text((x+6,y+390),f'{f/FPS:.2f}s',fill='white')
    sheet.save(ROOT/'motion-graphics-sheet.jpg',quality=93)
    print(ROOT/'motion-graphics-sheet.jpg',flush=True)


def save_video():
    score=HERE/'motion_graphics_score.wav'
    if not score.exists():raise FileNotFoundError('Run music_motion_graphics.py first')
    output=ROOT/'sakamoto-motion-graphics-short.mp4'
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r',str(FPS),'-i','-','-i',str(score),'-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','18','-tune','animation','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-t','9','-movflags','+faststart',str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for f in range(NFRAMES):
            proc.stdin.write(render_frame(f).tobytes())
            if f%30==0:print(f'{f}/{NFRAMES}',flush=True)
        proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('FFmpeg encode failed')
    except BaseException:
        proc.kill();proc.wait();raise
    print(output,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['stills','video']);args=parser.parse_args()
    save_stills() if args.mode=='stills' else save_video()
