"""Delivery checks: complete decode, timing, source-copy integrity, audio metadata.

Run after the final render. Review contact.jpg visually as well as this report.
This is an export audit, not a claim that a numeric score evaluates artistic quality.
"""
from pathlib import Path
import hashlib, json, subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw
import imageio_ffmpeg
from timeline import SHOTS, BEAT, FPS, DURATION

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
DEST=HERE/'check'
DEST.mkdir(exist_ok=True)
assert SHOTS[0][0]==0 and SHOTS[-1][1]*BEAT==DURATION
assert all(a[1]==b[0] for a,b in zip(SHOTS,SHOTS[1:])), 'Timeline gap or overlap'
source=[]
for p in sorted((ROOT/'panels').glob('*.png')):
    im=Image.open(p)
    source.append({'page':p.name,'width':im.width,'height':im.height,
                   'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(source)==14
manifest=HERE/'source_manifest.json'
if manifest.exists():
    assert json.loads(manifest.read_text())==source, 'Source assets differ from recorded hashes'
else:
    manifest.write_text(json.dumps(source,indent=2))

path=ROOT/'kagurabachi-short.mp4'
cap=cv2.VideoCapture(str(path))
assert cap.isOpened(),path
width,height,rate=cap.get(3),cap.get(4),cap.get(5)
assert (width,height,rate)==(1080,1920,30),(width,height,rate)
selected={round((a+min(1.2,(b-a)*.5))*BEAT*FPS):j for j,(a,b,*_) in enumerate(SHOTS)}
selected.update({899:28,900:29,902:30,903:31,1079:32})
grid=Image.new('RGB',(236*7,420*5),(26,28,31))
count=0; means=[]
while True:
    ok,im=cap.read()
    if not ok:break
    means.append(float(im.mean()))
    if count in selected:
        j=selected[count]
        th=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));th.thumbnail((216,384))
        tile=Image.new('RGB',(236,420),(26,28,31));tile.paste(th,(10,5))
        ImageDraw.Draw(tile).text((12,397),f'{count/FPS:05.2f}s / frame {count}',fill='white')
        grid.paste(tile,((j%7)*236,(j//7)*420))
    count+=1
cap.release()
assert count==round(DURATION*FPS),count
grid.save(DEST/'encoded-contact.jpg',quality=94)

ff=imageio_ffmpeg.get_ffmpeg_exe()
audio=subprocess.run([ff,'-hide_banner','-i',str(path),'-vn','-af',
    'loudnorm=I=-14:TP=-1.2:LRA=9:print_format=json','-f','null','-'],
    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True).stderr
start=audio.rfind('{');stop=audio.rfind('}')
levels=json.loads(audio[start:stop+1])
report={'file':path.name,'width':width,'height':height,'fps':rate,'decoded_frames':count,
    'duration_seconds':count/rate,'shots':len(SHOTS),'source_pages':len(source),
    'min_frame_mean':min(means),'max_frame_mean':max(means),
    'audio_integrated_lufs':float(levels['input_i']),
    'audio_true_peak_dbtp':float(levels['input_tp']),
    'audio_loudness_range_lu':float(levels['input_lra']),
    'timeline_contiguous':True,'size_mb':round(path.stat().st_size/1e6,2)}
assert report['audio_true_peak_dbtp']<0,'Audio clipping'
(HERE/'qa_report.json').write_text(json.dumps(report,indent=2))
(DEST/'audio-analysis.txt').write_text(audio)
print(json.dumps(report,indent=2))
print(DEST/'encoded-contact.jpg')
