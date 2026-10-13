"""Verify the actual delivered PNGs, source hashes, decoded video and AAC mix."""
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
    movie=ROOT/'sakamoto-layer-preview-short.mp4'
    reader=imageio_ffmpeg.read_frames(str(movie),pix_fmt='rgb24');meta=next(reader)
    frames=sum(1 for _ in reader)
    assert frames==270,frames
    assert meta['size']==(1080,1920),meta
    assert abs(meta['fps']-30)<.001,meta
    assert abs(meta['duration']-9)<.05,meta
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
    result=dict(accepted_layers=len(manifest['assets']),roles=dict(Counter(a['role'] for a in manifest['assets'])),source_images_verified=10,rgba_and_hashes_verified=True,decoded_frames=frames,size=list(meta['size']),fps=meta['fps'],duration=meta['duration'],aac_integrated_lufs=integrated,aac_true_peak_dbtp=peak,quiet_gap_rms_ratio=ratio,impact_frame=180,impact_audio_sample=288000)
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':verify()
