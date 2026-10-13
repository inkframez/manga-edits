"""Verify motion graphics against actual decoded media, layer/source hashes and AAC."""
from pathlib import Path
import hashlib, json, re, subprocess
from collections import Counter
import numpy as np
from PIL import Image
import imageio_ffmpeg

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent

def verify():
    manifest=json.loads((ROOT/'layers.json').read_text())
    for a in manifest['assets']:
        p=ROOT/a['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],a['id']
        with Image.open(p) as im:
            im.load();assert im.mode=='RGBA',a['id'];assert list(im.size)==a['size'],a['id']
        assert a['sprite_scale']>0 and len(a['origin'])==2
    for a in json.loads((ROOT/'sources.json').read_text())['assets']:
        assert hashlib.sha256((ROOT/a['file']).read_bytes()).hexdigest()==a['sha256'],a['file']
    movie=ROOT/'sakamoto-motion-graphics-short.mp4'
    reader=imageio_ffmpeg.read_frames(str(movie),pix_fmt='rgb24');meta=next(reader)
    frames=0;review={}
    for i,raw in enumerate(reader):
        frames+=1
        if i in (159,178,180,181,185):
            review[i]=np.frombuffer(raw,np.uint8).reshape(1920,1080,3).copy()
    assert frames==270,frames
    assert meta['size']==(1080,1920),meta
    assert abs(meta['fps']-30)<.001,meta
    assert abs(meta['duration']-9)<.05,meta
    assert review[180].mean()>220 and review[181].mean()>220,'Missing impact flash'
    assert review[185].mean()<210,'Impact does not recover to readable artwork'
    hold_difference=float(np.abs(review[159].astype(float)-review[178].astype(float)).mean())
    assert hold_difference<1.,hold_difference
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    report=subprocess.run([ff,'-hide_banner','-i',str(movie),'-vn','-af','loudnorm=I=-14:TP=-1:LRA=9:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    loud=json.loads(re.findall(r'\{[^{}]+\}',report.stderr)[-1])
    integrated=float(loud['input_i']);peak=float(loud['input_tp'])
    assert -15<=integrated<=-13,integrated
    assert peak<=-1.,peak
    decoded=subprocess.run([ff,'-v','error','-i',str(movie),'-vn','-f','f32le','-ac','2','-ar','48000','-'],capture_output=True,check=True)
    sound=np.frombuffer(decoded.stdout,dtype='<f4').reshape(-1,2)
    # AAC may append codec padding; decoded container duration is checked above.
    assert abs(len(sound)/48000-9)<.03,len(sound)
    quiet=np.sqrt(np.mean(sound[round(5.4*48000):round(5.9*48000)]**2))
    drive=np.sqrt(np.mean(sound[round(.7*48000):round(2.5*48000)]**2))
    ratio=float(quiet/max(drive,1e-9));assert ratio<.12,ratio
    # Check the encoded attack itself, allowing AAC pre-echo within one frame.
    mono=np.mean(sound**2,axis=1)
    window=240
    local=np.sqrt(np.convolve(mono[round(5.9*48000):round(6.15*48000)],np.ones(window)/window,'valid'))
    crossed=np.flatnonzero(local>.06);assert len(crossed),'Missing encoded final attack'
    attack_time=5.9+int(crossed[0])/48000
    assert abs(attack_time-6)<1/30,attack_time
    result=dict(accepted_layers=len(manifest['assets']),roles=dict(Counter(a['role'] for a in manifest['assets'])),source_images_verified=10,rgba_and_hashes_verified=True,decoded_frames=frames,size=list(meta['size']),fps=meta['fps'],duration=meta['duration'],aac_integrated_lufs=integrated,aac_true_peak_dbtp=peak,quiet_gap_rms_ratio=ratio,impact_frame=180,impact_audio_sample=288000)
    result.update(encoded_attack_seconds=round(attack_time,5),hold_decoded_mean_pixel_difference=round(hold_difference,5),two_frame_impact_flash_verified=True,video_sha256=hashlib.sha256(movie.read_bytes()).hexdigest())
    (HERE/'motion_graphics_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':verify()
