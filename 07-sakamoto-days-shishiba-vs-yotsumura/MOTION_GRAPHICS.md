# Sakamoto Days — motion graphics version

`sakamoto-motion-graphics-short.mp4` is a new **9-second, 1080 × 1920, 30 fps**
edit. The previous layer demonstration, source pages, Canva exports and metadata
remain unchanged. This is a focused motion sample, not a complete account of the
chapter or a replacement for the cloud agent's full fight edit.

The two local action references informed the camera language. Sampled contact
sheets and quarter-second sequences showed layered foreground occlusion, camera
arrivals that decelerate into readable compositions, graphic changes of scale,
and short high-contrast impact frames. No footage, music or replacement artwork
from those references is included in this export.

## Choreography

| Time | Picture | Sound |
|---|---|---|
| 0–1.5 s | Tight rooftop contact pulls back to both fighters; original drawn sound effect retained; small independent foreground drifts | Syncopated bass, percussion, contact metal |
| 1.5–2.625 s | Opposed fighters, camera banks along weapon exchange; sliced typography beneath silhouettes; authentic wide band establishes both poses | Dry clash and blade swish |
| 2.625–3.375 s | Stage disguise crosses the image/type boundary; overlapping action pair stays joined | Short transition and driving rhythm |
| 3.375–4.125 s | Head, cloth and drawn motion trail travel together; fast camera arrival | Reveal hit |
| 4.125–5.25 s | Reflected face fills upper band; hammer crosses lower band; one local amber metal glint | Small metal detail and rising noise |
| 5.25–6 s | Exact held composition, including frozen grain | Silence |
| 6–7.875 s | Two paper frames; foreground recoil, original ink arc/droplets, short shake, decelerating pullback | Strong impact and decay |
| 7.875–9 s | Complete original impact spread resolves into a title composition | Decay and final fade |

Paper, ink and amber continue the Kagurabachi lessons. Art occupies the frame;
wide art uses full-width bands. Typography sits behind the drawing or belongs to
the final title. Amber marks metal/contact only. There are no persistent HUD
rails. Fast arrivals use a half-frame shutter sample and a decaying camera bank;
poses, faces and weapons are not redrawn or bent.

Small source-space movement is retained over reconstructed plates. Characters
from the rejected-background spread are composed on paper rather than over
residual fighter silhouettes. The reveal head and cloth receive identical
translation. Joined fighter layers remain joined.

The clash arrivals and finishing follow-through use larger foreground travel
on designed paper fields. There is no repaired background underneath those
sprites to expose; the manifest's small displacement limits still apply whenever
a reconstructed scene plate is used.

## Editable files

- `video/motion_graphics.py`: standalone compositor built on the accepted RGBA
  asset interface and existing premultiplied resampling utility.
- `video/motion_graphics_timeline.json`: shared picture/audio timing and shot notes.
- `video/music_motion_graphics.py`: original 160 BPM synthesis, metallic details,
  swishes, impact, compression and measured normalization.
- `video/motion_graphics_score.wav`: 48 kHz stereo original soundtrack.
- `motion-graphics-sheet.jpg`: phone-size review contact sheet.
- `video/motion_graphics_verification.json`: measurements of the delivered MP4.

Run from `video/` with the repository's Python dependencies:

```bash
python music_motion_graphics.py
python motion_graphics.py stills
python motion_graphics.py video
python -m unittest test_layer_preview test_motion_graphics -v
python verify_motion_graphics.py
```

The original renderer interfaces and `layers.json` are unchanged. The audio
generator has its own timing map and output names so running either version
does not overwrite the other. The title uses Impact, with a font fallback;
small credits use Bahnschrift when installed.

Artwork: Yuto Suzuki / Shueisha. Motion graphics and soundtrack produced for this
project, 2026-10-14.
